#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import lxml.html
import re
import progressbar


def requests_retry_session(
    retries=5,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def dioid2wd(dioid):
    QUERY4DIOID = 'SELECT ?item ?itemLabel WHERE { ?item wdt:P1866 "' + dioid + '". }'
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    try:
        generator = pg.WikidataSPARQLPageGenerator(QUERY4DIOID, site=wikidata_site)
        for item in generator:
            mywd = item.get()
            print(('--- WD-Item-4-Diocese found: ' + item.id))
            return item.id

    except:
        print('!!! query for diocese failed.')
        return False


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathiLabel WHERE {
  ?item wdt:P1047 ?cathi;
    wdt:P39 ?position.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q1144278. })
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q65924966. })
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q948657. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
GROUP BY ?item ?itemLabel ?birthLabel ?cathiLabel
LIMIT 10000
"""

path4qs = 'log_quick_hiddenbishopships.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
generator = list(generator)
repo = wikidata_site.data_repository()
item_properties = ''
count_props = 0

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):
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
            print(('-- Catholic-Hierarchy-Id: ' + mycathid))
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print(('-- Catholic-Hierarchy-URL: ' + chorgurl))

            r = requests_retry_session().get(chorgurl)
            if r.status_code != 200:
                print(('### HTTP-ERROR ON cath-id: ' + chorgurl))
                continue
            diocesan_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Bishop of (.*)</td>.*</tr>", r.content)
            titular_bishopship_tr = re.findall(b"<tr><td[^>]+>.*\</td><td>.*</td><td>Titular Bishop of (.*)</td>.*</tr>", r.content)

            l_dbishop = []
            l_tbishop = []

            l_known_dbishopships = []
            l_known_tbishopships = []

            claim_list_currentpositions = mywd['claims']['P39']

            for single_pos in claim_list_currentpositions:
                trgt_pos = single_pos.getTarget()
                if trgt_pos.id == 'Q1144278':
                    l_known_dbishopships.append(single_pos)
                elif trgt_pos.id == 'Q948657':
                    l_known_tbishopships.append(single_pos)

            if len(diocesan_bishopship_tr) > 0:
                for x in range(0, len(diocesan_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', diocesan_bishopship_tr[x])
                    if(len(dioceseid) > 0):
                        l_dbishop.append(dioceseid[0].decode('utf-8'))
                l_dbishop = list(set(l_dbishop))
                print(('-- Diocesan-Bishopship-Info: ' + ', '.join(l_dbishop)))

                if (len(l_known_dbishopships) > 0):
                    print(('-- Found {} Job-Claims for diocesan bishopships'.format(len(l_known_dbishopships))))

                if (len(l_known_tbishopships) > 0):
                    print(('-- Found {} Job-Claims for titular bishopships'.format(len(l_known_dbishopships))))

                for dbishop in l_dbishop:
                    mydiowd = dioid2wd(dbishop)
                    known_a2d = False

                    for known_dbishopship in l_known_dbishopships:
                        a_qualis = known_dbishopship.qualifiers
                        if not 'P708' in a_qualis:
                            continue
                        if (len(a_qualis['P708']) > 1):
                            print('-- !!! Take care there are more than 1 Dio-Claims!')
                            continue
                        diozese_claim = a_qualis['P708'][0]
                        trgt_d = diozese_claim.getTarget()
                        if (trgt_d.id == mydiowd):
                            print('-- Found diocesan bishopship without already known and matching Diozese-Claim.')
                            known_a2d = True
                            continue

                    if (known_a2d == True):
                        continue

                    if (mydiowd != False and mydiowd != None):
                        if len(l_dbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ1144278\tP708\t" + mydiowd
                            item_properties += "\tS1047\t\"" + mycathid + "\"\t"
                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_db = pywikibot.ItemPage(repo, 'Q1144278')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_db)
                            new_claim.addQualifier(target_dioclaim)
                            item.addClaim(new_claim, summary='added bishop-claim')

            if len(titular_bishopship_tr) > 0:
                for y in range(0, len(titular_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', titular_bishopship_tr[y])
                    if(len(dioceseid) > 0):
                        l_tbishop.append(dioceseid[0].decode('utf-8'))

                l_tbishop = list(set(l_tbishop))
                print(('-- Titular-Arch-Bishopship-Info: ' + ', '.join(l_tbishop)))
                for tbishop in l_tbishop:
                    mydiowd = dioid2wd(tbishop)

                    known_t2d = False

                    for known_tbishopship in l_known_tbishopships:
                        a_qualis = known_tbishopship.qualifiers
                        if not 'P708' in a_qualis:
                            continue
                        if (len(a_qualis['P708']) > 1):
                            print('-- !!! Take care there are more than 1 Dio-Claims!')
                            continue
                        diozese_claim = a_qualis['P708'][0]
                        trgt_d = diozese_claim.getTarget()
                        if (trgt_d.id == mydiowd):
                            print('-- Found titular-bishopship without already known and matching Diozese-Claim.')
                            known_t2d = True
                            continue

                    if (known_t2d == True):
                        continue

                    if (mydiowd != False and mydiowd != None):
                        if len(l_tbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP708\t" + mydiowd
                            item_properties += "\tS1047\t\"" + mycathid + "\"\t"

                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_tb = pywikibot.ItemPage(repo, 'Q948657')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_tb)
                            new_claim.addQualifier(target_dioclaim)
                            item.addClaim(new_claim, summary='added titular-bishopship-claim')
            bar.update(index)
            fq = open(path4qs, "a")
            fq.write(item_properties)
            fq.close()
            item_properties = ''

print('Done!' + "\n")
