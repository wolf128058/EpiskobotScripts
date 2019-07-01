#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html

QUERY = """
SELECT ?item ?itemLabel ?religion ?cathid ?rel2sub WHERE {
  ?item wdt:P39 wd:Q48629921;
    wdt:P140 wd:Q9592, ?religion;
    wdt:P1047 ?cathid.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS {
    ?item p:P39 _:b80.
    _:b80 ps:P39 ?relsub2;
      prov:wasDerivedFrom _:b30.
  })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birth)
LIMIT 5000
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

# print(QUERY)

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    changed = False

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
                changed = True
print('Done!')
