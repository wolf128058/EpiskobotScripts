#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import re
from random import shuffle
import datetime

import progressbar

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import pywikibot
from pywikibot import pagegenerators as pg

L_LEGALPOS = ['Q45722', 'Q75178', 'Q157037', 'Q611644', 'Q948657', 'Q1144278', 'Q1993358', 'Q15253909', 'Q48629921', 'Q50362553', 'Q103163', 'Q19546', 'Q171692']

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
    QUERY4DIOID = 'SELECT ?item WHERE { ?item wdt:P1866 "' + dioid + '". }'
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    try:
        generator = pg.WikidataSPARQLPageGenerator(QUERY4DIOID, site=wikidata_site)
        generator = list(generator)

        if len(generator) > 1:
            print('-- DioId ' + dioid + ' is ambiguous.')
            return False
        for item in generator:
            item.get(get_redirect=True)
            print('--- WD-Item-4-Diocese found: ' + item.id)
            return item.id

    except:
        print('!!! query for diocese failed. (dioid: ' + dioid + ')')
        return False


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
QUERY_WITHOUT_START = '''
SELECT ?item WHERE {
  ?item wdt:P1047 ?cathi;
    wdt:P39 ?position
# FILTER( ?position NOT IN (wd:Q48629921, wd:Q50362553) )
 FILTER( ?position NOT IN (wd:Q65924966) )
}
'''

