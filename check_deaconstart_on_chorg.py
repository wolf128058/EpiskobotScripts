#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re

from random import shuffle

import datetime
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

import progressbar

import pywikibot
from pywikibot import pagegenerators as pg


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
SELECT ?item ?itemLabel ?cathid WHERE {
  ?item p:P106 ?position;
    wdt:P1047 ?cathid.
  ?position ps:P106 wd:Q25393460.
  FILTER(NOT EXISTS { ?position pq:P580 ?start. })
}
"""
path4qs = 'data/log_quick_deaconstarts.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
generator = list(generator)
shuffle(generator)
item_properties = ''
count_props = 0

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):
        bar.update(index)
        mywd = item.get(get_redirect=True)
        mywd_id = item.id
        print("\n" + '>> Checking WD-ID: ' + mywd_id)
        print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

        claim_list_pos = {}
        my_cathdeacon_claim = {}
        count_deaconpos = 0
        try:
            claim_list_pos = mywd['claims']['P106']
            for pos_item in claim_list_pos:
                my_pos_data = pos_item.getTarget()
                if my_pos_data.id == 'Q25393460':
                    count_deaconpos += 1
                    my_cathdeacon_claim = my_pos_data

            print('-- Found {} Position-Claims for Catholic deacon'.format(count_deaconpos))
        except:
            print('-- No Position for Catholic-deacon found.')

        if not count_deaconpos:
            print('-- {} Position-Claims for Catholic deacon is to less. I skip.'.format(count_deaconpos))
            continue
        if count_deaconpos > 1:
            print('-- {} Position-Claims for Catholic deacon is to much. I skip.'.format(count_deaconpos))
            continue

        try:
            my_cathdeacon_claim_start = my_cathdeacon_claim['claims']['P580']
            print('-- Sorry, but we have a startdate set already. I skip.')
            continue

        except:
            print('-- No Startdate set. (yet...)')

        claim_list_cathid = mywd['claims']['P1047']
        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            print('-- Catholic-Hierarchy-Id: ' + mycathid)
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('-- Catholic-Hierarchy-URL: ' + chorgurl)

            r = requests_retry_session().get(chorgurl)
            if r.status_code != 200:
                print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                continue

            deacon_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>.*</td><td>Ordained Deacon</td>.*</tr>', r.content)
            if not deacon_tr:
                deacon_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>Ordained Deacon</td>.*</tr>', r.content)
            if deacon_tr:
                print('-- deacon-Info: ' + deacon_tr[0].decode('utf-8'))

                deacon_tr_clean = ''
                if isinstance(deacon_tr[0].decode('utf-8'), str):
                    deacon_tr_clean = re.sub(r'\<[^\<]+\>', '', deacon_tr[0].decode('utf-8'))
                if isinstance(deacon_tr[0], str):
                    deacon_tr_clean = re.sub(r'\<[^\<]+\>', '', deacon_tr[0])

                print('-- deacon-Info-Clean: ' + deacon_tr_clean)

                deacon_tr_circa = re.findall(r'(.*)&', deacon_tr_clean)
            else:
                print('-- No deacon-Ordination Data in table found. I skip.')
                continue

            if not deacon_tr_circa:

                try:
                    deaconstart_datetime = datetime.strptime(deacon_tr_clean.strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/11' + "\tS1047\t\"" + mycathid + "\"\t"
                    count_props += 1
                except:
                    print('- No valid startdate (precision day) found: "' + deacon_tr_clean + '"')
                    try:
                        deaconstart_datetime = datetime.strptime(deacon_tr_clean.strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/10' + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                    except:
                        print('- No valid startdate (precision month) found: "' + deacon_tr_clean + '"')
                        try:
                            deaconstart_datetime = datetime.strptime(deacon_tr_clean.strip(), '%Y')
                            item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/9' + "\tS1047\t\"" + mycathid + "\"\t"
                            count_props += 1
                        except:
                            print('- No valid startdate (precision year) found: "' + deacon_tr_clean + '"')

            else:
                try:
                    deaconstart_datetime = datetime.strptime(deacon_tr_circa[0].strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                    count_props += 1
                except:
                    print('- No valid ~startdate (precision day) found: "' + deacon_tr_circa[0].strip() + '"')
                    try:
                        deaconstart_datetime = datetime.strptime(deacon_tr_circa[0].strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                    except:
                        print('- No valid ~startdate (precision month) found: "' + deacon_tr_circa[0].strip() + '"')
                        try:
                            deaconstart_datetime = datetime.strptime(deacon_tr_circa[0].strip(), '%Y')
                            item_properties += "\n" + mywd_id + "\tP106\tQ25393460\tP580\t+" + deaconstart_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                            count_props += 1
                        except:
                            print('- No valid ~startdate (precision year) found: "' + deacon_tr_circa[0].strip() + '"')
        fq = open(path4qs, "a")
        fq.write(item_properties)
        fq.close()
        item_properties = ''

print('Done!' + "\n")
