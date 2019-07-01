#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import os
from os import system

import lxml.html
import re
import requests

path4qs = 'log_quick_consefounds.txt'

QUERY = """
SELECT ?item ?itemLabel ?cathiLabel ?birthLabel WHERE {
  ?item wdt:P1047 ?cathi.
  OPTIONAL {?item wdt:P569 ?birth}
  FILTER(NOT EXISTS { ?item wdt:P1598 ?statement. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
  FILTER((YEAR(?birth)) >= 0 )
}
ORDER BY DESC (?birthLabel)"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get()
    mycathid = ''
    changed = False
    conse_getter_id = item.id
    conse_setter_id = ''
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        if len(mycathid) == 0:
            continue
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

        try:
            r = requests.head(chorgurl)
        except:
            continue

        if r.status_code != 200:
            print '### ERROR ON cath-id: ' + mycathid
        if r.status_code == 200:
            print ''
            print '>> Catholic-Hierarchy-Id: ' + mycathid
            print '-- URL: ' + chorgurl

            try:
                t = lxml.html.parse(chorgurl)
            except:
                continue

            mytitle = t.find(".//title").text
            mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
            print '-- Title: ' + mytitle
            mylistitems = t.findall(".//li")
            for listitem in mylistitems:
                if listitem.text == 'Principal Consecrator:':
                    firstlink = listitem.find('.//a[@href]')
                    firsthref = firstlink.attrib['href']
                    conse_match = re.match('b([0-9a-z]+)\.html', firsthref)
                    if conse_match:
                        print '-- conse: ' + conse_match.groups()[0]
                        SUBQUERY_CONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + conse_match.groups()[
                            0] + '". }'
                        subgenerator_conse = pg.WikidataSPARQLPageGenerator(
                            SUBQUERY_CONSE, site=wikidata_site)
                        count_conse_found = 0
                        for item in subgenerator_conse:
                            count_conse_found += 1
                            conse_setter_id = item.id
                        if count_conse_found == 1:
                            print '!!! Conse found: ' + conse_setter_id + ' => ' + conse_getter_id
                            fq = open(path4qs, "a")
                            fq.write("\n" + conse_getter_id +
                                     "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442817")
                            fq.close()
                        elif count_conse_found == 0:
                            print '-- checking ch.org for conse-info: ' + 'http://www.catholic-hierarchy.org/bishop/b' + conse_match.groups()[0] + '.html'
                            os.system("./create_by_chorg-id.py " + conse_match.groups()[0] + " create_quick_log.txt")

                elif listitem.text == 'Principal Co-Consecrators:' and count_conse_found == 1:
                    firstlink = listitem.find('.//a[@href]')
                    firsthref = firstlink.attrib['href']
                    coconse_match = re.match('b([0-9a-z]+)\.html', firsthref)
                    if coconse_match:
                        print '-- co-conse: ' + coconse_match.groups()[0]
                        SUBQUERY_COCONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + coconse_match.groups()[
                            0] + '". }'
                        subgenerator_coconse = pg.WikidataSPARQLPageGenerator(
                            SUBQUERY_COCONSE, site=wikidata_site)
                        count_coconse_found = 0
                        for item in subgenerator_coconse:
                            count_coconse_found += 1
                            conse_setter_id = item.id
                            if count_coconse_found >= 1:
                                print '!!! Co-Conse found: ' + conse_setter_id + ' => ' + conse_getter_id
                                fq = open(path4qs, "a")
                                fq.write("\n" + conse_getter_id +
                                         "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442822")
                                fq.close()
                            elif count_conse_found == 0:
                                print '-- checking ch.org for co-conse-info: ' + 'http://www.catholic-hierarchy.org/bishop/b' + conse_match.groups()[0] + '.html'
                                os.system("./create_by_chorg-id.py " + conse_match.groups()[0] + " create_quick_log.txt")


print('Done!')
