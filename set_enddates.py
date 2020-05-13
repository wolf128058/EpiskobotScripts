#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import re
import os
import random
from random import shuffle

import sys
import getopt

from datetime import datetime

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


diocese = False
position = False


def main(argv):
    opts, args = getopt.getopt(argv, "hd:p:", ["diocese=", "position="])
    print(args)
    ret = {}
    for opt, arg in opts:
        if opt == '-h':
            print('set_enddates.py -d <diocese> -p <position>')
            sys.exit()
        elif opt in ("-d", "--diocese"):
            diocese = arg
            if diocese.isnumeric():
                diocese = 'Q' + diocese
            ret['dio'] = diocese
        elif opt in ("-p", "--position"):
            position = arg
            if position.isnumeric():
                position = 'Q'.position
            ret['pos'] = position
    return ret


if __name__ == "__main__":
    mainret = main(sys.argv[1:])
    if 'dio' in mainret:
        diocese = mainret['dio']
    if 'pos' in mainret:
        position = mainret['pos']

list_events = ['Resigned', 'Ceased']
list_pos = {}
list_pos['Q1144278'] = ['Bishop', 'Archbishop \(Personal Title\)']
list_pos['Q948657'] = ['Titular Bishop']
list_pos['Q48629921'] = ['Archbishop']
list_pos['Q50362553'] = ['Titular Archbishop']
list_pos['Q75178'] = ['Auxiliary Bishop']
list_pos['Q15253909'] = ['Vicar Apostolic']
list_pos['Q1993358'] = ['Apostolic Administrator']
list_pos['Q65924966'] = ['Bishop', 'Archbishop', 'Archbishop \(Personal Title\)']

if position == False and diocese != False:
    for single_pos in list_pos.keys():
        os.system('python3 set_enddates.py -d ' + diocese + ' -p' + single_pos)

if not position in list_pos.keys():
    print('!!! - ' + str(position) + ' is not a position this script is designed for.')
    exit()


QUERY = """
SELECT ?item WHERE {
  ?item wdt:P1047 ?cathi;
    wdt:P39 wd:""" + position + """.
}
"""

if diocese:
    QUERY = """
    SELECT ?item WHERE {
    ?item wdt:P39 wd:""" + position + """;
        p:P39 ?DBship.
    ?DBship ps:P39 wd:""" + position + """;
        pq:P708 wd:""" + diocese + ".}"

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()
claim_enddate = pywikibot.Claim(repo, 'P582')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')
shuffle(generator)

