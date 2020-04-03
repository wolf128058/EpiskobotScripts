#!/usr/bin/python3
# -*- coding: utf-8 -*-


import re

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import progressbar

import pywikibot
from pywikibot import pagegenerators as pg


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
            item.get(get_redirect=True)
            print('--- WD-Item-4-Diocese found: ' + item.id)
            return item.id
    except:
        print('!!! query for diocese failed.')
        return False


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathiLabel WHERE {
  ?item wdt:P39 wd:Q48629921;
    wdt:P1047 ?cathi.
  BIND(wd:Q48629921 AS ?archbishopship)
  FILTER(NOT EXISTS { ?archbishopship pq:P708 ?statement. })
  OPTIONAL { ?item wdt:P569 ?birth. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
"""
path4qs = 'data/log_quick_archbishop2diocese.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
generator = list(generator)

repo = wikidata_site.data_repository()

item_properties = ''
count_props = 0

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        bar.update(index)
        mywd = item.get(get_redirect=True)
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
            if(myjob_id == 'Q48629921' or myjob_id == 'Q50362553'):
                qualifiers = jobclaim.qualifiers
                for qualifier in qualifiers:
                    if qualifier == 'P708':
                        bAlreadySet = True

        if bAlreadySet == True:
            print('-- diocesan or titular archbishopship already set. i skip that candidate')
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

            diocesan_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Archbishop of (.*)</td>.*</tr>", r.content)
            titular_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Titular Archbishop of (.*)</td>.*</tr>", r.content)

            l_dbishop = []
            l_tbishop = []

            if diocesan_bishopship_tr:
                for x in range(0, len(diocesan_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', diocesan_bishopship_tr[x])
                    if dioceseid:
                        l_dbishop.append(dioceseid[0].decode('utf-8'))
                l_dbishop = list(set(l_dbishop))
                print('-- Diocesan-Arch-Bishopship-Info: ' + ', '.join(l_dbishop))
                for dbishop in l_dbishop:
                    mydiowd = dioid2wd(dbishop)
                    if (mydiowd != False and mydiowd != None):
                        if len(l_dbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ48629921\tP708\t" + mydiowd + "\tS1047\t\"" + mycathid + "\"\t"
                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_db = pywikibot.ItemPage(repo, 'Q48629921')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_db)
                            new_claim.addQualifier(target_dioclaim)
                            item.addClaim(new_claim, summary='added archbishop-claim')

            if titular_bishopship_tr:
                for y in range(0, len(titular_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', titular_bishopship_tr[y])
                    if dioceseid:
                        l_tbishop.append(dioceseid[0].decode('utf-8'))

                l_tbishop = list(set(l_tbishop))
                print('-- Titular-Arch-Bishopship-Info: ' + ', '.join(l_tbishop))
                for tbishop in l_tbishop:
                    mydiowd = dioid2wd(tbishop)
                    if (mydiowd != False and mydiowd != None):
                        if len(l_tbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ50362553\tP708\t" + mydiowd + "\tS1047\t\"" + mycathid + "\"\t"
                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_tb = pywikibot.ItemPage(repo, 'Q50362553')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_tb)
                            new_claim.addQualifier(target_dioclaim)
                            item.addClaim(new_claim, summary='added titular-archbishopship-claim')

        fq = open(path4qs, "a")
        fq.write(item_properties)
        fq.close()
        item_properties = ''
# eof


print('Done!' + "\n")
