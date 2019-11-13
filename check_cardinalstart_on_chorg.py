#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re

import datetime
from datetime import datetime

from random import shuffle

import pywikibot
from pywikibot import pagegenerators as pg

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import progressbar


def requests_retry_session(
        retries=5,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?birthLabel ?cathid WHERE {
  ?item p:P39 ?position;
    wdt:P1047 ?cathid.
  ?position ps:P39 wd:Q45722.
  FILTER(NOT EXISTS { ?position pq:P580 ?start. })
}
"""
path4qs = 'log_quick_cardinalstarts.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
generator = list(generator)
shuffle(generator)
item_properties = ''
count_props = 0

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):
        mywd = item.get(get_redirect=True)
        mywd_id = item.id
        print("\n" + '>> Checking WD-ID: ' + mywd_id)
        print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

        claim_list_jobs = {}
        my_cardinal_claim = {}
        count_cardinaljobs = 0
        try:
            claim_list_jobs = mywd['claims']['P39']
            for job_item in claim_list_jobs:
                my_job_data = job_item.getTarget()
                if my_job_data.id == 'Q45722':
                    count_cardinaljobs += 1
                    my_cardinal_claim = my_job_data

            print('-- Found {} Job-Claims for Cardinal'.format(count_cardinaljobs))
        except:
            print('-- No Job for Cardinal found.')

        if count_cardinaljobs < 1:
            print('-- {} Job-Claims for Cardinal is to less. I skip.'.format(count_cardinaljobs))
            continue
        if count_cardinaljobs > 1:
            print('-- {} Job-Claims for Cardinal is to much. I skip.'.format(count_cardinaljobs))
            continue

        try:
            my_cardinal_claim_start = my_cardinal_claim['claims']['P580']
            print('-- Sorry, but we have a startdate set already. I skip.')
            continue

        except:
            print('-- No Startdate set. (yet...)')

        claim_list_cathid = mywd['claims']['P1047']
        for cathids in claim_list_cathid:
            data_found = False
            cardinal_tr_circa = []
            mycathid = cathids.getTarget()
            print('-- Catholic-Hierarchy-Id: ' + mycathid)
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-URL: ' + chorgurl)

            r = requests_retry_session().get(chorgurl)
            if r.status_code != 200:
                print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                continue

            try:
                cardinal_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Elevated to Cardinal</td>.*</tr>", r.content)
            except:
                cardinal_tr = []

            if cardinal_tr:
                print('-- Cardinal-Info: ' + cardinal_tr[0].decode('utf-8'))
                cardinal_tr = re.sub(r'\<[^\<]+>', '', cardinal_tr[0].decode('utf-8'))
                cardinal_tr_circa = re.findall(r"(.*)&", cardinal_tr.strip())
            else:
                print('-- No Cardinal-Ordination Data in table found. I skip.')

            if not cardinal_tr_circa and cardinal_tr:
                print('-- There is nice data as precise data.')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr.strip(), '%d %b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/11' + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                        data_found = True
                except:
                    if data_found == False:
                        print('- No valid startdate (precision day) found: "' + cardinal_tr + '"')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr.strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/10' + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                        data_found = True
                except:
                    if data_found == False:
                        print('- No valid startdate (precision month) found: "' + cardinal_tr + '"')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr.strip(), '%Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/9' + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                except:
                    if data_found == False:
                        print('- No valid startdate (precision year) found:Francesco Saverio Dracopoli "' + cardinal_tr + '"')

            elif(len(cardinal_tr_circa) > 0 and data_found == False):
                print('-- But there is nice data as circa data.')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr_circa[0].strip(), '%d %b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                        data_found = True
                except:
                    if data_found == False:
                        print('- No valid ~ startdate (precision day) found: "' + cardinal_tr_circa[0].strip() + '"')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr_circa[0].strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                        data_found = True
                except:
                    if data_found == False:
                        print('- No valid ~ startdate (precision month) found: "' + cardinal_tr_circa[0].strip() + '"')

                try:
                    if data_found == False:
                        cardinalstart_datetime = datetime.strptime(cardinal_tr_circa[0].strip(), '%Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ45722\tP580\t+" + cardinalstart_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                        data_found = True
                except:
                    if data_found == False:
                        print('- No valid ~ startdate (precision day) found: "' + cardinal_tr_circa[0].strip() + '"')
        bar.update(index)
        fq = open(path4qs, "a")
        fq.write(item_properties)
        fq.close()
        item_properties = ''

print('Done!' + "\n")
