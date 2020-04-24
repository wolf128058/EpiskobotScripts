#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import re
from random import shuffle

from urllib import parse

import urllib.parse
import json

import lxml.html
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
            if trgt_pos.id == 'Q1144278':
                l_known_dbishopships.append(single_pos)
                pos_sources = single_pos.getSources()
                if not pos_sources:
                    sources_missing += 1

        if sources_missing == 0:
            print('-- All Diocesan Bishop Positions have sources. I skip that one.')
            continue

        if l_known_dbishopships:
            print('-- Found {} Job-Claims for diocesan bishopships'.format(len(l_known_dbishopships)))
        else:
            print('### No Dio-Bishop!')
            continue

        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
        r = requests_retry_session().get(chorgurl)

        try:
            r = requests_retry_session().get(chorgurl)
            # r = requests.head(chorgurl)
        except:
            continue

        if r.status_code != 200:
            print('### ERROR ON http-call forcath-id: ' + mycathid)
            continue
        if r.status_code == 200:
            print('>> Catholic-Hierarchy-Id: ' + mycathid)
            print('-- URL: ' + chorgurl)
            try:
                t = lxml.html.parse(chorgurl)
            except:
                continue

            mytitle = t.find(".//title").text
            mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
            print('-- Title: ' + mytitle)

            diocesan_bishopship_tr = re.findall(b"<tr><td[^>]+>.*</td><td>.*</td><td>Bishop of (.*)</td>.*</tr>", r.content)

            if not diocesan_bishopship_tr:
                print('-- Seems not to be a bishop(!)')
                continue

            diocesan_bishopship_tr = list(set(diocesan_bishopship_tr))

            for x, value in enumerate(diocesan_bishopship_tr, 0):
                dioceseid = re.findall(b'href="/diocese/d([a-z0-9]+).html"', diocesan_bishopship_tr[x])
                if not dioceseid:
                    print('### Diocese-Id not found!')
                    continue

                l_dbishop.append(dioceseid[0].decode('utf-8'))
                l_dbishop = list(set(l_dbishop))
                print('-- Dioceses found: ' + ', '.join(l_dbishop))

                for dbishop in l_dbishop:
                    mydiowd = dioid2wd(dbishop)
                    if mydiowd:
                        l_associated_dioceseids.append(mydiowd)

                for known_dbishopship in l_known_dbishopships:
                    a_qualis = known_dbishopship.qualifiers
                    if not 'P708' in a_qualis:
                        continue
                    if len(a_qualis['P708']) > 1:
                        print('-- !!! Take care there are more than 1 Dio-Claims!')
                        continue

                    diozese_claim = a_qualis['P708'][0]
                    trgt_d = diozese_claim.getTarget()
                    if trgt_d.id in l_associated_dioceseids:
                        print('-- Found diocesan bishopship with already known and matching Diozese-Claim. (' + str(trgt_d.id) + ' in ' + ', '.join(l_associated_dioceseids) + ')')
                        claim_sources = known_dbishopship.getSources()
                        if not claim_sources:
                            print('>>> Adding Source Claim')
                            source_claim = pywikibot.Claim(repo, 'P1047')
                            source_claim.setTarget(mycathid)
                            known_dbishopship.addSources([source_claim], summary='add catholic-hierarchy as source for diocesan bishop position')
                            continue
                        else:
                            print('--- Sources already given.')

print('Done!')
