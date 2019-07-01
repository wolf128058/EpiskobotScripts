#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html
import re
import requests

import datetime
from datetime import datetime

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathid WHERE {
  ?item p:P39 ?position;
    wdt:P1047 ?cathid.
  ?position ps:P39 wd:Q611644.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?position pq:P580 ?start. })
  FILTER(EXISTS { ?item p:P1047 ?statement. })
  FILTER((YEAR(?birth)) >= 0 )
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birthLabel)
LIMIT 1000
"""
path4qs = 'log_quick_bishopstarts.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
item_properties = ''


for item in generator:
    mywd = item.get()
    mywd_id = item.id
    print "\n" + '>> Checking WD-ID: ' + mywd_id
    print '-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id

    claim_list_pos = {}
    my_cathbishop_claim = {}
    count_bishoppos = 0
    try:
        claim_list_pos = mywd['claims']['P39']
        for pos_item in claim_list_pos:
            my_pos_data = pos_item.getTarget()
            if my_pos_data.id == 'Q611644':
                count_bishoppos += 1
                my_cathbishop_claim = my_pos_data

        print '-- Found {} Position-Claims for Catholic Bishop'.format(count_bishoppos)
    except:
        print '-- No Position for Catholic-Bishop found.'

    if(count_bishoppos < 1):
        print '-- {} Position-Claims for Catholic Bishop is to less. I skip.'.format(count_bishoppos)
        continue
    if(count_bishoppos > 1):
        print '-- {} Position-Claims for Catholic Bishop is to much. I skip.'.format(count_bishoppos)
        continue

    try:
        my_cathbishop_claim_start = my_cathbishop_claim['claims']['P580']
        print '-- Sorry, but we have a startdate set already. I skip.'
        continue

    except:
        print '-- No Startdate set. (yet...)'

    claim_list_cathid = mywd['claims']['P1047']
    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print '-- Catholic-Hierarchy-Id: ' + mycathid
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
        print '-- Catholic-Hierarchy-URL: ' + chorgurl

        r = requests.get(chorgurl)
        if r.status_code != 200:
            print '### HTTP-ERROR ON cath-id: ' + chorgurl
            continue

        bishop_tr = re.findall(r"\<tr\>\<td[^\>]+\>(.*)\<\/td\>\<td\>.*\<\/td\>\<td\>Ordained Bishop\<\/td\>.*\<\/tr\>", r.content)
        if len(bishop_tr) > 0:
            print '-- Bishop-Info: ' + bishop_tr[0]
            bishop_tr = re.sub(r'\<[^\<]+>', '', bishop_tr[0])
            bishop_tr_circa = re.findall(r"(.*)&sup[0-9];", bishop_tr.strip())
        else:
            print '-- No Bishop-Ordination Data in table found. I skip.'
            continue

        if len(bishop_tr_circa) == 0:
            bishopstart_datetime = datetime.strptime(bishop_tr, '%d %b %Y')

            try:
                bishopstart_datetime = datetime.strptime(bishop_tr, '%d %b %Y')
                item_properties += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/11'
            except:
                print '- No valid startdate (precision day) found: "' + bishop_tr + '"'
                try:
                    bishopstart_datetime = datetime.strptime(bishop_tr, '%b %Y')
                    item_properties += "\n" + mywd_id + "\tP39\tQ250867\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/10'
                except:
                    print '- No valid startdate (precision month) found: "' + bishop_tr + '"'
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr, '%Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ250867\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/9'
                    except:
                        print '- No valid startdate (precision year) found: "' + bishop_tr + '"'


fq = open(path4qs, "a")
fq.write(item_properties)
fq.close()

print('Done!' + "\n")
