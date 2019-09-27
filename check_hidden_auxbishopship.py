#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html
import re
import requests


def dioid2wd(dioid):
    QUERY4DIOID = 'SELECT ?item ?itemLabel WHERE { ?item wdt:P1866 "' + dioid + '". }'
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    try:
        generator = pg.WikidataSPARQLPageGenerator(QUERY4DIOID, site=wikidata_site)
        for item in generator:
            mywd = item.get()
            print('--- WD-Item-4-Diocese found: ' + item.id)
            return item.id

    except:
        print('!!! query for diocese failed.')
        return False


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item WHERE {
  ?item wdt:P1047 ?cathi.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q75178. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY (RAND())
LIMIT 50000
"""

path4qs = 'log_quick_hiddenauxbishopships.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
repo = wikidata_site.data_repository()
item_properties = ''
count_props = 0


for item in generator:
    mywd = item.get()
    mywd_id = item.id
    print("\n" + '>> Checking WD-ID: ' + mywd_id)
    print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

    claim_list_pos = {}
    my_cathbishop_claim = {}
    count_bishoppos = 0

    claim_list_cathid = mywd['claims']['P1047']
    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print('-- Catholic-Hierarchy-Id: ' + mycathid)
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
        print('-- Catholic-Hierarchy-URL: ' + chorgurl)

        r = requests.get(chorgurl, timeout=10)
        if r.status_code != 200:
            print('### HTTP-ERROR ON cath-id: ' + chorgurl)
            continue
        aux_bishopship_tr = re.findall(r"\<tr\>\<td[^\>]+\>.*\<\/td\>\<td\>.*\<\/td\>\<td\>Auxiliary Bishop of (.*)\<\/td\>.*\<\/tr\>", r.content)

        l_auxbishop = []

        if len(aux_bishopship_tr) > 0:
            for x in range(0, len(aux_bishopship_tr)):
                dioceseid = re.findall(r'href="\/diocese\/d([a-z0-9]+).html"', aux_bishopship_tr[x])
                if(len(dioceseid) > 0):
                    l_auxbishop.append(dioceseid[0])
            l_auxbishop = list(set(l_auxbishop))
            print('-- Diocesan-Bishopship-Info: ' + ', '.join(l_auxbishop))

            try:
                claim_list_currentpositions = mywd['claims']['P39']
            except:
                claim_list_currentpositions = []

            l_known_auxbishopships = []

            for single_pos in claim_list_currentpositions:
                trgt_pos = single_pos.getTarget()
                if trgt_pos.id == 'Q75178':
                    l_known_auxbishopships.append(single_pos)

            if (len(l_known_auxbishopships) > 0):
                print(('-- Found {} Job-Claims for aux-bishopships'.format(len(l_known_auxbishopships))))

            for dbishop in l_auxbishop:
                mydiowd = dioid2wd(dbishop)
                known_a2d = False

                for known_auxbishopship in l_known_auxbishopships:
                    a_qualis = known_auxbishopship.qualifiers
                    if not 'P708' in a_qualis:
                        continue
                    if (len(a_qualis['P708']) > 1):
                        print('-- !!! Take care there are more than 1 Dio-Claims!')
                        continue
                    diozese_claim = a_qualis['P708'][0]
                    trgt_d = diozese_claim.getTarget()
                    if (trgt_d.id == mydiowd):
                        print('-- Found aux-bishopship without already known and matching Diozese-Claim.')
                        known_a2d = True
                        continue

                if (known_a2d == True):
                    continue

                if (mydiowd != False and mydiowd != None):
                    if len(l_auxbishop) == 1:
                        item_properties += "\n" + mywd_id + "\tP39\tQ75178\tP708\t" + mydiowd
                        item_properties += "\tS1047\t\"" + mycathid + "\"\t"
                    else:
                        new_claim = pywikibot.Claim(repo, 'P39')
                        target_db = pywikibot.ItemPage(repo, 'Q75178')
                        target_dioclaim = pywikibot.Claim(repo, 'P708')
                        target_dio = pywikibot.ItemPage(repo, mydiowd)
                        target_dioclaim.setTarget(target_dio)
                        new_claim.setTarget(target_db)
                        new_claim.addQualifier(target_dioclaim)
                        item.addClaim(new_claim, summary='added aux-bishop-claim')

        fq = open(path4qs, "a")
        fq.write(item_properties)
        fq.close()
        item_properties = ''

print(('Done!' + "\n"))
