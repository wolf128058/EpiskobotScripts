#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import re
from random import shuffle
import configparser

from datetime import datetime

from urllib import parse

import urllib.parse
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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


CONFIG = configparser.ConfigParser()
CONFIG.read('data/.credentials.ini')

WIKIDATA_SITE = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = """
SELECT ?item ?itemLabel ?cathid WHERE {
  ?item p:P39 ?position;
    wdt:P1047 ?cathid.
  ?position ps:P39 wd:Q611644.
  FILTER(NOT EXISTS { ?position pq:P580 ?start. })
}
"""
PATH_QSLOG = 'data/log_quick_bishopstarts.txt'
GENERATOR = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=WIKIDATA_SITE)
GENERATOR = list(GENERATOR)
shuffle(GENERATOR)
ITEM_PROPERTIES = ''
COUNT_PROPS = 0

with progressbar.ProgressBar(max_value=len(GENERATOR), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(GENERATOR):
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
                if my_pos_data.id == 'Q611644':
                    count_bishoppos += 1
                    my_cathbishop_claim = my_pos_data

            print('-- Found {} Position-Claims for Catholic Bishop'.format(count_bishoppos))
        except:
            print('-- No Position for Catholic-Bishop found.')

        if not count_bishoppos:
            print('-- {} Position-Claims for Catholic Bishop is to less. I skip.'.format(count_bishoppos))
            continue
        if count_bishoppos > 1:
            print('-- {} Position-Claims for Catholic Bishop is to much. I skip.'.format(count_bishoppos))
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

            REQUEST_RESULT = requests_retry_session().get(chorgurl)
            if REQUEST_RESULT.status_code != 200:
                print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                continue

            bishop_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>.*</td><td>Ordained Bishop</td>.*</tr>', REQUEST_RESULT.content)
            if not bishop_tr:
                bishop_tr = re.findall(b'<tr><td[^>]+>(.*)</td><td>Ordained Bishop</td>.*</tr>', REQUEST_RESULT.content)
            if bishop_tr:
                print('-- Bishop-Info: ' + bishop_tr[0].decode('utf-8'))

                bishop_tr_clean = ''
                if isinstance(bishop_tr[0].decode('utf-8'), str):
                    bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0].decode('utf-8'))
                if isinstance(bishop_tr[0], str):
                    bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0])

                print('-- Bishop-Info-Clean: ' + bishop_tr_clean)

                bishop_tr_circa = re.findall(r'(.*)&', bishop_tr_clean)
            else:
                print('-- No Bishop-Ordination Data in table found. I skip.')
                continue

            if not bishop_tr_circa:

                try:
                    bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%d %b %Y')
                    ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" \
                                       + bishopstart_datetime.isoformat() + 'Z/11' + "\tS1047\t\"" + mycathid + "\"\t"
                    COUNT_PROPS += 1
                except:
                    print('- No valid startdate (precision day) found: "' + bishop_tr_clean + '"')
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%b %Y')
                        ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" \
                                           + bishopstart_datetime.isoformat() + 'Z/10' + "\tS1047\t\"" + mycathid + "\"\t"
                        COUNT_PROPS += 1
                    except:
                        print('- No valid startdate (precision month) found: "' + bishop_tr_clean + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_clean.strip(), '%Y')
                            ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" \
                                               + bishopstart_datetime.isoformat() + 'Z/9' \
                                               + "\tS1047\t\"" + mycathid + "\"\t"
                            COUNT_PROPS += 1
                        except:
                            print('- No valid startdate (precision year) found: "' + bishop_tr_clean + '"')

            else:
                try:
                    bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%d %b %Y')
                    ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" + bishopstart_datetime.isoformat() \
                                       + 'Z/11' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                    COUNT_PROPS += 1
                except:
                    print('- No valid ~startdate (precision day) found: "' + bishop_tr_circa[0].strip() + '"')
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%b %Y')
                        ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" \
                                           + bishopstart_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902" + "\tS1047\t\"" + mycathid + "\"\t"
                        COUNT_PROPS += 1
                    except:
                        print('- No valid ~startdate (precision month) found: "' + bishop_tr_circa[0].strip() + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_circa[0].strip(), '%Y')
                            ITEM_PROPERTIES += "\n" + mywd_id + "\tP39\tQ611644\tP580\t+" \
                                               + bishopstart_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902" \
                                               + "\tS1047\t\"" + mycathid + "\"\t"
                            COUNT_PROPS += 1
                        except:
                            print('- No valid ~startdate (precision year) found: "' + bishop_tr_circa[0].strip() + '"')

    QUICKURL = 'https://tools.wmflabs.org/quickstatements/api.php?'
    QUICKURL += 'action=import'
    QUICKURL += '&submit=1'
    QUICKURL += '&username=' + CONFIG['tools.wmflabs.org']['username']
    QUICKURL += '&token=' + CONFIG['tools.wmflabs.org']['token']
    QUICKURL += '&format=v1'
    QUICKURL += '&batchname=bishopstart-' + mycathid
    QUICKURL += '&data=' + urllib.parse.quote(ITEM_PROPERTIES, safe='')
    QUICKURL += '&compress=0'
    QUICKURL += '&site=wikidata'
    QUICKURL += ''

    SPLIT_URL = parse.urlsplit(QUICKURL)

    REQUEST_RESULT = requests.post(SPLIT_URL.scheme + "://" + SPLIT_URL.netloc + SPLIT_URL.path, data=dict(parse.parse_qsl(parse.urlsplit(QUICKURL).query)))

    PARSED_TEXT = REQUEST_RESULT.text
    if not isinstance(REQUEST_RESULT.text, dict):
        JSON_ACCEPTABLE_STRING = REQUEST_RESULT.text.replace("'", "\"")
        PARSED_TEXT = json.loads(JSON_ACCEPTABLE_STRING)

    if PARSED_TEXT['status'] and PARSED_TEXT['status'] == 'OK':
        print('- Creation initiated automatically: See https://tools.wmflabs.org/quickstatements/#/batch/' + str(
            PARSED_TEXT['batch_id']) + ' for status.')
    else:
        print('>> Error on batch submission: Try Url:')
        print('>> ' + QUICKURL)
        LOG_FILE = open(PATH_QSLOG, "a")
        LOG_FILE.write(ITEM_PROPERTIES)
        LOG_FILE.close()
        ITEM_PROPERTIES = ''

print('Done!' + "\n")
