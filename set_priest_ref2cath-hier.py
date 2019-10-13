#!/usr/bin/python3
# -*- coding: utf-8 -*-

import progressbar
import re

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


QUERY = '''
SELECT ?item ?itemLabel ?cathid WHERE {
  ?item wdt:P106 wd:Q250867;
    wdt:P1047 ?cathid.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS {
    ?item p:P106 _:b80.
    _:b80 ps:P106 ?relsub2;
      prov:wasDerivedFrom _:b30.
  })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birth)
LIMIT 1000'''

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
shuffle(generator)

repo = wikidata_site.data_repository()

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):
        itemdetails = item.get()
        mycathid = ''

        claim_list_position = itemdetails['claims']['P106']
        claim_list_cathid = itemdetails['claims']['P1047']

        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            print('>> Catholic-Hierarchy-Id: ' + mycathid)
            print('>> URL: https://www.wikidata.org/wiki/' + item.id)

        for rel_claim in claim_list_position:
            trgt = rel_claim.getTarget()
            print('-- Claim for {} found.'.format(trgt.id))
            if trgt.id == 'Q250867':

                rel_claim_sources = rel_claim.getSources()

                if len(rel_claim_sources) == 0:
                    chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
                    r = requests_retry_session().get(chorgurl)

                    if r.status_code != 200:
                        print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                        continue

                    try:
                        priest_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Ordained Priest</td>.*</tr>", r.content)
                    except:
                        priest_tr = []

                    if len(priest_tr) > 0:
                        print('-- Priest-Info: ' + priest_tr[0].decode('utf-8'))
                        source_claim = pywikibot.Claim(repo, 'P1047')
                        source_claim.setTarget(mycathid)
                        rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for position catholic-priest')
                    else:
                        print('-- No Priest-Ordination Data in table found. I skip.')
                        continue
        bar.update(index)
print('Done!')
