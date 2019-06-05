#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

with open('cathid-no-rel-ref.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

# print(QUERY)

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    changed=False

    claim_list_religion = itemdetails['claims']['P140']
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print '>> Catholic-Hierarchy-Id: ' + mycathid

    for claim in claim_list_religion:
        trgt = claim.getTarget()
        print '-- Claim for {} found.'.format(trgt.id)
        if trgt.id == 'Q9592':
            # print claim
            ref_claim = claim.fromJSON(repo, {
                u'type': u'statement',
                u'references': [{u'snaks': {u'P1047': [{
                    u'datatype': u'external-id',
                    u'datavalue': {u'type': u'string',
                                   u'value': mycathid},
                    u'property': u'P1047',
                    u'snaktype': u'value',
                    }]}, u'hash': None, u'snaks-order': [u'P1047']}],
                u'mainsnak': {
                    u'datatype': u'wikibase-item',
                    u'datavalue': {u'type': u'wikibase-entityid',
                                   u'value': {u'entity-type': u'item',
                                   u'numeric-id': 9592}},
                    u'property': u'P140',
                    u'snaktype': u'value',
                    },
                u'rank': u'normal',
                })

            correct_page = pywikibot.ItemPage(repo, 'Q9592', 0)
            if changed == False:
                item.removeClaims(claim)
                item.addClaim(ref_claim, summary=u' add catholic-hierarchy as source for religion')
                changed=True
print('Done!')

