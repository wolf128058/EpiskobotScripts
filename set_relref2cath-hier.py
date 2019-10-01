#!/usr/bin/python3
# -*- coding: utf-8 -*-

import progressbar

import pywikibot
from pywikibot import pagegenerators as pg

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from random import shuffle


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


QUERY = """
SELECT ?item WHERE {
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
  ?item wdt:P1047 ?Katholische_Hierarchie_Personen_ID.
  ?item wdt:P140 wd:Q9592.
}
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
shuffle(generator)

repo = wikidata_site.data_repository()

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        itemdetails = item.get()
        mycathid = ''
        mywd_id = item.id
        print("\n" + '>> Checking WD-ID: ' + mywd_id)
        print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

        claim_list_religion = itemdetails['claims']['P140']
        claim_list_cathid = itemdetails['claims']['P1047']

        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-Id: ' + mycathid)

        for rel_claim in claim_list_religion:
            trgt = rel_claim.getTarget()
            print(('-- Claim for {} found.'.format(trgt.id)))
            if trgt.id == 'Q9592':
                rel_claim_sources = rel_claim.getSources()
                if len(rel_claim_sources) == 0:
                    r = requests_retry_session().head(chorgurl)
                    if r.status_code == 200:
                        print('-- Status 200 received for: ' + chorgurl)
                        source_claim = pywikibot.Claim(repo, 'P1047')
                        source_claim.setTarget(mycathid)
                        rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for religion')
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
                    if(cath_id_src == False):
                        r = requests_retry_session().head(chorgurl)
                        if r.status_code == 200:
                            print('-- Status 200 received for: ' + chorgurl)
                            source_claim = pywikibot.Claim(repo, 'P1047')
                            source_claim.setTarget(mycathid)
                            rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for religion')
        bar.update(index)
print('Done!')
