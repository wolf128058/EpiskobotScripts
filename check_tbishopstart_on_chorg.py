#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
from random import shuffle

import datetime
from datetime import datetime

from urllib import parse

import urllib.parse

import json

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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
  ?item p:P39 ?position;
    wdt:P1047 ?cathid.
  ?position ps:P39 wd:Q948657.
  FILTER(NOT EXISTS { ?position pq:P580 ?start. })
}
"""
path4qs = 'data/log_quick_tbishopstarts.txt'
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
        my_cathbishop_claim = {}
        count_bishoppos = 0
        try:
            claim_list_pos = mywd['claims']['P39']
            for pos_item in claim_list_pos:
                my_pos_data = pos_item.getTarget()
                if my_pos_data.id == 'Q948657':
                    count_bishoppos += 1
                    my_cathbishop_claim = my_pos_data

            print('-- Found {} Position-Claims for Titularbishopship'.format(count_bishoppos))
        except:
            print('-- No Position for Catholic-Bishop found.')

        if not count_bishoppos:
            print('-- {} Position-Claims for Titularbishopship is to less. I skip.'.format(count_bishoppos))
            continue
        if count_bishoppos > 1:
            print('-- {} Position-Claims for Titularbishopship is to much. I skip.'.format(count_bishoppos))
            continue

        try:
            my_cathbishop_claim_start = my_cathbishop_claim['claims']['P580']
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

            bishop_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>.*</td><td>Appointed</td><td>Titular Bishop .*</td>.*</tr>', r.content)
            if not bishop_tr:
                bishop_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>Appointed</td><td>Titular Bishop .*</td>.*</tr>', r.content)
            if bishop_tr:
                print('-- Bishop-Info: ' + bishop_tr[0].decode('utf-8'))

                bishop_tr_clean = ''
                if isinstance(bishop_tr[0].decode('utf-8'), str):
                    bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0].decode('utf-8'))
                    bishop_tr_clean = bishop_tr_clean.strip(' ')
                if isinstance(bishop_tr[0], str):
                    bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0])
                    bishop_tr_clean = bishop_tr_clean.strip(' ')

                print('-- Bishop-Info-Clean: ' + bishop_tr_clean)

                bishop_tr_circa = re.findall(r'(.*)&', bishop_tr_clean)
            else:
                print('-- No Bishop-Ordination Data in table found. I skip.')
                continue

            if not bishop_tr_circa:

                try:
                    bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/11' + "\tS1047\t\"" + mycathid + "\"\t"
                    count_props += 1
                except:
                    print('- No valid startdate (precision day) found: "' + bishop_tr_clean + '"')
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/10' + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                    except:
                        print('- No valid startdate (precision month) found: "' + bishop_tr_clean + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%Y')
                            item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/9' + "\tS1047\t\"" + mycathid + "\"\t"
                            count_props += 1
                        except:
                            print('- No valid startdate (precision year) found: "' + bishop_tr_clean + '"')

            else:
                try:
                    bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%d %b %Y')
                    item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                    count_props += 1
                except:
                    print('- No valid ~startdate (precision day) found: "' + bishop_tr_circa[0].strip() + '"')
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%b %Y')
                        item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        count_props += 1
                    except:
                        print('- No valid ~startdate (precision month) found: "' + bishop_tr_circa[0].strip() + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%Y')
                            item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP580\t+" + bishopstart_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                            count_props += 1
                        except:
                            print('- No valid ~startdate (precision year) found: "' + bishop_tr_circa[0].strip() + '"')

        if count_props % 140 == 0 or count_props == len(generator):

            quickurl = 'https://tools.wmflabs.org/quickstatements/api.php?'
            quickurl += 'action=import'
            quickurl += '&submit=1'
            quickurl += '&username=GETYOUROWNUSERNAME'
            quickurl += '&token=GETYOUROWNTOKEN'
            quickurl += '&format=v1'
            quickurl += '&batchname=tb-start-' + str(int((count_props / 140)))
            quickurl += '&data=' + urllib.parse.quote(item_properties, safe='')
            quickurl += '&compress=0'
            quickurl += '&site=wikidata'
            quickurl += ''

            split_url = parse.urlsplit(quickurl)

            r = requests.post(split_url.scheme + "://" + split_url.netloc + split_url.path, data=dict(parse.parse_qsl(parse.urlsplit(quickurl).query)))

            parsed_text = r.text
            if not isinstance(r.text, dict):
                json_acceptable_string = r.text.replace("'", "\"")
                parsed_text = json.loads(json_acceptable_string)

            if parsed_text['status'] and parsed_text['status'] == 'OK':
                print('###OK### Creation initiated automatically: See https://tools.wmflabs.org/quickstatements/#/batch/' + str(parsed_text['batch_id']) + ' for status.')
                item_properties = ''
            else:
                print('>> Error on batch submission: Try Url:')
                print('>> ' + quickurl)
                exit()

                fq = open(path4qs, "a")
                fq.write(item_properties)
                fq.close()
                item_properties = ''

print('Done!' + "\n")
