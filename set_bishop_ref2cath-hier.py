#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re

from random import shuffle

import progressbar

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import pywikibot
from pywikibot import pagegenerators as pg


import lxml.html


def requests_retry_session(retries=5, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
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
SELECT ?item ?itemLabel ?religion ?cathid ?rel2sub WHERE {
  ?item wdt:P39 wd:Q611644;
    wdt:P1047 ?cathid.
  FILTER(NOT EXISTS {
    ?item p:P39 _:b80.
    _:b80 ps:P39 ?relsub2;
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

        claim_list_position = itemdetails['claims']['P39']
        claim_list_cathid = itemdetails['claims']['P1047']

        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-Id: ' + mycathid)
            print('-- URL: ' + chorgurl)

        for rel_claim in claim_list_position:
            trgt = rel_claim.getTarget()
            print('-- Claim for {} found.'.format(trgt.id))
            if trgt.id == 'Q611644':
                source_claim = pywikibot.Claim(repo, 'P1047')
                source_claim.setTarget(mycathid)
                rel_claim_sources = rel_claim.getSources()

                if not rel_claim_sources:
                    t = lxml.html.parse(chorgurl)
                    mytitle = t.find(".//title").text

                    if mytitle.startswith('Bishop'):
                        print('-- Title match: "' + mytitle + '"')
                        rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for position catholic-bishop')
                    else:

                        r = requests_retry_session().get(chorgurl)
                        if r.status_code != 200:
                            print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                            continue

                        dio_bishopship_tr = re.findall(b'<tr><td[^>]+>.*</td><td>(Succeeded|Appointed|Ordained Bishop)</td><td>(Bishop of |Titular Bishop of )(.*)</td>.*</tr>', r.content)
                        if dio_bishopship_tr:
                            print('-- Table match: "' + dio_bishopship_tr[0][0].decode('iso-8859-1') + ', ' + dio_bishopship_tr[0][1].decode('iso-8859-1') + ', ' + dio_bishopship_tr[0][2].decode('iso-8859-1') + '"')
                            rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for position catholic-bishop')
                        else:
                            print('-- Not title match: "' + mytitle + '"')

        bar.update(index)

print('Done!')
