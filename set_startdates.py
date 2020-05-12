#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import re
from random import shuffle

import datetime
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


def dioid2wd(dioid):
    QUERY4DIOID = 'SELECT ?item ?itemLabel WHERE { ?item wdt:P1866 "' + dioid + '". }'
    try:
        for my_item in pg.WikidataSPARQLPageGenerator(QUERY4DIOID, site=pywikibot.Site('wikidata', 'wikidata')):
            my_item.get(get_redirect=True)
            print('--- WD-Item-4-Diocese found: ' + my_item.id)
            return my_item.id

    except:
        print('!!! query for diocese failed.')
        return False


QUERY = """
SELECT ?item ?birthLabel WHERE {
  ?item wdt:P1047 ?cathi;
    wdt:P39 wd:Q1144278.
}
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()
claim_startdate = pywikibot.Claim(repo, 'P580')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')
shuffle(generator)


with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        print('')
        bar.update(index)
        itemdetails = item.get(get_redirect=True)
        itemdetails_id = item.id
        mycathid = ''
        changed = False

        print('>> CHECKING: Wikidata-Item: https://www.wikidata.org/wiki/' + itemdetails_id)
        claim_list_cathid = itemdetails['claims']['P1047']
        mycathid = claim_list_cathid[0].getTarget()
        if not mycathid:
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
            if trgt_pos.id == 'Q1144278':
                a_qualis = single_pos.qualifiers
                if 'P580' in a_qualis:
                    str_dio = ''
                    if 'P708' in a_qualis:
                        str_dio = 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id'])
                        print('-- Yet known startdate in ' + str_dio + '.')
                        continue
                else:
                    l_dbishopships_wostart.append(single_pos)
                    dates_missing += 1

        if dates_missing == 0:
            print('-- All Diocesan Bishop Positions have start-dates. I skip that one.')
            continue

        if l_dbishopships_wostart:
            print('-- Found {} Job-Claims for diocesan bishopships without start-date'.format(len(l_dbishopships_wostart)))
        else:
            print('### No Dio-Bishop w/o startdate!')
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
                print('### DioId-Claim-Check failed (not unique)!')
                continue

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

                bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>Appointed</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>Appointed</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>Selected</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>Selected</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>Succeeded</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>Succeeded</td><td>Bishop of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>Appointed</td><td>Archbishop \(Personal Title\) of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>Appointed</td><td>Archbishop \(Personal Title\) of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>.*</td><td>Succeeded</td><td>Archbishop \(Personal Title\) of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)
                if not bishop_tr or len(bishop_tr) != 1:
                    bytes_regex = str.encode('<tr><td[^>]+>(.*)</td><td>Succeeded</td><td>Archbishop \(Personal Title\) of <a href="/diocese/d' + my_chdid + '.html">.*</td>.*</tr>')
                    bishop_tr = re.findall(bytes_regex, r.content)

                if bishop_tr and len(bishop_tr) == 1:
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
                        bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%d %b %Y')
                        if bishopstart_datetime.year < 1584:
                            my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                        start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=bishopstart_datetime.month, day=bishopstart_datetime.day, precision=11, before=0, after=0,
                                                         timezone=0, calendarmodel=my_calendar_model)
                        date_found = True

                    except:
                        print('- No valid startdate (precision day) found: "' + bishop_tr_clean + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%b %Y')
                            if bishopstart_datetime.year < 1584:
                                my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                            start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=bishopstart_datetime.month, day=1, precision=10, before=0, after=0,
                                                             timezone=0, calendarmodel=my_calendar_model)
                            date_found = True

                        except:
                            print('- No valid startdate (precision month) found: "' + bishop_tr_clean + '"')
                            try:
                                bishopstart_datetime = datetime.strptime(bishop_tr_clean, '%Y')
                                if bishopstart_datetime.year < 1584:
                                    my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                                start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=1, day=1, precision=9, before=0, after=0,
                                                                 timezone=0, calendarmodel=my_calendar_model)
                                date_found = True

                            except:
                                print('- No valid startdate (precision year) found: "' + bishop_tr_clean + '"')

                else:
                    try:
                        bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%d %b %Y')
                        if bishopstart_datetime.year < 1584:
                            my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                        start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=bishopstart_datetime.month, day=bishopstart_datetime.day, precision=11, before=0, after=0,
                                                         timezone=0, calendarmodel=my_calendar_model)
                        date_found = True

                    except:
                        print('- No valid ~startdate (precision day) found: "' + bishop_tr_circa[0] + '"')
                        try:
                            bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%b %Y')
                            if bishopstart_datetime.year < 1584:
                                my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                            start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=bishopstart_datetime.month, day=1, precision=10, before=0, after=0,
                                                             timezone=0, calendarmodel=my_calendar_model)
                            date_found = True

                        except:
                            print('- No valid ~startdate (precision month) found: "' + bishop_tr_circa[0] + '"')
                            try:
                                bishopstart_datetime = datetime.strptime(bishop_tr_circa[0], '%Y')
                                if bishopstart_datetime.year < 1584:
                                    my_calendar_model = 'http://www.wikidata.org/entity/Q1985786'
                                start_date4wd = pywikibot.WbTime(year=bishopstart_datetime.year, month=1, day=1, precision=9, before=0, after=0, timezone=0, calendarmodel=my_calendar_model)
                                date_found = True

                            except:
                                print('- No valid ~startdate (precision year) found: "' + bishop_tr_circa[0] + '"')

            if date_found:
                print(start_date4wd)
                claim_startdate.setTarget(start_date4wd)
                attempts = 0

                while attempts < 3:
                    try:
                        single_pos.addQualifier(claim_startdate, summary=u'added startdate')
                        break
                    except e:
                        attempts += 1
                        print("Error {}".format(e))

print('Done!')
