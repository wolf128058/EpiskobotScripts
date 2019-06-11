#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html

with open('cathid-no-rel-archbishop.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

# print(QUERY)

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    changed=False

    claim_list_position = itemdetails['claims']['P39']
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print '>> Catholic-Hierarchy-Id: ' + mycathid

    for rel_claim in claim_list_position:
        trgt = rel_claim.getTarget()
        print '-- Claim for {} found.'.format(trgt.id)
        if trgt.id == 'Q48629921':

            if changed == False:
                source_claim = pywikibot.Claim(repo, u'P1047')
                source_claim.setTarget(mycathid)
                rel_claim_sources = rel_claim.getSources()

                if len(rel_claim_sources) == 0:
                     t = lxml.html.parse('http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html')
                     mytitle = t.find(".//title").text

                     if mytitle.startswith('Archbishop'):
                         print('-- Title match: "' + mytitle + '"')
                         rel_claim.addSources([source_claim], summary=u'add catholic-hierarchy as source for position catholic-archbishop')
                changed=True
print('Done!')

