#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg
import requests
import re

QUERY = '''
SELECT ?item ?itemLabel ?cathid WHERE {
  ?item wdt:P39 wd:Q45722;
    wdt:P1047 ?cathid.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS {
    ?item p:P39 _:b80.
    _:b80 ps:P39 ?relsub2;
      prov:wasDerivedFrom _:b30.
  })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birth)'''

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
        print(('>> Catholic-Hierarchy-Id: ' + mycathid))

    for rel_claim in claim_list_position:
        trgt = rel_claim.getTarget()
        print(('-- Claim for {} found.'.format(trgt.id)))
        if trgt.id == 'Q45722':

            if changed == False:

                rel_claim_sources = rel_claim.getSources()

                if len(rel_claim_sources) == 0:
                    chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
                    r = requests.get(chorgurl)

                    if r.status_code != 200:
                        print(('### HTTP-ERROR ON cath-id: ' + chorgurl))
                        continue

                    try:
                        cardinal_tr = re.findall(r"\<tr\>\<td[^\>]+\>(.*)\<\/td\>\<td\>.*\<\/td\>\<td\>Elevated to Cardinal\<\/td\>.*\<\/tr\>", r.content)
                    except:
                        cardinal_tr = []

                    if len(cardinal_tr) > 0:
                        print(('-- Cardinal-Info: ' + cardinal_tr[0]))
                        source_claim = pywikibot.Claim(repo, 'P1047')
                        source_claim.setTarget(mycathid)
                        rel_claim.addSources([source_claim], summary='add catholic-hierarchy as source for position cardinal')
                    else:
                        print('-- No Priest-Ordination Data in table found. I skip.')
                        continue
                changed = True

print('Done!')
