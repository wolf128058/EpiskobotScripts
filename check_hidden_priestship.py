#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html
import re
import requests


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathiLabel ?jobLabel WHERE {
  ?item wdt:P1047 ?cathi.
  OPTIONAL { ?item wdt:P569 ?birth. }
  OPTIONAL { ?item wdt:P106 ?job. }
  FILTER(NOT EXISTS { ?item wdt:P106 wd:Q250867. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
LIMIT 5000
"""

path4qs = 'log_quick_hiddenpriestships.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
repo = wikidata_site.data_repository()
item_properties = ''
count_props = 0


for item in generator:
    mywd = item.get()
    mywd_id = item.id
    print "\n" + '>> Checking WD-ID: ' + mywd_id
    print '-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id

    claim_list_pos = {}
    my_cathbishop_claim = {}
    count_bishoppos = 0

    claim_list_cathid = mywd['claims']['P1047']
    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print '-- Catholic-Hierarchy-Id: ' + mycathid
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
        print '-- Catholic-Hierarchy-URL: ' + chorgurl

        r = requests.get(chorgurl, timeout=10)
        if r.status_code != 200:
            print '### HTTP-ERROR ON cath-id: ' + chorgurl
            continue
        priestship_tr = re.findall(r"\<tr\>\<td[^\>]+\>.*\<\/td\>\<td\>.*\<\/td\>\<td\>Ordained Priest\<\/td\>.*\<\/tr\>", r.content)

        l_dbishop = []
        l_known_priestships = []

        try:
            claim_list_currentjobs = mywd['claims']['P106']
        except:
            claim_list_currentjobs = []

        for single_pos in claim_list_currentjobs:
            trgt_pos = single_pos.getTarget()
            if trgt_pos.id == 'Q250867':
                l_known_priestships.append(single_pos)

        if (len(l_known_priestships) > 0):
            print('-- Found {} Job-Claims for Priestships on WD'.format(len(l_known_priestships)))

        if (len(priestship_tr) > 0):
            print('-- Found {} Job-Claims for Priestships on CH'.format(len(priestship_tr)))

        if (len(priestship_tr) > 0 and len(l_known_priestships) == 0):
            item_properties += "\n" + mywd_id + "\tP106\tQ250867"
            item_properties += "\tS1047\t\"" + mycathid + "\"\t"

        fq = open(path4qs, "a")
        fq.write(item_properties)
        fq.close()
        item_properties = ''

print('Done!' + "\n")
