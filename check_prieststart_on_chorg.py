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
  ?item p:P106 ?job;
    wdt:P1047 ?cathid.
  ?job ps:P106 wd:Q250867.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?job pq:P580 ?start. })
  FILTER(EXISTS { ?item p:P1047 ?statement. })
  FILTER((YEAR(?birth)) >= 0 )
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY DESC (?birthLabel)
LIMIT 1000
"""
path4qs = 'log_quick_prieststarts.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
item_properties = ''


for item in generator:
    mywd = item.get()
    mywd_id = item.id
    print "\n" + '>> Checking WD-ID: ' + mywd_id
    print '-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id

    claim_list_jobs = {}
    my_cathpriest_claim = {}
    count_priestjobs = 0
    try:
        claim_list_jobs = mywd['claims']['P106']
        for job_item in claim_list_jobs:
            my_job_data = job_item.getTarget()
            if my_job_data.id == 'Q250867':
                count_priestjobs += 1
                my_cathpriest_claim = my_job_data

        print '-- Found {} Job-Claims for Catholic Priest'.format(count_priestjobs)
    except:
        print '-- No Job for Catholic Priest found.'

    if(count_priestjobs < 1):
        print '-- {} Job-Claims for Catholic Priest is to less. I skip.'.format(count_priestjobs)
        continue
    if(count_priestjobs > 1):
        print '-- {} Job-Claims for Catholic Priest is to much. I skip.'.format(count_priestjobs)
        continue

    try:
        my_cathpriest_claim_start = my_cathpriest_claim['claims']['P580']
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

        priest_tr = re.findall(r"\<tr\>\<td[^\>]+\>(.*)\<\/td\>\<td\>.*\<\/td\>\<td\>Ordained Priest\<\/td\>.*\<\/tr\>", r.content)
        if len(priest_tr) > 0:
            print '-- Priest-Info: ' + priest_tr[0]
            priest_tr = re.sub(r'\<[^\<]+>', '', priest_tr[0])
            priest_tr_circa = re.findall(r"(.*)&sup[0-9];", priest_tr.strip())
        else:
            print '-- No Priest-Ordination Data in table found. I skip.'
            continue

        if len(priest_tr_circa) == 0:
            prieststart_datetime = datetime.strptime(priest_tr, '%d %b %Y')

            try:
                prieststart_datetime = datetime.strptime(priest_tr, '%d %b %Y')
                item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/11'
            except:
                print '- No valid startdate (precision day) found: "' + priest_tr + '"'
                try:
                    prieststart_datetime = datetime.strptime(priest_tr, '%b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/10'
                except:
                    print '- No valid startdate (precision month) found: "' + priest_tr + '"'
                    try:
                        prieststart_datetime = datetime.strptime(priest_tr, '%Y')
                        item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/9'
                    except:
                        print '- No valid startdate (precision year) found: "' + priest_tr + '"'


fq = open(path4qs, "a")
fq.write(item_properties)
fq.close()

print('Done!' + "\n")
