#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import random
import re
import sys
import configparser
import urllib.parse
from datetime import datetime
from urllib import parse

import lxml.html
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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


def lreplace(pattern, sub, string):
    return re.sub('^%s' % pattern, sub, string)


MY_CH_ID = sys.argv[1]
if sys.argv:
    try:
        MYLOGFILE = sys.argv[2]
    except:
        MYLOGFILE = ''

MYCREATECODE = ''
ITEM_LABEL = ''
ITEM_PROPERTIES = ''
CONFIG = configparser.ConfigParser()
CONFIG.read('data/.credentials.ini')

CH_URL = 'http://www.catholic-hierarchy.org/bishop/b' + MY_CH_ID + '.html'

REQUEST_RESULT = requests_retry_session().get(CH_URL)
if REQUEST_RESULT.status_code != 200:
    print('### ERROR ON cath-id: ' + MY_CH_ID)
    quit()
if REQUEST_RESULT.status_code == 200:
    WD_QUERY = 'SELECT ?item WHERE {?item wdt:P1047 "' + MY_CH_ID + '"}'
    WIKIDATA_SITE = pywikibot.Site('wikidata', 'wikidata')
    GENERATOR = pg.WikidataSPARQLPageGenerator(WD_QUERY, site=WIKIDATA_SITE)
    WD_MATCHES = 0
    for item in GENERATOR:
        WD_MATCHES += 1
        item_id = item.id
    if WD_MATCHES > 0:
        print('### item "' + MY_CH_ID + '" already exists: https://www.wikidata.org/wiki/' + item_id)
        quit()

    PARSED_SOURCE = lxml.html.parse(CH_URL)
    MYTITLE = PARSED_SOURCE.find(".//title").text
    MYTITLE = MYTITLE.replace(' [Catholic-Hierarchy]', '')
    print('>> Found:' + MYTITLE + ' [id: ' + MY_CH_ID + ']')
    DEFLINE = 'CREATE'
    ITEM_PROPERTIES += "\nLAST\tP31\tQ5\t"
    ITEM_PROPERTIES += "\nLAST\tP21\tQ6581097\t"
    ITEM_PROPERTIES += "\nLAST\tP140\tQ9592\tS1047\t\"" + MY_CH_ID + "\""
    ITEM_PROPERTIES += "\nLAST\tP1047\t\"" + MY_CH_ID + "\"\t"

    CH_SOURCE = REQUEST_RESULT.content
    # print CH_SOURCE

    # CHECK SOURCE FOR DATES
    PRIEST_TR = re.findall(b"<tr>.*<td>Ordained Priest</td>.*</tr>", CH_SOURCE)
    if PRIEST_TR:
        ITEM_PROPERTIES += "\nLAST\tP106\tQ250867\tS1047\t\"" + MY_CH_ID + "\"\t"

    # BIRTHDATE
    BIRTH_DATETIME = None

    BIRTH_TR = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*<td>Born</td></tr>", CH_SOURCE)

    if BIRTH_TR:
        BIRTH_TR = re.findall(b"<tr><td[^>]+>(.*)</td><td>Born</td>.*</tr>", CH_SOURCE)

    if BIRTH_TR:
        print('-- Birth-Info: ' + BIRTH_TR[0].decode('utf-8'))
        BIRTH_TR = re.sub(r'\<[^\<]+\>', '', BIRTH_TR[0].decode('utf-8'))
        BIRTH_TR_CIRCA = re.findall(r"(.*)&sup[0-9];", BIRTH_TR.strip())

        if not BIRTH_TR_CIRCA:
            try:
                BIRTH_DATETIME = datetime.strptime(BIRTH_TR, '%d %b %Y')
                ITEM_PROPERTIES += "\nLAST\tP569\t+" + BIRTH_DATETIME.isoformat() + 'Z/11'
            except:
                print('- No valid birthdate (exact day) found: "' + BIRTH_TR + '"')
        elif len(BIRTH_TR_CIRCA[0]) == 4:
            try:
                BIRTH_DATETIME = datetime.strptime(BIRTH_TR_CIRCA[0], '%Y')
                ITEM_PROPERTIES += "\nLAST\tP569\t+" + BIRTH_DATETIME.isoformat() + 'Z/9' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ year) found: "' + BIRTH_TR + '"')
        elif len(BIRTH_TR_CIRCA[0]) == 8:
            try:
                BIRTH_DATETIME = datetime.strptime(BIRTH_TR_CIRCA[0], '%b %Y')
                ITEM_PROPERTIES += "\nLAST\tP569\t+" + BIRTH_DATETIME.isoformat() + 'Z/10' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ month) found: "' + BIRTH_TR + '"')
        else:
            try:
                BIRTH_DATETIME = datetime.strptime(BIRTH_TR_CIRCA[0], '%d %b %Y')
                ITEM_PROPERTIES += "\nLAST\tP569\t+" + BIRTH_DATETIME.isoformat() + 'Z/11' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ day) found: "' + BIRTH_TR_CIRCA[0] + '"')

    if BIRTH_DATETIME is None:

        BIRTH_PROP = re.findall(b'.*<time itemprop="birthDate" datetime="([0-9-]+)">.*</time>.*', CH_SOURCE)

        if BIRTH_PROP:
            print('-- Birth-Prop: ' + BIRTH_PROP[0].decode('utf-8'))
            try:
                BIRTH_DATETIME = datetime.strptime(BIRTH_PROP[0].decode('utf-8'), '%Y-%m-%d')
                ITEM_PROPERTIES += "\nLAST\tP569\t+" + BIRTH_DATETIME.isoformat() + 'Z/11'
                print('-- Birth-Prop: ' + BIRTH_PROP[0].decode('utf-8'))
            except:
                print('- No valid birthprop found: "' + BIRTH_PROP[0].decode('utf-8') + '"')

    # DEATHDATE
    DEATH_DATETIME = None

    DEATH_TR = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*<td>Died</td>.*</tr>", CH_SOURCE)
    if DEATH_TR:
        DEATH_TR = re.findall(b"<tr><td[^>]+>(.*)</td><td>Died</td>.*</tr>", CH_SOURCE)
    if DEATH_TR:
        DEATH_TR = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Died</td>.*</tr>", CH_SOURCE)

    if DEATH_TR:
        print('-- Death-Info: ' + DEATH_TR[0].decode('utf-8'))
        DEATH_TR = re.sub(r'\<[^\<]+>', '', DEATH_TR[0].decode('utf-8'))
        DEATH_TR_CIRCA = re.findall(r"(.*)&sup[0-9];", DEATH_TR.strip())

        if not DEATH_TR_CIRCA:
            try:
                DEATH_DATETIME = datetime.strptime(DEATH_TR, '%d %b %Y')
                ITEM_PROPERTIES += "\nLAST\tP570\t+" + DEATH_DATETIME.isoformat() + 'Z/11'
            except:
                print('- No valid deathdate found: "' + DEATH_TR + '"')
        elif len(DEATH_TR_CIRCA[0]) == 4:
            try:
                DEATH_DATETIME = datetime.strptime(DEATH_TR_CIRCA[0], '%Y')
                ITEM_PROPERTIES += "\nLAST\tP570\t+" + DEATH_DATETIME.isoformat() + 'Z/9' + "\tP1480\tQ5727902"
            except:
                print('- No valid deathdate found: "' + DEATH_TR + '"')
        elif len(DEATH_TR_CIRCA[0]) == 8:
            try:
                DEATH_DATETIME = datetime.strptime(DEATH_TR_CIRCA[0], '%b %Y')
                ITEM_PROPERTIES += "\nLAST\tP570\t+" + DEATH_DATETIME.isoformat() + 'Z/10' + "\tP1480\tQ5727902"
            except:
                print('- No valid deathdate found: "' + DEATH_TR + '"')
        else:
            try:
                DEATH_DATETIME = datetime.strptime(DEATH_TR_CIRCA[0], '%d %b %Y')
                ITEM_PROPERTIES += "\nLAST\tP570\t+" + DEATH_DATETIME.isoformat() + 'Z/11' + "\tP1480\tQ5727902"

            except:
                print('- No valid deathdate found: "' + DEATH_TR_CIRCA[0] + '"')

    if DEATH_DATETIME is None:

        DEATH_PROP = re.findall(b'.*<time itemprop="deathDate" datetime="([0-9-]+)">.*</time>.*', CH_SOURCE)
        if DEATH_PROP:
            try:
                DEATH_DATETIME = datetime.strptime(DEATH_PROP[0].decode('utf-8'), '%Y-%m-%d')
                ITEM_PROPERTIES += "\nLAST\tP570\t+" + DEATH_DATETIME.isoformat() + 'Z/11'
                print('-- Death-Prop: ' + DEATH_PROP[0].decode('utf-8'))
            except:
                print('- No valid deathprop found: "' + DEATH_PROP[0].decode('utf-8') + '"')

    MYTITLE = re.sub(r'\([^)]*\)', '', MYTITLE)
    MYTITLE = re.sub(r"\s\s+", " ", MYTITLE)
    MYTITLE = MYTITLE.strip()

    if MYTITLE.startswith('Bishop '):
        pos_de = random.choice(['Bischof der römisch-katholischen Kirche', 'römisch-katholischer Bischof', 'katholischer Bischof'])
        pos_en = random.choice(['bishop of the roman-catholic church', 'roman-catholic bishop', 'catholic bishop'])
        ITEM_PROPERTIES += "\nLAST\tP39\tQ611644\tS1047\t\"" + MY_CH_ID + "\"\t"
        DEFLINE += "\nLAST\tDde\t\"" + pos_de + "\""
        DEFLINE += "\nLAST\tDen\t\"" + pos_en + "\""
        DEFLINE += "\nLAST\tDit\t\"vescovo cattolico\""
        DEFLINE += "\nLAST\tDfr\t\"évêque catholique\""
        DEFLINE += "\nLAST\tDpl\t\"biskup katolicki\""
        DEFLINE += "\nLAST\tDla\t\"episcopus catholicus\""
        DEFLINE += "\nLAST\tDca\t\"bisbe catòlic\""
        DEFLINE += "\nLAST\tDes\t\"obispo católico\""
        DEFLINE += "\nLAST\tDnl\t\"katholiek bisschop\""
        ITEM_LABEL = lreplace('Bishop ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.startswith('Constitutional Bishop '):
        ITEM_PROPERTIES += "\nLAST\tP39\tQ1782975\t"
        DEFLINE += "\nLAST\tDde\t\"konstitutioneller Bischof\""
        DEFLINE += "\nLAST\tDen\t\"constitutional bishop\""
        DEFLINE += "\nLAST\tDit\t\"vescovo costituzionale\""
        DEFLINE += "\nLAST\tDfr\t\"évêque constitutionnel\""
        DEFLINE += "\nLAST\tDpl\t\"biskup konstytucyjny\""
        DEFLINE += "\nLAST\tDes\t\"obispo constitucional\""
        ITEM_LABEL = lreplace('Constitutional Bishop ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.startswith('Archbishop '):
        pos_de = random.choice(['Erzbischof der römisch-katholischen Kirche', 'römisch-katholischer Erzbischof', 'katholischer Erzischof', 'Erzbischof'])
        pos_en = random.choice(['archbishop of the roman-catholic church', 'roman-catholic archbishop', 'catholic archbishop'])
        ITEM_PROPERTIES += "\nLAST\tP39\tQ48629921\tS1047\t\"" + MY_CH_ID + "\"\t"
        DEFLINE += "\nLAST\tDde\t\"" + pos_de + "\""
        DEFLINE += "\nLAST\tDen\t\"" + pos_en + "\""
        DEFLINE += "\nLAST\tDit\t\"arcivescovo cattolico\""
        DEFLINE += "\nLAST\tDes\t\"arzobispo católico\""
        DEFLINE += "\nLAST\tDfr\t\"archevêque catholique\""
        DEFLINE += "\nLAST\tDla\t\"archiepiscopus catholicus\""
        ITEM_LABEL = lreplace('Archbishop ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.startswith('Patriarch '):
        ITEM_PROPERTIES += "\nLAST\tP39\tQ171692\t"
        DEFLINE += "\nLAST\tDde\t\"römisch-katholischer Patriarch\""
        DEFLINE += "\nLAST\tDen\t\"roman-catholic patriarch\""
        ITEM_LABEL = lreplace('Patriarch ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.startswith('Father '):
        DEFLINE += "\nLAST\tDde\t\"römisch-katholischer Geistlicher\""
        DEFLINE += "\nLAST\tDen\t\"roman-catholic clergyman \""
        ITEM_LABEL = lreplace('Father ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.startswith('Abbot '):
        ITEM_PROPERTIES += "\nLAST\tP39\tQ103163\tS1047\t\"" + MY_CH_ID + "\"\t"
        DEFLINE += "\nLAST\tDde\t\"römisch-katholischer Abt\""
        DEFLINE += "\nLAST\tDen\t\"roman-catholic abbot\""
        DEFLINE += "\nLAST\tDit\t\"abad cattolico\""
        DEFLINE += "\nLAST\tDes\t\"arzobispo católico\""
        DEFLINE += "\nLAST\tDfr\t\"abbé catholique\""
        DEFLINE += "\nLAST\tDla\t\"abbas catholicus\""
        ITEM_LABEL = lreplace('Abbot ', '', MYTITLE)
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.find('Cardinal ') != -1:
        ITEM_PROPERTIES += "\nLAST\tP39\tQ45722\tS1047\t\"" + MY_CH_ID + "\"\t"
        DEFLINE += "\nLAST\tDde\t\"Kardinal der römisch-katholischen Kirche\""
        DEFLINE += "\nLAST\tDen\t\"cardinal of the roman-catholic church\""
        DEFLINE += "\nLAST\tDit\t\"cardinale cattolico\""
        DEFLINE += "\nLAST\tDes\t\"cardenal católico\""
        DEFLINE += "\nLAST\tDfr\t\"cardinal catholique\""
        DEFLINE += "\nLAST\tDla\t\"cardinalis catholicus\""
        ITEM_LABEL = MYTITLE.replace('Cardinal ', '')
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    elif MYTITLE.find('Patriotic Bishop ') != -1:
        ITEM_PROPERTIES += "\nLAST\tP39\tQ611644\tS1047\t\"" + MY_CH_ID + "\"\t"
        DEFLINE += "\nLAST\tDde\t\"Patriotischer Bischof\""
        DEFLINE += "\nLAST\tDen\t\"patriotic bishop\""
        ITEM_LABEL = MYTITLE.replace('Patriotic Bishop ', '')
        DEFLINE += "\nLAST\tLde\t\"" + ITEM_LABEL + "\""
        DEFLINE += "\nLAST\tLen\t\"" + ITEM_LABEL + "\""

    else:
        quit('--- unknown job on "' + MYTITLE + '" ---')

    DEFLINE += "\t" + ITEM_PROPERTIES

    QUICKURL = 'https://tools.wmflabs.org/quickstatements/api.php?'
    QUICKURL += 'action=import'
    QUICKURL += '&submit=1'
    QUICKURL += '&username=' + CONFIG['tools.wmflabs.org']['username']
    QUICKURL += '&token=' + CONFIG['tools.wmflabs.org']['token']
    QUICKURL += '&format=v1'
    QUICKURL += '&batchname=create-' + MY_CH_ID
    QUICKURL += '&data=' + urllib.parse.quote(DEFLINE, safe='')
    QUICKURL += '&compress=0'
    QUICKURL += '&site=wikidata'
    QUICKURL += ''

    SPLIT_URL = parse.urlsplit(QUICKURL)

    if MYLOGFILE:
        FILE_LOG = open(MYLOGFILE, "a")
        FILE_LOG.write("\n\n" + DEFLINE)
        FILE_LOG.close()

    print("\n\n" + DEFLINE + "\n\n")

print('  Done!')
