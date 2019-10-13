#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re


import pywikibot
from pywikibot import pagegenerators as pg

import requests
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
            item.get()
            print('--- WD-Item-4-Diocese found: ' + item.id)
            return item.id

    except:
        print('!!! query for diocese failed.')
        return False


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathiLabel WHERE {
  ?item wdt:P39 wd:Q611644;
    wdt:P1047 ?cathi.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER((YEAR(?birth)) >= 0 )
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q75178. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birthLabel)
LIMIT 5000
"""
path4qs = 'log_quick_auxbishopships.txt'
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

        claim_list_cathid = mywd['claims']['P1047']

        claim_list_jobs = mywd['claims']['P39']

        bAlreadySet = False
        for jobclaim in claim_list_jobs:
            myjob = jobclaim.getTarget()
            myjob_id = myjob.id
            print('----- JOB-WD-ID: ' + myjob_id)
            if myjob_id == 'Q75178':
                qualifiers = jobclaim.qualifiers
                for qualifier in qualifiers:
                    if qualifier == 'P708':
                        bAlreadySet = True

        if bAlreadySet == True:
            print('--aux bishopship already set. i skip that candidate')
            continue
        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            print('-- Catholic-Hierarchy-Id: ' + mycathid)
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-URL: ' + chorgurl)

            r = requests_retry_session().get(chorgurl)
            if r.status_code != 200:
                print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                continue

            aux_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Auxiliary Bishop of (.*)</td>.*</tr>", r.content)

            l_auxbishop = []

            if len(aux_bishopship_tr) > 0:
                for x in range(0, len(aux_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', aux_bishopship_tr[x])
                    if len(dioceseid) > 0:
                        l_auxbishop.append(dioceseid[0].decode('utf-8'))
                l_auxbishop = list(set(l_auxbishop))
                print('-- Aux-Bishopship-Info: ' + ', '.join(l_auxbishop))
                for auxbishop in l_auxbishop:
                    mydiowd = dioid2wd(auxbishop)
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
                            item.addClaim(new_claim, summary='added auxbishopship-claim')
            bar.update(index)
            fq = open(path4qs, "a")
            fq.write(item_properties)
            fq.close()
            item_properties = ''


print('Done!' + "\n")
