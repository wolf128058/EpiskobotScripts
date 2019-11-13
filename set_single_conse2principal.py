#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import requests
import re
import lxml.html


QUERY = '''
SELECT ?item ?itemLabel (COUNT(?conse) AS ?count) WHERE {
  ?item wdt:P1047 ?catid;
    wdt:P1598 ?conse.
  FILTER(NOT EXISTS {
    ?item p:P1598 ?func.
    ?func pq:P3831 wd:Q18442817.
  })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de,en". }
}
GROUP BY ?item ?itemLabel
HAVING (?count = 1 )
# LIMIT 5000
'''

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
repo = wikidata_site.data_repository()

for item in generator:
    itemdetails = item.get(get_redirect=True)
    conse_getter_id = item.id

    mycathid = ''

    claim_list_conse = itemdetails['claims']['P1598']
    claim_list_cathid = itemdetails['claims']['P1047']

    for cathids in claim_list_cathid:
        mycathid = cathids.getTarget()
        print "\n" + '>> Catholic-Hierarchy-Id: ' + mycathid

    if len(claim_list_cathid) != 1:
        continue

    consecount = len(claim_list_conse)

    print '-- Consecrator-Amount: {}.'.format(consecount)
    if consecount != 1:
        continue

    conse_details = claim_list_conse[0].getTarget()
    print '-- Conse on WD: ' + conse_details.id

    chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'

    try:
        r = requests.head(chorgurl)
    except:
        continue

    if r.status_code != 200:
        print '### ERROR ON cath-id: ' + mycathid
    if r.status_code == 200:
        print '-- URL: ' + chorgurl
        t = lxml.html.parse(chorgurl)
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
                    print '-- Conse on ch.org: ' + conse_match.groups()[0]
                    SUBQUERY_CONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + conse_match.groups()[0] + '". }'
                    subgenerator_conse = pg.WikidataSPARQLPageGenerator(SUBQUERY_CONSE, site=wikidata_site)
                    count_conse_found = 0
                    for item in subgenerator_conse:
                        count_conse_found += 1
                        conse_setter_id = item.id
                    if count_conse_found == 1:
                        print '-- Principal-Conse found: ' + conse_setter_id + ' => ' + conse_getter_id
                        if conse_details.id == conse_setter_id:

                            try:
                                if(len(claim_list_conse[0].qualifiers['P2868']) == 1):
                                    myqual = claim_list_conse[0].qualifiers['P2868'][0]
                                    print '-- Subject-Qualifier detected ... Removing'
                                    claim_list_conse[0].removeQualifiers([myqual], summary=u'removed the principal consecrator via P2868')
                            except:
                                print '-- No wrong qualifier detected. Good boy!'

                            print '~~~ That is correct. I will tag that as principal consecrator.'
                            q_as = pywikibot.Claim(repo, 'P3831', is_qualifier=True)
                            principal_claim = pywikibot.ItemPage(repo, u'Q18442817')
                            q_as.setTarget(principal_claim)
                            try:
                                claim_list_conse[0].addQualifier(q_as, summary=u'checked on catholic-hierarchy: this is the principal consecrator via P3831(!)')
                                print '--- Success!'
                            except:
                                continue

print('Done!')