my_succ_dio_id = False

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        print('')
        bar.update(index)
        itemdetails = item.get(get_redirect=True)
        itemdetails_id = item.id
        mycathid = ''
        changed = False

        print('>> CHECKING: Wikidata-Item: https://www.wikidata.org/wiki/' + itemdetails_id)
        try:
            claim_list_cathid = itemdetails['claims']['P1047']
        except:
            print('-- Not Catholic-Hierarchy-Id found. I skip that one')
            continue
        mycathid = claim_list_cathid[0].getTarget()
        if not mycathid:
            print('-- Not Catholic-Hierarchy-Id found. I skip that one')
            continue

        l_dbishop = []
        l_dbishopships_wostart = []
        l_associated_dioceseids = []

        try:
            claim_list_currentpositions = itemdetails['claims']['P39']
        except:
            print('### Job-Claim-Check failed!')
            continue

        dates_missing = 0
        for single_pos in claim_list_currentpositions:
            trgt_pos = single_pos.getTarget()
            to_json = single_pos.toJSON()
            if trgt_pos.id == position:
                a_qualis = single_pos.qualifiers
                if 'P580' not in a_qualis:
                    print('-- Startdate unknown. I skip that one')
                if 'P582' in a_qualis:
                    str_dio = ''
                    if 'P708' in a_qualis:
                        str_dio = 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id'])
                        print('-- Yet known enddate in ' + str_dio + '.')
                        continue
                else:
                    l_dbishopships_wostart.append(single_pos)
                    dates_missing += 1

        if dates_missing == 0:
            print('-- All selected Positions have start-dates. I skip that one.')
            continue

        if l_dbishopships_wostart:
            print('-- Found {} Job-Claims for selected jobs without start-date'.format(
                len(l_dbishopships_wostart)))
        else:
            print('### No selected position w/o enddate!')
            continue

        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

        try:
            r = requests_retry_session().get(chorgurl)
        except:
            continue

        if r.status_code != 200:
            print('### ERROR ON http-call forcath-id: ' + mycathid)
            continue

        if r.status_code == 200:
            print('>> Catholic-Hierarchy-Id: ' + mycathid)
            print('-- URL: ' + chorgurl)

        for single_pos in l_dbishopships_wostart:
            start_date4wd = None
            date_found = False
            my_calendar_model = None

            to_json = single_pos.toJSON()

            try:
                to_json['qualifiers']['P708']
            except KeyError:
                print("-- No diocese given!")
                continue

            my_dio = 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id'])
            my_wd_dio = pywikibot.ItemPage(repo, my_dio)
            diodetails = my_wd_dio.get(get_redirect=True)

            try:
                dio_claim_list_chd_id = diodetails['claims']['P1866']
            except KeyError:
                print('### DioId-Claim-Check failed!')
                continue

            if len(dio_claim_list_chd_id) != 1:
                if diocese != False and my_succ_dio_id:
                    dio_claim_list_chd_id = my_succ_dio_id

                dio_claim_list_chd_id = [random.choice(dio_claim_list_chd_id)]
                print('### DioId-Claim-Check failed (not unique)!')

            my_chdid = ''
            d_to_json = dio_claim_list_chd_id[0].toJSON()
            try:
                my_chdid = d_to_json['mainsnak']['datavalue']['value']
            except KeyError:
                print('!!! - Did not find Diocese-Id')
                continue

            if my_chdid:
                print('-- Pos for dio:' + my_chdid)
                # and now check for start in this dio

                bishop_tr = False
                for pos_name in list_pos[position]:
                    for event in list_events:
                        if not bishop_tr or len(bishop_tr) != 1:
                            bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>' + event + '</td><td>' + pos_name + ' of '
                                                     '<a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                            bishop_tr = re.findall(bytes_regex, r.content)
                        if not bishop_tr or len(bishop_tr) != 1:
                            bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>' + event + '</td><td>' + pos_name + ' of '
                                                     '<a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                            bishop_tr = re.findall(bytes_regex, r.content)

                if bishop_tr and len(bishop_tr) == 1:
                    print('-- Pos-Start-Info: ' + bishop_tr[0].decode('utf-8'))

                    bishop_tr_clean = ''
                    if isinstance(bishop_tr[0].decode('utf-8'), str):
                        bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0].decode('utf-8'))
                        bishop_tr_clean = bishop_tr_clean.strip()
                    if isinstance(bishop_tr[0], str):
                        bishop_tr_clean = re.sub(r'\<[^\<]+\>', '', bishop_tr[0])
                        bishop_tr_clean = bishop_tr_clean.strip()

                    print('-- Pos-Info-Clean: ' + bishop_tr_clean)

                    bishop_tr_circa = re.findall(r'(.*)&', bishop_tr_clean)
                else:
                    print('-- No Pos-End Data in table found. I skip.')
                    continue

                if not bishop_tr_circa:
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%d %b %Y')
                        if bishopstart_datetime.year < 1584:
                            my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                        start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year,
                                                         month=bishopstart_datetime.month, day=bishopstart_datetime.day,
                                                         precision=11, before=0, after=0,
                                                         timezone=0, calendarmodel=my_calendar_model)
                        date_found = True

                    except:
                        print('- No valid enddate (precision day) found: "' + bishop_tr_clean + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%b %Y')
                            if bishopstart_datetime.year < 1584:
                                my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                            start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year,
                                                             month=bishopstart_datetime.month, day=1, precision=10,
                                                             before=0, after=0,
                                                             timezone=0, calendarmodel=my_calendar_model)
                            date_found = True

                        except:
                            print('- No valid enddate (precision month) found: "' + bishop_tr_clean + '"')
                            try:
                                bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%Y')
                                if bishopstart_datetime.year < 1584:
                                    my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                                start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=1, day=1,
                                                                 precision=9, before=0, after=0,
                                                                 timezone=0, calendarmodel=my_calendar_model)
                                date_found = True

                            except:
                                print('- No valid enddate (precision year) found: "' + bishop_tr_clean + '"')

                else:
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%d %b %Y')
                        if bishopstart_datetime.year < 1584:
                            my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                        start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year,
                                                         month=bishopstart_datetime.month, day=bishopstart_datetime.day,
                                                         precision=11, before=0, after=0,
                                                         timezone=0, calendarmodel=my_calendar_model)
                        date_found = True

                    except:
                        print('- No valid ~enddate (precision day) found: "' + bishop_tr_circa[0] + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%b %Y')
                            if bishopstart_datetime.year < 1584:
                                my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                            start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year,
                                                             month=bishopstart_datetime.month, day=1, precision=10,
                                                             before=0, after=0,
                                                             timezone=0, calendarmodel=my_calendar_model)
                            date_found = True

                        except:
                            print('- No valid ~enddate (precision month) found: "' + bishop_tr_circa[0] + '"')
                            try:
                                bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%Y')
                                if bishopstart_datetime.year < 1584:
                                    my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                                start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=1, day=1,
                                                                 precision=9, before=0, after=0, timezone=0,
                                                                 calendarmodel=my_calendar_model)
                                date_found = True

                            except:
                                # print('- No valid ~enddate (precision year) found: "' + bishop_tr_circa[0] + '"')
                                try:
                                    if (bishop_tr_circa[0].strip().isnumeric()):
                                        tmpyear = int(bishop_tr_circa[0].strip())
                                        if tmpyear < 1584:
                                            my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                                        start_date4wd = pywikibot.WbTime(year=tmpyear, month=1, day=1,
                                                                         precision=9, before=0, after=0, timezone=0,
                                                                         calendarmodel=my_calendar_model)
                                        date_found = True
                                except:
                                    print('- No valid ~enddate (precision year) found: "' + bishop_tr_circa[0] + '"')

            if date_found:
                if diocese != False:
                    my_succ_dio_id = dio_claim_list_chd_id
                print(start_date4wd)
                claim_enddate.setTarget(start_date4wd)
                attempts = 0

                while attempts < 3:
                    try:
                        single_pos.addQualifier(claim_enddate, summary=u'added enddate')
                        break
                    except e:
                        attempts += 1
                        print("Error {}".format(e))

print('Done!')