path4qs = 'data/log_quick_hiddenbishopships.txt'
generator = pg.WikidataSPARQLPageGenerator(QUERY_WITHOUT_START, site=wikidata_site)
generator = list(generator)
shuffle(generator)
repo = wikidata_site.data_repository()
item_properties = ''
count_props = 0

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    bar.update(0)
    for index, item in enumerate(generator):

        now = datetime.datetime.utcnow()
        my_date4wd = pywikibot.WbTime(
            year=now.year,
            month=now.month,
            day=now.day,
            precision=11,
            calendarmodel='http://www.wikidata.org/entity/Q1985727')

        mywd = item.get(get_redirect=True)
        mywd_id = item.id
        print("\n" + '>> Checking WD-ID: ' + mywd_id)
        print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

        claim_list_pos = {}
        my_cathbishop_claim = {}
        count_bishoppos = 0

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
            diocesan_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Bishop of (.*)</td>.*</tr>", r.content)
            titular_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Titular Bishop of (.*)</td>.*</tr>", r.content)

            l_dbishop = []
            l_tbishop = []

            l_known_dbishopships = []
            l_known_tbishopships = []

            try:
                claim_list_currentpositions = mywd['claims']['P39']
            except:
                print('### Job-Claim-Check failed!')
                continue

            illegal_pos = False
            for single_pos in claim_list_currentpositions:
                trgt_pos = single_pos.getTarget()
                if trgt_pos.id not in L_LEGALPOS:
                    print('This person has a illegal position. (https://www.wikidata.org/wiki/' + trgt_pos.id + ' ) I skip.')
                    illegal_pos = True

            if illegal_pos:
                continue

            for single_pos in claim_list_currentpositions:
                trgt_pos = single_pos.getTarget()
                if trgt_pos.id == 'Q1144278':
                    l_known_dbishopships.append(single_pos)
                elif trgt_pos.id == 'Q948657':
                    l_known_tbishopships.append(single_pos)

                if len(l_known_dbishopships) > 0:
                    print('-- Found {} Job-Claims for diocesan bishopships'.format(len(l_known_dbishopships)))

                if len(l_known_tbishopships) > 0:
                    print('-- Found {} Job-Claims for titular bishopships'.format(len(l_known_dbishopships)))

            if len(diocesan_bishopship_tr) > 0:
                for x in range(0, len(diocesan_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', diocesan_bishopship_tr[x])
                    if len(dioceseid) > 0:
                        l_dbishop.append(dioceseid[0].decode('utf-8'))
                l_dbishop = list(set(l_dbishop))
                print('-- Diocesan-Bishopship-Info: ' + ', '.join(l_dbishop))

                for dbishop in l_dbishop:
                    mydiowd = dioid2wd(dbishop)
                    known_a2d = False

                    for known_dbishopship in l_known_dbishopships:
                        a_qualis = known_dbishopship.qualifiers
                        if not 'P708' in a_qualis:
                            continue
                        if len(a_qualis['P708']) > 1:
                            print('-- !!! Take care there are more than 1 Dio-Claims!')
                            continue
                        diozese_claim = a_qualis['P708'][0]
                        trgt_d = diozese_claim.getTarget()
                        if trgt_d.id == mydiowd:
                            print('-- Found diocesan bishopship with already known and matching Diozese-Claim.')
                            known_a2d = True
                            continue

                    if known_a2d:
                        continue

                    if not mydiowd and mydiowd is not None:
                        if len(l_dbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ1144278\tP708\t" + mydiowd
                            item_properties += "\tS1047\t\"" + mycathid + "\"\t"
                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_db = pywikibot.ItemPage(repo, 'Q1144278')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_db)
                            new_claim.addQualifier(target_dioclaim)

                            source_claim_statedin = pywikibot.Claim(repo, 'P248')
                            source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                            source_claim_catid = pywikibot.Claim(repo, 'P1047')
                            source_claim_catid.setTarget(mycathid)
                            source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                            source_claim_retrieved.setTarget(my_date4wd)
                            new_claim.addSources([source_claim_statedin, source_claim_catid, source_claim_retrieved])

                            item.addClaim(new_claim, summary='added bishop-claim')

            if len(titular_bishopship_tr) > 0:
                for y in range(0, len(titular_bishopship_tr)):
                    dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', titular_bishopship_tr[y])
                    if len(dioceseid) > 0:
                        l_tbishop.append(dioceseid[0].decode('utf-8'))

                l_tbishop = list(set(l_tbishop))
                print('-- Titular-Arch-Bishopship-Info: ' + ', '.join(l_tbishop))
                for tbishop in l_tbishop:
                    mydiowd = dioid2wd(tbishop)

                    known_t2d = False

                    for known_tbishopship in l_known_tbishopships:
                        a_qualis = known_tbishopship.qualifiers
                        if not 'P708' in a_qualis:
                            continue
                        if len(a_qualis['P708']) > 1:
                            print('-- !!! Take care there are more than 1 Dio-Claims!')
                            continue
                        diozese_claim = a_qualis['P708'][0]
                        trgt_d = diozese_claim.getTarget()
                        if trgt_d.id == mydiowd:
                            print('-- Found titular-bishopship with already known and matching Diozese-Claim.')
                            known_t2d = True
                            continue

                    if known_t2d:
                        continue

                    if not mydiowd and mydiowd is not None:
                        if len(l_tbishop) == 1:
                            item_properties += "\n" + mywd_id + "\tP39\tQ948657\tP708\t" + mydiowd
                            item_properties += "\tS1047\t\"" + mycathid + "\"\t"

                        else:
                            new_claim = pywikibot.Claim(repo, 'P39')
                            target_tb = pywikibot.ItemPage(repo, 'Q948657')
                            target_dioclaim = pywikibot.Claim(repo, 'P708')
                            target_dio = pywikibot.ItemPage(repo, mydiowd)
                            target_dioclaim.setTarget(target_dio)
                            new_claim.setTarget(target_tb)
                            new_claim.addQualifier(target_dioclaim)

                            source_claim_statedin = pywikibot.Claim(repo, 'P248')
                            source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                            source_claim_catid = pywikibot.Claim(repo, 'P1047')
                            source_claim_catid.setTarget(mycathid)
                            source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                            source_claim_retrieved.setTarget(my_date4wd)
                            new_claim.addSources([source_claim_statedin, source_claim_catid, source_claim_retrieved])

                            item.addClaim(new_claim, summary='added titular-bishopship-claim')

            bar.update(index)
            item_properties = ''

print('Done!' + "\n")
