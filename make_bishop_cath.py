#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

QUERY = '''
SELECT ?item WHERE {
  ?item wdt:P39 wd:Q611644
  FILTER(NOT EXISTS { ?item wdt:P140 ?statement. })
  FILTER(EXISTS { ?item wdt:P1047 ?statement. })
}
'''

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:

    itemdetails = item.get(get_redirect=True)
    mypage = pywikibot.ItemPage(repo, item.id)
    claim = pywikibot.Claim(repo, 'P140')
    target = pywikibot.ItemPage(repo, 'Q9592')
    claim.setTarget(target)
    item.addClaim(claim,
                  summary='catholic bishop of r.catholic religion')
