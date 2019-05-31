#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

with open('bishop_catholicism.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

# print(QUERY)

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()

    claim_list = itemdetails["claims"]["P140"]
    for claim in claim_list:
        trgt = claim.getTarget()
        print("Claim for {} found.".format(trgt.id))
        if trgt.id == 'Q1841':
            correct_page = pywikibot.ItemPage(repo, "Q9592", 0)
            claim.changeTarget(correct_page, summary=u'catholic bishop of r.catholic religion (not only catholicism)')
