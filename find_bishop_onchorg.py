#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import os
from os import system

import lxml
from lxml import html

import re
import requests

path4qs = 'log_quick_bishops_found.txt'

QUERY = """
SELECT ?item WHERE {
  ?item wdt:P1047 ?value.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q65924966. })  
  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q611644 })
#  FILTER(NOT EXISTS { ?item wdt:P39 wd:Q48629921 })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en". }
}
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    bishop_wd_id = item.id
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        if len(mycathid) == 0:
            continue
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

        try:
            r = requests.head(chorgurl)
        except:
            continue

        if r.status_code != 200:
            print('### ERROR ON cath-id: ' + mycathid)
        if r.status_code == 200:
            print('')
            print('>> Catholic-Hierarchy-Id: ' + mycathid)
            print('-- CH-URL: ' + chorgurl)

            try:
                t = lxml.html.parse(chorgurl)
            except:
                continue

            mytitle = t.find(".//title").text
            mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
            print('-- Title: ' + mytitle)
            print('-- WD-URL: https://www.wikidata.org/wiki/' + bishop_wd_id)
            claim_list_positions = []
            is_tagged_bishop = False
            is_tagged_archbishop = False

            try:
                claim_list_positions = itemdetails['claims']['P39']
            except:
                print('-- This one has no position held (P39)')

            for claim_list_position in claim_list_positions:
                pos_detail = claim_list_position.getTarget()
                pos_id = pos_detail.id
                print('-- POS-Found: ' + pos_id)
                if (pos_id == 'Q611644'):
                    is_tagged_bishop = True
                elif (pos_id == 'Q48629921'):
                    is_tagged_archbishop = True

            if mytitle.startswith('Bishop '):
                print(('-- Title match "Bishop": "' + mytitle + '"'))

                for claim_list_position in claim_list_positions:
                    pos_detail = claim_list_position.getTarget()
                    pos_id = pos_detail.id
#                    if (pos_id == 'Q29182'):
#                        correct_page = pywikibot.ItemPage(repo, "Q611644", 0)
#                        claim_list_position.changeTarget(correct_page, summary=u'a bishop of r.catholic religion with matching entry on CH is a catholic bishop.')
#                        is_tagged_bishop = True
#                        print('-- Bishop had to be catholicised')

                if (is_tagged_bishop == False):
                    fq = open(path4qs, "a")
                    fq.write("\n" + bishop_wd_id + "\tP39\tQ611644\tS1047\t\"" + mycathid + "\"")
                    fq.close()
                    print('-- Bishop is on your list.')

            if mytitle.startswith('Archbishop '):
                print(('-- Title match "Archbishop": "' + mytitle + '"'))

                for claim_list_position in claim_list_positions:
                    pos_detail = claim_list_position.getTarget()
                    pos_id = pos_detail.id
#                    if (pos_id == 'Q49476'):
#                        correct_page = pywikibot.ItemPage(repo, "Q48629921", 0)
#                        claim_list_position.changeTarget(correct_page, summary=u'a archbishop of r.catholic religion with matching entry on CH is a catholic archbishop.')
#                        is_tagged_archbishop = True
#                        print('-- Archbishop had to be catholicised')

                if (is_tagged_archbishop == False):
                    fq = open(path4qs, "a")
                    fq.write("\n" + bishop_wd_id + "\tP39\tQ48629921\tS1047\t\"" + mycathid + "\"")
                    fq.close()
                    print('-- Archbishop is on your list.')


print('Done!')
