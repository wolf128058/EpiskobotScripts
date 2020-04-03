#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators as pg

import os
from os import system

import re
import requests

import progressbar


def sparql_namesearch(firstname):
    querystring = '''
    SELECT ?item ?itemLabel WHERE {
    { ?item wdt:P31 wd:Q12308941;
      rdfs:label "''' + firstname + '''"@en. }
    UNION {
      ?item wdt:P31 wd:Q12308941;
      rdfs:label "''' + firstname + '''"@de. }
    UNION {
      ?item wdt:P31 wd:Q12308941;
      rdfs:label "''' + firstname + '''"@it. }
    UNION {
      ?item wdt:P31 wd:Q3409032;
      rdfs:label "''' + firstname + '''"@en. }
    UNION {
      ?item wdt:P31 wd:Q3409032;
      rdfs:label "''' + firstname + '''"@de. }
    UNION {
      ?item wdt:P31 wd:Q3409032;
      rdfs:label "''' + firstname + '''"@it. }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en,it". }
    } LIMIT 1'''
    return querystring


path4qs = 'data/log_quick_namefounds.txt'

QUERY = """
# ohne vornamen
SELECT ?item ?itemLabel ?cathiLabel WHERE {
  ?item wdt:P1047 ?cathi;
    wdt:P31 wd:Q5;
    wdt:P21 wd:Q6581097;

  FILTER(NOT EXISTS { ?item wdt:P735 ?statement. })
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en,it,nl,ast,sl". }
}
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)

repo = wikidata_site.data_repository()

Names2Items = dict()
NoNames = list()

counter = 0
with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        #    if counter >= 1000:
        #        break
        changed = False
        item.get(get_redirect=True)
        mylabel = ''
        myid = item.id
        print('>>> Examining: ' + item.id)
        print('--- URL: https://www.wikidata.org/wiki/' + item.id)
        if 'de' in item.labels and mylabel == '':
            mylabel = item.labels['de']
        if 'en' in item.labels and mylabel == '':
            mylabel = item.labels['en']
        if 'it' in item.labels and mylabel == '':
            mylabel = item.labels['it']
        if 'nl' in item.labels and mylabel == '':
            mylabel = item.labels['nl']
        if 'ast' in item.labels and mylabel == '':
            mylabel = item.labels['ast']
        if 'sl' in item.labels and mylabel == '':
            mylabel = item.labels['sl']
        print('--- Label:"' + mylabel + '"')

        if mylabel == '':
            print('!!! empty label. i skip.' + "\n")
            continue

        words = mylabel.split()
        firstname = words[0]
        firstname = firstname.encode('utf8')

        if firstname in Names2Items:
            print('--- I know "' + firstname.decode('utf-8') + '" is a first name.')
            fq = open(path4qs, "a")
            fq.write("\n" + myid + "\tP735\t" + Names2Items[firstname])
            counter += 1
            fq.close()
        elif firstname in NoNames:
            print('--- I know "' + firstname.decode('utf-8') + '" is NOT A KNOWN first name.')
        elif firstname not in NoNames:
            print('--- I guess "' + words[0] + '" could be a first name.')
            FN_SPARQL = sparql_namesearch(firstname.decode('utf-8'))
            subgenerator_fn = pg.WikidataSPARQLPageGenerator(FN_SPARQL, site=wikidata_site)
            match = False
            for item in subgenerator_fn:
                match = True
                mynameitem = item.get(get_redirect=True)
                print('### Male firstname found: "' + words[0] + '" is ' + item.id)
                Names2Items[firstname] = item.id
                fq = open(path4qs, "a")
                fq.write("\n" + myid + "\tP735\t" + item.id)
                counter += 1
                fq.close()
            if match == False:
                NoNames.append(firstname)
        print("\n")
        bar.update(index)

print('Done!')
