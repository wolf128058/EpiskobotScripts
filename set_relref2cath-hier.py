#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime
from random import shuffle

import progressbar

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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


QUERY = '''
SELECT ?item ?itemLabel ?religion ?cathid WHERE {
  ?item wdt:P140 wd:Q9592, ?religion;
    wdt:P1047 ?cathid.
  FILTER(NOT EXISTS {
    ?item p:P140 _:b80.
    _:b80 ps:P140 ?relsub2;
      prov:wasDerivedFrom _:b30.
  })
}
'''

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
shuffle(generator)
repo = wikidata_site.data_repository()

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):
        itemdetails = item.get(get_redirect=True)
        mycathid = ''
        mywd_id = item.id
        print("\n" + '>> Checking WD-ID: ' + mywd_id)
        print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

        claim_list_religion = itemdetails['claims']['P140']
        claim_list_cathid = itemdetails['claims']['P1047']

        now = datetime.datetime.utcnow()
        my_date4wd = pywikibot.WbTime(
            year=now.year,
            month=now.month,
            day=now.day,
            precision=11,
            calendarmodel='http://www.wikidata.org/entity/Q1985727')

        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-Id: ' + mycathid)
            print('-- URL: ' + chorgurl)

        for rel_claim in claim_list_religion:
            trgt = rel_claim.getTarget()
            print('-- Claim for {} found.'.format(trgt.id))
            if trgt.id == 'Q9592':
                rel_claim_sources = rel_claim.getSources()

                if len(rel_claim_sources) == 0:
                    r = requests_retry_session().head(chorgurl)
                    if r.status_code == 200:
                        print('-- Status 200 received for: ' + chorgurl)
                        source_claim_statedin = pywikibot.Claim(repo, 'P248')
                        source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                        source_claim_catid = pywikibot.Claim(repo, 'P1047')
                        source_claim_catid.setTarget(mycathid)
                        source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                        source_claim_retrieved.setTarget(my_date4wd)
                        rel_claim.addSources(
                            [source_claim_statedin, source_claim_catid, source_claim_retrieved],
                            summary='add catholic-hierarchy as source for religion')

                else:
                    cath_id_src = False
                    for rel_claim_source in rel_claim_sources:
                        print('-- Found claim for Religion')
                        try:
                            claimTarget = rel_claim_source['P1047']
                            cath_id_src = True
                            print('--- Cath-Id-Src found')
                        except:
                            print('--- Other than Cath-Id-Src found')

                    if cath_id_src == False:
                        r = requests_retry_session().head(chorgurl)
                        if r.status_code == 200:
                            print('-- Status 200 received for: ' + chorgurl)
                            source_claim_statedin = pywikibot.Claim(repo, 'P248')
                            source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                            source_claim_catid = pywikibot.Claim(repo, 'P1047')
                            source_claim_catid.setTarget(mycathid)
                            source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                            source_claim_retrieved.setTarget(my_date4wd)
                            rel_claim.addSources(
                                [source_claim_statedin, source_claim_catid, source_claim_retrieved],
                                summary='add catholic-hierarchy as source for religion')

        bar.update(index)

print('Done!')
