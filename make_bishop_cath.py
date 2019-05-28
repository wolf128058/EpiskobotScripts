#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

with open('bishop_non_cath.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

# print(QUERY)

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:

    itemdetails = item.get()
    mypage = pywikibot.ItemPage(repo, item.id)
    claim = pywikibot.Claim(repo, u'P140')
    target = pywikibot.ItemPage(repo, u'Q9592')
    claim.setTarget(target)
    item.addClaim(claim,
                  summary=u'catholic bishop of r.catholic religion')

