#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import os
from random import shuffle

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
    query4_dioid = 'SELECT ?item ?itemLabel WHERE { ?item wdt:P1866 "' + dioid + '". }'
    try:
        for my_item in pg.WikidataSPARQLPageGenerator(query4_dioid, site=pywikibot.Site('wikidata', 'wikidata')):
            my_item.get(get_redirect=True)
            print('--- WD-Item-4-Diocese found: ' + my_item.id)
            return my_item.id

    except:
        print('!!! query for diocese failed.')
        return False


QUERY = """
SELECT ?item WHERE {
  ?item wdt:P39 wd:Q48629921;
    wdt:P1047 ?cathi;
    p:P39 ?pos.
  FILTER(EXISTS { ?pos pq:P708 ?statement. })
  FILTER(EXISTS { ?pos pq:P1365 ?statement. })
  FILTER(EXISTS { ?pos pq:P1366 ?statement. })
}
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')
shuffle(generator)

repo = wikidata_site.data_repository()

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
        l_known_dbishopships = []
        l_associated_dioceseids = []

        try:
            claim_list_currentpositions = itemdetails['claims']['P39']
        except:
            print('### Job-Claim-Check failed!')
            continue

        sources_missing = 0
        for single_pos in claim_list_currentpositions:
            trgt_pos = single_pos.getTarget()
            if trgt_pos.id == 'Q48629921':
                chp_source = False
                chd_source = False
                set_chd_source = False
                pos_sources = single_pos.getSources()

                if pos_sources:
                    for pos_source in pos_sources:
                        try:
                            if pos_source['P1047']:
                                chp_source = True
                        except KeyError:
                            pass

                        try:
                            if pos_source['P1866']:
                                chd_source = True
                        except KeyError:
                            pass

                if chp_source and chd_source:
                    print('-- Both sources given. I skip that one.')
                    continue
                elif not chp_source:
                    print('-- No CH-Person-Source given. I skip that one.')
                    continue

                to_json = single_pos.toJSON()
                missing = 0

                try:
                    to_json['qualifiers']['P708']
                except KeyError:
                    print("-- No diocese given!")
                    continue

                try:
                    to_json['qualifiers']['P1365']
                except KeyError:
                    print("-- No predecessor given")
                    missing += 1
                    if trgt_pos.id in ['Q1144278']:
                        os.system('python3 set_predecessor.py -d ' + 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id']) + ' -o ' + itemdetails_id + ' -p ' + trgt_pos.id + ' -a 1')

                try:
                    to_json['qualifiers']['P1366']
                except KeyError:
                    print("-- No sucessor given")
                    missing += 2

                try:
                    to_json['qualifiers']['P1545']
                except KeyError:
                    print("-- No position given")
                    missing += 4

                # TODO: on missing = 2,6 check if alive
                if (missing == 1 and to_json['qualifiers']['P1545'] == '1') or missing in [0, 4]:
                    my_dio = 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id'])
                    site = pywikibot.Site('wikidata', 'wikidata')
                    repo = site.data_repository()
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

                    if len(my_chdid) > 0:
                        print('>>> Adding Source Claim')
                        source_claim = pywikibot.Claim(repo, 'P1866')
                        source_claim.setTarget(my_chdid)
                        single_pos.addSources([source_claim], summary='add catholic-hierarchy-diocese-id as source')
                        continue

print('Done!')
