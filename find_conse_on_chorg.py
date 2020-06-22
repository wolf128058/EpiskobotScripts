#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import os
import re
from random import shuffle

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


path4qs = 'data/log_quick_consefounds.txt'

QUERY = """
SELECT ?item  ?birthLabel WHERE {
  ?item wdt:P1047 ?cathi.
  OPTIONAL {?item wdt:P569 ?birth}
 FILTER( EXISTS { ?item wdt:P1598 ?statement. })
# FILTER(NOT EXISTS { ?item wdt:P1598 ?statement. })
#  FILTER((YEAR(?birth)) >= 1584 )
}
# ORDER BY ASC (?birthLabel)
# LIMIT 5000
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')

shuffle(generator)

repo = wikidata_site.data_repository()

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        bar.update(index)
        itemdetails = item.get(get_redirect=True)
        mycathid = ''
        changed = False
        conse_getter_id = item.id
        print('>> CHECKING: Wikidata-Item: https://www.wikidata.org/wiki/' + conse_getter_id)
        conse_setter_id = ''
        claim_list_cathid = itemdetails['claims']['P1047']
        try:
            claim_list_conses = itemdetails['claims']['P1598']
        except:
            claim_list_conses = []

        known_conses = []

        for conse in claim_list_conses:
            myconse = conse.getTarget()
            if not myconse:
                continue
            known_conses.append(myconse.id)

        if known_conses:
            print(known_conses)

        for cathids in claim_list_cathid:
            mycathid = cathids.getTarget()
            if not mycathid:
                continue
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            r = requests_retry_session().get(chorgurl)

            try:
                r = requests_retry_session().get(chorgurl)
                # r = requests.head(chorgurl)
            except:
                continue

            if r.status_code != 200:
                print('### ERROR ON cath-id: ' + mycathid)
            if r.status_code == 200:
                print('')
                print('>> Catholic-Hierarchy-Id: ' + mycathid)
                print('-- URL: ' + chorgurl)

                try:
                    t = lxml.html.parse(chorgurl)
                except:
                    continue

                mytitle = t.find(".//title").text
                mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
                print('-- Title: ' + mytitle)
                mylistitems = t.findall(".//li")
                for listitem in mylistitems:
                    if listitem.text == 'Principal Consecrator:':
                        firstlink = listitem.find('.//a[@href]')
                        firsthref = firstlink.attrib['href']
                        conse_match = re.match('b([0-9a-z]+).html', firsthref)
                        if conse_match:
                            print('-- conse: ' + conse_match.groups()[0])
                            SUBQUERY_CONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + conse_match.groups()[
                                0] + '". }'
                            subgenerator_conse = pg.WikidataSPARQLPageGenerator(
                                SUBQUERY_CONSE, site=wikidata_site)
                            count_conse_found = 0
                            for conse_item in subgenerator_conse:
                                count_conse_found += 1
                                conse_setter_id = conse_item.id
                            if count_conse_found == 1:
                                print('!!! Conse found: ' + conse_setter_id + ' => ' + conse_getter_id)
                                if conse_setter_id in known_conses:
                                    print('- this is a known one, we skip the quick-statement and add a source')

                                    for conse in claim_list_conses:
                                        myconse = conse.getTarget()
                                        if myconse.id == conse_setter_id:
                                            conse_claim_sources = conse.getSources()
                                            if not conse_claim_sources:
                                                source_claim = pywikibot.Claim(repo, 'P1047')
                                                source_claim.setTarget(mycathid)
                                                conse.addSources([source_claim], summary='add catholic-hierarchy as source for consecrator')
                                    continue

                                fq = open(path4qs, "a")
                                fq.write("\n" + conse_getter_id +
                                         "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442817" +
                                         "\tS1047\t\"" + mycathid + "\"")
                                fq.close()
                            elif count_conse_found == 0:
                                print('-- checking ch.org for conse-info: ' + 'http://www.catholic-hierarchy.org/bishop/b' + conse_match.groups()[0] + '.html')
                                os.system("./create_by_chorg-id.py " + conse_match.groups()[0] + " create_quick_log.txt")

                    elif listitem.text == 'Principal Co-Consecrators:' and count_conse_found == 1:
                        links = listitem.findall('.//a[@href]')

                        for link_item in links:
                            myhref = link_item.attrib['href']
                            coconse_match = re.match('b([0-9a-z]+).html', myhref)
                            if coconse_match:
                                print('-- co-conse: ' + coconse_match.groups()[0])
                                SUBQUERY_COCONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + coconse_match.groups()[
                                    0] + '". }'
                                subgenerator_coconse = pg.WikidataSPARQLPageGenerator(
                                    SUBQUERY_COCONSE, site=wikidata_site)
                                count_coconse_found = 0
                                for coconse_item in subgenerator_coconse:
                                    count_coconse_found += 1
                                    conse_setter_id = coconse_item.id
                                    if count_coconse_found >= 1:
                                        print('!!! Co-Conse found: ' + conse_setter_id + ' => ' + conse_getter_id)
                                        if conse_setter_id in known_conses:
                                            print('- this is a known one, we skip the quick-statement and add a source')

                                            for conse in claim_list_conses:
                                                myconse = conse.getTarget()
                                                if myconse.id == conse_setter_id:
                                                    conse_claim_sources = conse.getSources()
                                                    if not conse_claim_sources:
                                                        source_claim = pywikibot.Claim(repo, 'P1047')
                                                        source_claim.setTarget(mycathid)
                                                        conse.addSources([source_claim], summary='add catholic-hierarchy as source for consecrator')
                                            continue
                                        fq = open(path4qs, "a")
                                        fq.write("\n" + conse_getter_id +
                                                 "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442822"
                                                 "\tS1047\t\"" + mycathid + "\"")

                                        fq.close()
                                    elif count_conse_found == 0:
                                        print('-- checking ch.org for co-conse-info: ' + 'http://www.catholic-hierarchy.org/bishop/b' + conse_match.groups()[0] + '.html')
                                        os.system("./create_by_chorg-id.py " + conse_match.groups()[0] + " create_quick_log.txt")


print('Done!')
