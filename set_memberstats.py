#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import re
import locale

import sys
import getopt

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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
repo = wikidata_site.data_repository()

diocese = False
dioid = False
position = False


def create_claim_pit(year):
    cal_model = None
    if year < 1584:
        cal_model = 'http://www.wikidata.org/entity/Q1985786'

    my_wbtime = pywikibot.WbTime(year=year,
                                 month=1, day=1,
                                 precision=9, before=0, after=0,
                                 timezone=0, calendarmodel=cal_model)

    claim = pywikibot.Claim(repo, 'P585')
    claim.setTarget(my_wbtime)
    return claim


def main(argv):
    opts, args = getopt.getopt(argv, "hd:i:", ["diocese=", 'id='])
    ret = {}
    for opt, arg in opts:
        if opt == '-h':
            print('check_bishopstart_on_chorg.py -d <diocese> -i <id>')
            sys.exit()
        elif opt in ("-d", "--diocese"):
            diocese = arg
            if diocese.isnumeric():
                diocese = 'Q' + diocese
            ret['diocese'] = diocese
        elif opt in ("-i", "--id"):
            dioid = arg
            ret['dioid'] = dioid
    return ret


if __name__ == "__main__":
    mainret = main(sys.argv[1:])
    if 'diocese' in mainret:
        diocese = mainret['diocese']
    if 'dioid' in mainret:
        dioid = mainret['dioid']


if diocese == False and dioid == False:
    print('!! NO DIOCESE GIVEN. I quit.')

itemdetails = False
target_page = False

if diocese:
    target_page = pywikibot.ItemPage(repo, diocese)
    itemdetails = target_page.get(get_redirect=True)
    list_currentdioids = itemdetails['claims']['P1866']
    if len(list_currentdioids) == 1:
        diocese = target_page.id
        print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
        dioid = list_currentdioids[0].getTarget()
    else:
        print('! Length of P1866 (Claim for Catholic Hierarchy diocese ID) !=1')
        exit()
elif not diocese and dioid:
    SPARQL = "SELECT ?item WHERE { ?item wdt:P1866 \"" + dioid + "\". }"
    my_generator = pg.WikidataSPARQLPageGenerator(SPARQL, site=wikidata_site)
    my_generator = list(my_generator)
    if len(my_generator) != 1:
        print('!!!- Found {} Results for DioId="' + dioid + '" that works only with an exact match.'.format(len(my_generator)))
        exit()
    else:
        target_page = my_generator[0]
        itemdetails = target_page.get(get_redirect=True)
        list_currentdioids = itemdetails['claims']['P1866']
        if len(list_currentdioids) == 1:
            diocese = target_page.id
            print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
        else:
            print('! Length of P1866 (Claim for Catholic Hierarchy diocese ID) !=1')
            exit()

chorgurl = 'http://www.catholic-hierarchy.org/diocese/d' + dioid + '.html'


try:
    r = requests_retry_session().get(chorgurl)
except:
    print('!!! Could not request url:' + chorgurl)
    exit()

if r.status_code != 200:
    print('### ERROR ON http-call for : ' + chorgurl)
if r.status_code == 200:
    print('>> Catholic-Hierarchy-DioId: ' + dioid)
    print('-- URL: ' + chorgurl)


bytes_regex = str.encode('<h2 align=center><a name="stats">Statistics<\/a><\/h2><p>\n(<table[\s\S]*<\/table>)')
stat_table = re.findall(bytes_regex, r.content)

if stat_table:
    print('--- Stat-Table found.')
else:
    print('!!- Stat-Table not found.')
    exit()

if not itemdetails:
    print('!!- Could not load WD-Item')
    exit()

bytes_regex = str.encode('<tr>(<th>.*<\/th>)<\/tr>')
stat_html_headlines = re.findall(bytes_regex, stat_table[0])

if not stat_html_headlines:
    print('!!- No Headlines found')
    exit()


bytes_regex = str.encode('<th>([\w ]+)<\/th>')
list_headlines = re.findall(bytes_regex, stat_html_headlines[0])

if not list_headlines:
    print('!!- No Plaintext Headlines found')
    exit()

# print(list_headlines)

yearpos = False
memberpos = False


try:
    yearpos = list_headlines.index(str.encode('Year'))
except:
    print('!-- Year-Column not found')
    exit()

try:
    memberpos = list_headlines.index(str.encode('Catholics'))
except:
    print('!-- Catholics-Column not found')
    exit()

bytes_regex = str.encode('<tr[^>]*>(.*)<\/tr>')
stat_html_rows = re.findall(bytes_regex, stat_table[0])

a_yearstat_ch = {}

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
for html_row in stat_html_rows:
    bytes_regex = str.encode('<th>.*<\/th>')
    stat_th_in = re.findall(bytes_regex, html_row)
    if stat_th_in:
        continue

    bytes_regex = str.encode('>([^<]+)<')
    td_in = re.findall(bytes_regex, html_row)
    if not len(td_in) == len(list_headlines):
        continue

    my_year = int(td_in[yearpos])
    my_members = int(locale.atoi(td_in[memberpos].decode('utf-8')))
    a_yearstat_ch[str(my_year)] = my_members


try:
    known_stats = itemdetails['claims']['P2124']
except KeyError:
    known_stats = []


a_yearstat_wd = {}
for known_stat in known_stats:
    trgt_number = known_stat.getTarget()
    print(trgt_number)
    a_qualis = known_stat.qualifiers
    if 'P585' not in a_qualis:
        print('-- Point in time unknown. I skip that one')
        continue

    my_year = a_qualis['P585'][0].getTarget().year
    my_members = trgt_number.amount
    a_yearstat_wd[str(my_year)] = int(my_members)

a_todo_stat = {}

for key in a_yearstat_ch.keys():
    if key not in a_yearstat_wd:
        a_todo_stat[key] = a_yearstat_ch[key]


for key in a_todo_stat:
    claim_membernumber = pywikibot.Claim(repo, 'P2124')
    amount_membernumber = pywikibot.WbQuantity(a_todo_stat[key], site=wikidata_site)
    claim_membernumber.setTarget(amount_membernumber)
    quali_pit = create_claim_pit(int(key))
    claim_membernumber.addQualifier(quali_pit)

    source_claim = pywikibot.Claim(repo, 'P1866')
    source_claim.setTarget(dioid)
    claim_membernumber.addSources([source_claim])
    target_page.addClaim(claim_membernumber, summary='added member amount')

print('Done!')
