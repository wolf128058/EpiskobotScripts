#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import string

import lxml.html
import requests
import re

import datetime
from datetime import datetime

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


mycathid = sys.argv[1]
if len(sys.argv) > 0:
    try:
        mylogfile = sys.argv[2]
    except:
        mylogfile = ''
mycreatecode = ''
item_label = ''
item_properties = ''

chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

r = requests_retry_session().get(chorgurl)
if r.status_code != 200:
    print('### ERROR ON cath-id: ' + mycathid)
    quit()
if r.status_code == 200:
    wd_query = 'SELECT ?item WHERE {?item wdt:P1047 "' + mycathid + '"}'
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    generator = pg.WikidataSPARQLPageGenerator(wd_query, site=wikidata_site)
    wd_matches = 0
    for item in generator:
        wd_matches += 1
        item_id = item.id
    if wd_matches > 0:
        print('### item already exists: https://www.wikidata.org/wiki/' + item_id)
        quit()

    t = lxml.html.parse(chorgurl)
    mytitle = t.find(".//title").text
    mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
    print('>> Found:' + mytitle + ' [id: ' + mycathid + ']')
    defline = 'CREATE'
    item_properties += "\nLAST\tP31\tQ5\t"
    item_properties += "\nLAST\tP21\tQ6581097\t"
    item_properties += "\nLAST\tP140\tQ9592\t"
    item_properties += "\nLAST\tP1047\t\"" + mycathid + "\"\t"

    source = r.content
    # print source

# CHECK SOURCE FOR DATES
    priest_tr = re.findall(b"<tr>.*<td>Ordained Priest</td>.*\</tr>", source)
    if len(priest_tr) > 0:
        item_properties += "\nLAST\tP106\tQ250867\tS1047\t\"" + mycathid + "\"\t"

# BIRTHDATE
    birth_datetime = None

    birth_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*<td>Born</td></tr>", source)

    if len(birth_tr) > 0:
        birth_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>Born</td>.*</tr>", source)

    if len(birth_tr) > 0:
        print('-- Birth-Info: ' + birth_tr[0].decode('utf-8'))
        birth_tr = re.sub(r'\<[^\<]+\>', '', birth_tr[0].decode('utf-8'))
        birth_tr_circa = re.findall(r"(.*)&sup[0-9];", birth_tr.strip())

        if len(birth_tr_circa) == 0:
            try:
                birth_datetime = datetime.strptime(birth_tr, '%d %b %Y')
                item_properties += "\nLAST\tP569\t+" + birth_datetime.isoformat() + 'Z/11'
            except:
                print('- No valid birthdate (exact day) found: "' + birth_tr + '"')
        elif len(birth_tr_circa[0]) == 4:
            try:
                birth_datetime = datetime.strptime(birth_tr_circa[0], '%Y')
                item_properties += "\nLAST\tP569\t+" + birth_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ year) found: "' + birth_tr + '"')
        elif len(birth_tr_circa[0]) == 8:
            try:
                birth_datetime = datetime.strptime(birth_tr_circa[0], '%b %Y')
                item_properties += "\nLAST\tP569\t+" + birth_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ month) found: "' + birth_tr + '"')
        else:
            try:
                birth_datetime = datetime.strptime(birth_tr_circa[0], '%d %b %Y')
                item_properties += "\nLAST\tP569\t+" + birth_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902"
            except:
                print('- No valid birthdate (~ day) found: "' + birth_tr_circa[0] + '"')

    if birth_datetime == None:

        birth_prop = re.findall(b'.*<time itemprop="birthDate" datetime="([0-9-]+)">.*</time>.*', source)
        if len(birth_prop) > 0:
            print('-- Birth-Prop: ' + birth_prop[0].decode('utf-8'))

        if len(birth_prop) > 0:
            try:
                birth_datetime = datetime.strptime(birth_prop[0].decode('utf-8'), '%Y-%m-%d')
                item_properties += "\nLAST\tP569\t+" + birth_datetime.isoformat() + 'Z/11'
                print('-- Birth-Prop: ' + birth_prop[0].decode('utf-8'))
            except:
                print('- No valid birthprop found: "' + birth_prop[0].decode('utf-8') + '"')


