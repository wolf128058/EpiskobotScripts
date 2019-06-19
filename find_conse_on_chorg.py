#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import lxml.html
import re
import requests

path4qs ='log_quick_consefounds.txt'

QUERY = """
SELECT ?item ?itemLabel ?birthLabel ?cathiLabel WHERE {
  ?item wdt:P1047 ?cathi.
  FILTER(NOT EXISTS { ?item wdt:P1598 ?statement. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
ORDER BY (RAND())"""

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
            break
        chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

        try:
            r = requests.head(chorgurl)
        except:
            break

        if r.status_code != 200:
            print '### ERROR ON cath-id: ' + mycathid
        if r.status_code == 200:
            print ''
            print '>> Catholic-Hierarchy-Id: ' + mycathid
            print '-- URL: ' + chorgurl

            try:
                t = lxml.html.parse(chorgurl)
            except:
                break

            mytitle = t.find(".//title").text
            mytitle = mytitle.replace(' [Catholic-Hierarchy]', '')
            print '-- Title: ' + mytitle
            mylistitems = t.findall(".//li")
            has_conse = 0
            for listitem in mylistitems:
                if listitem.text == 'Principal Consecrator:':
                    has_conse = 1
                    firstlink = listitem.find('.//a[@href]')
                    firsthref = firstlink.attrib['href']
                    conse_match = re.match('b([0-9a-z]+)\.html', firsthref)
                    if conse_match:
                        print '-- conse: ' + conse_match.groups()[0]
                        SUBQUERY = 'SELECT ?item WHERE { ?item wdt:P1047 "' + conse_match.groups()[
                            0] + '". }'
                        subgenerator = pg.WikidataSPARQLPageGenerator(
                            SUBQUERY, site=wikidata_site)
                        count_conse_found = 0
                        for item in subgenerator:
                            count_conse_found += 1
                            conse_setter_id = item.id
                        if count_conse_found == 1:
                            print '!!! Conse found: ' + conse_setter_id + ' => ' + conse_getter_id
                            f.write("\n" + 'https://www.wikidata.org/wiki/' +
                                    conse_getter_id + "\t\t" + conse_setter_id)
                            fq = open(path4qs, "a")
                            fq.write("\n" + conse_getter_id +
                                     "\tP1598\t" + conse_setter_id)
                            fq.close()

print('Done!')
