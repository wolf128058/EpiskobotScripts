#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import os
from random import shuffle
import progressbar

import pywikibot
from pywikibot import pagegenerators as pg


def position2query(position_id):
    QUERY = '''
SELECT ?item ?diocese WHERE {
  ?item p:P39 ?position.
  ?position ps:P39 wd:''' + position_id + ''';
    pq:P708 ?diocese.
  FILTER(NOT EXISTS { ?position pq:P1365 ?statement. })
  FILTER(NOT EXISTS { ?position pq:P1545 "1". })
}
    '''
    return QUERY


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
POSITIONS = ['Q1144278', 'Q48629921']
WINNER = {'position': '', 'diocese': '', 'candidates': ''}
STATISTICS = {}
LISTS = {}

for pos in POSITIONS:
    print('- Getting Positions of ' + pos)
    POS_QUERY = position2query(pos)
    generator = pg.WikidataSPARQLPageGenerator(POS_QUERY, site=wikidata_site)
    generator = list(generator)
    shuffle(generator)
    STATISTICS[pos] = len(generator)
    LISTS[pos] = generator
    print('-- found: ' + str(STATISTICS[pos]))

MAX_STAT = 0
for key, stat in STATISTICS.items():
    if stat > MAX_STAT:
        WINNER['position'] = key
        MAX_STAT = stat

DIO_STAT = {}

counter = 0
with progressbar.ProgressBar(max_value=len(LISTS[WINNER['position']]), redirect_stdout=True) as bar:
    for entry in LISTS[WINNER['position']]:
        bar.update(counter)
        counter += 1
        mywd = entry.get(get_redirect=True)
        claim_list_pos = mywd['claims']['P39']
        for claimed_pos in claim_list_pos:
            my_pos_data = claimed_pos.getTarget()
            if my_pos_data.id == WINNER['position']:
                my_qualifiers = claimed_pos.qualifiers
                for qualifier in my_qualifiers:
                    if qualifier == 'P708':
                        # print('https://www.wikidata.org/wiki/' + entry.id)
                        my_params = {}
                        to_json = claimed_pos.toJSON()
                        my_params['dio'] = 'Q' + str(to_json['qualifiers']['P708'][0]['datavalue']['value']['numeric-id'])
                        my_params['pos'] = my_pos_data.id
                        my_params['me'] = entry.id
                        print(my_params)
                        os.system('python3 set_predecessor.py -s 1 -p ' + my_params['pos'] + ' -d ' + my_params['dio'] + ' -o ' + my_params['me'])