# DEATHDATE
    death_datetime = None

    death_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*<td>Died</td>.*</tr>", source)
    if len(death_tr) > 0:
        death_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>Died</td>.*</tr>", source)
    if len(death_tr) > 0:
        death_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Died</td>.*</tr>", source)

    if len(death_tr) > 0:
        print('-- Death-Info: ' + death_tr[0].decode('utf-8'))
        death_tr = re.sub(r'\<[^\<]+>', '', death_tr[0].decode('utf-8'))
        death_tr_circa = re.findall(r"(.*)&sup[0-9];", death_tr.strip())

        if len(death_tr_circa) == 0:
            try:
                death_datetime = datetime.strptime(death_tr, '%d %b %Y')
                item_properties += "\nLAST\tP570\t+" + death_datetime.isoformat() + 'Z/11'
            except:
                print('- No valid deathdate found: "' + death_tr + '"')
        elif len(death_tr_circa[0]) == 4:
            try:
                death_datetime = datetime.strptime(death_tr_circa[0], '%Y')
                item_properties += "\nLAST\tP570\t+" + death_datetime.isoformat() + 'Z/9' + "\tP1480\tQ5727902"
            except:
                print('- No valid deathdate found: "' + death_tr + '"')
        elif len(death_tr_circa[0]) == 8:
            try:
                death_datetime = datetime.strptime(death_tr_circa[0], '%b %Y')
                item_properties += "\nLAST\tP570\t+" + death_datetime.isoformat() + 'Z/10' + "\tP1480\tQ5727902"
            except:
                print('- No valid deathdate found: "' + death_tr + '"')
        else:
            try:
                death_datetime = datetime.strptime(death_tr_circa[0], '%d %b %Y')
                item_properties += "\nLAST\tP570\t+" + death_datetime.isoformat() + 'Z/11' + "\tP1480\tQ5727902"

            except:
                print('- No valid deathdate found: "' + death_tr_circa[0] + '"')

    if death_datetime == None:

        death_prop = re.findall(b'.*<time itemprop="deathDate" datetime="([0-9-]+)">.*</time>.*', source)
        if len(death_prop) > 0:
            try:
                death_datetime = datetime.strptime(death_prop[0].decode('utf-8'), '%Y-%m-%d')
                item_properties += "\nLAST\tP570\t+" + death_datetime.isoformat() + 'Z/11'
                print('-- Death-Prop: ' + death_prop[0].decode('utf-8'))
            except:
                print('- No valid deathprop found: "' + death_prop[0].decode('utf-8') + '"')

    mytitle = re.sub(r'\([^)]*\)', '', mytitle)
    mytitle = re.sub("\s\s+", " ", mytitle)
    mytitle = mytitle.strip()

    if mytitle.startswith('Bishop '):
        item_properties += "\nLAST\tP39\tQ611644\tS1047\t\"" + mycathid + "\"\t"
        defline += "\nLAST\tDde\t\"Bischof der römisch-katholischen Kirche\""
        defline += "\nLAST\tDen\t\"bishop of the roman-catholic church\""
        defline += "\nLAST\tDit\t\"vescovo cattolico\""
        defline += "\nLAST\tDfr\t\"évêque catholique\""
        defline += "\nLAST\tDpl\t\"biskup katolicki\""
        defline += "\nLAST\tDla\t\"episcopus catholicus\""
        defline += "\nLAST\tDca\t\"bisbe catòlic\""
        defline += "\nLAST\tDes\t\"obispo católico\""
        defline += "\nLAST\tDnl\t\"katholiek bisschop\""
        item_label = lreplace('Bishop ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.startswith('Constitutional Bishop '):
        item_properties += "\nLAST\tP39\tQ1782975\t"
        defline += "\nLAST\tDde\t\"konstitutioneller Bischof\""
        defline += "\nLAST\tDen\t\"constitutional bishop\""
        defline += "\nLAST\tDit\t\"vescovo costituzionale\""
        defline += "\nLAST\tDfr\t\"évêque constitutionnel\""
        defline += "\nLAST\tDpl\t\"biskup konstytucyjny\""
        defline += "\nLAST\tDes\t\"obispo constitucional\""
        item_label = lreplace('Constitutional Bishop ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.startswith('Archbishop '):
        item_properties += "\nLAST\tP39\tQ48629921\tS1047\t\"" + mycathid + "\"\t"
        defline += "\nLAST\tDde\t\"Erzbischof der römisch-katholischen Kirche\""
        defline += "\nLAST\tDen\t\"archbishop of the roman-catholic church\""
        defline += "\nLAST\tDit\t\"arcivescovo cattolico\""
        defline += "\nLAST\tDes\t\"arzobispo católico\""
        defline += "\nLAST\tDfr\t\"archevêque catholique\""
        defline += "\nLAST\tDla\t\"archiepiscopus catholicus\""
        item_label = lreplace('Archbishop ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.startswith('Patriarch '):
        item_properties += "\nLAST\tP39\tQ171692\t"
        defline += "\nLAST\tDde\t\"römisch-katholischer Patriarch\""
        defline += "\nLAST\tDen\t\"roman-catholic patriarch\""
        item_label = lreplace('Patriarch ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.startswith('Father '):
        defline += "\nLAST\tDde\t\"römisch-katholischer Geistlicher\""
        defline += "\nLAST\tDen\t\"roman-catholic clergyman \""
        item_label = lreplace('Father ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.startswith('Abbot '):
        item_properties += "\nLAST\tP39\tQ103163\tS1047\t\"" + mycathid + "\"\t"
        defline += "\nLAST\tDde\t\"römisch-katholischer Abt\""
        defline += "\nLAST\tDen\t\"roman-catholic abbot\""
        defline += "\nLAST\tDit\t\"abad cattolico\""
        defline += "\nLAST\tDes\t\"arzobispo católico\""
        defline += "\nLAST\tDfr\t\"abbé catholique\""
        defline += "\nLAST\tDla\t\"abbas catholicus\""
        item_label = lreplace('Abbot ', '', mytitle)
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    elif mytitle.find('Cardinal '):
        item_properties += "\nLAST\tP39\tQ45722\tS1047\t\"" + mycathid + "\"\t"
        defline += "\nLAST\tDde\t\"Kardinal der römisch-katholischen Kirche\""
        defline += "\nLAST\tDen\t\"cardinal of the roman-catholic church\""
        defline += "\nLAST\tDit\t\"cardinale cattolico\""
        defline += "\nLAST\tDes\t\"cardenal católico\""
        defline += "\nLAST\tDfr\t\"cardinal catholique\""
        defline += "\nLAST\tDla\t\"cardinalis catholicus\""
        item_label = mytitle.replace('Cardinal ', '')
        defline += "\nLAST\tLde\t\"" + item_label + "\""
        defline += "\nLAST\tLen\t\"" + item_label + "\""

    else:
        quit('--- unknown job on "' + mytitle + '" ---')

    defline += "\t" + item_properties

    if len(mylogfile) > 0:
        fq = open(mylogfile, "a")
        fq.write("\n\n" + defline)
        fq.close()

    print("\n\n" + defline + "\n\n")


print('  Done!')
