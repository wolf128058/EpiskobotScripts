#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import requests

with open('cathid-no-rel-ref.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    changed = False

    claim_list_religion = itemdetails['claims']['P140']
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print '>> Catholic-Hierarchy-Id: ' + mycathid

    for rel_claim in claim_list_religion:
        trgt = rel_claim.getTarget()
        print '-- Claim for {} found.'.format(trgt.id)
        if trgt.id == 'Q9592':

            if changed == False:
                source_claim = pywikibot.Claim(repo, u'P1047')
                source_claim.setTarget(mycathid)
                rel_claim_sources = rel_claim.getSources()
                if len(rel_claim_sources) == 0:
                    r = requests.head(
                        'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html')
                    if r.status_code == 200:
                        print('-- Status 200 received for: ' +
                              'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html')
                        rel_claim.addSources(
                            [source_claim], summary=u'add catholic-hierarchy as source for religion')
                changed = True
print('Done!')
