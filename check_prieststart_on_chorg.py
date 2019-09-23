#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html
import re
import requests
import json

import datetime
from datetime import datetime

from pprint import pprint


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathid WHERE {
  ?item p:P106 ?job;
    wdt:P1047 ?cathid.
  ?job ps:P106 wd:Q250867.
  OPTIONAL { ?item wdt:P569 ?birth. }
  FILTER(NOT EXISTS { ?job pq:P580 ?start. })
  FILTER(EXISTS { ?item p:P1047 ?statement. })
  FILTER((YEAR(?birth)) >= 1584 )
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY RAND()
# ORDER BY (?birthLabel)
LIMIT 5000
"""
path4qs = 'log_quick_prieststarts.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
item_properties = ''
count_props = 0


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
        data_found = False
        priest_tr_circa = []
        priest_tr = []
        mycathid = cathids.getTarget()
        print '-- Catholic-Hierarchy-Id: ' + mycathid
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
        print '-- Catholic-Hierarchy-URL: ' + chorgurl

        r = requests.get(chorgurl)
        if r.status_code != 200:
            print '### HTTP-ERROR ON cath-id: ' + chorgurl
            continue

        try:
            priest_tr = re.findall(r"\<tr\>\<td[^\>]+\>(.*)\<\/td\>\<td\>.*\<\/td\>\<td\>Ordained Priest\<\/td\>.*\<\/tr\>", r.content)
        except:
            priest_tr = []

        if len(priest_tr) > 0:
            print '-- Priest-Info: ' + priest_tr[0]
            priest_tr = re.sub(r'\<[^\<]+>', '', priest_tr[0])
            priest_tr_circa = re.findall(r"(.*)&", priest_tr.strip())
        else:
            print '-- No Priest-Ordination Data in table found. I skip.'

        if len(priest_tr_circa) == 0 and len(priest_tr) > 0:
            print '-- There is nice data as precise data.'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr.strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/11'
                    count_props += 1
                    data_found = True
            except:
                if data_found == False:
                    print '- No valid startdate (precision day) found: "' + priest_tr + '"'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr.strip(), '%b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/10'
                    count_props += 1
                    data_found = True
            except:
                if data_found == False:
                    print '- No valid startdate (precision month) found: "' + priest_tr + '"'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr.strip(), '%Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/9'
                    count_props += 1
            except:
                if data_found == False:
                    print '- No valid startdate (precision year) found:Francesco Saverio Dracopoli "' + priest_tr + '"'

        elif(len(priest_tr_circa) > 0 and data_found == False):
            print '-- But there is nice data as circa data.'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr_circa[0].strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902"
                    count_props += 1
                    data_found = True
            except:
                if data_found == False:
                    print '- No valid ~ startdate (precision day) found: "' + priest_tr_circa[0].strip() + '"'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr_circa[0].strip(), '%b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902"
                    count_props += 1
                    data_found = True
            except:
                if data_found == False:
                    print '- No valid ~ startdate (precision month) found: "' + priest_tr_circa[0].strip() + '"'

            try:
                if data_found == False:
                    prieststart_datetime = datetime.strptime(priest_tr_circa[0].strip(), '%Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ250867\tP580\t+" + prieststart_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902"
                    count_props += 1
                    data_found = True
            except:
                if data_found == False:
                    print '- No valid ~ startdate (precision day) found: "' + priest_tr_circa[0].strip() + '"'

    fq = open(path4qs, "a")
    fq.write(item_properties)
    fq.close()
    item_properties = ''

print('Done!' + "\n")
