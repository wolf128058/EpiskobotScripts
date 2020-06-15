#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import random
import pywikibot
from pywikibot import pagegenerators as pg


INITIAL_OFFICEHOLDER = 'Q69064'
POSITION = 'Q1144278'  # D-Bishop
COMMON_PROP_KEY = 'P708'  # Diocese
COMMON_PROP_VALUE = 'Q835426'  # Rottenburg-Stuttgart
KEY_PREDECESSOR = 'P1365'
KEY_SUCCESSOR = 'P1366'
QS_OUTPUT = ''

site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

if len(sys.argv) == 4:
    POSITION = sys.argv[1]
    COMMON_PROP_VALUE = sys.argv[2]
    INITIAL_OFFICEHOLDER = sys.argv[3]

if len(sys.argv) == 2:
    POSITION = sys.argv[1]
    QUERY = '''
    SELECT ?item WHERE {
      ?item wdt:P39 wd:''' + POSITION + ''' .
      FILTER(NOT EXISTS {?item wdt:P39 wd:Q157037})
      FILTER(EXISTS {
        ?item p:P39 ?pos.
        ?pos pq:P1365 ?statement.
      })
      FILTER(NOT EXISTS {
        ?item p:P39 ?pos.
        ?pos pq:P1366 ?statement.
      })
      FILTER(EXISTS {
        ?item p:P570 ?statement.
      })
      FILTER(NOT EXISTS {
        ?item p:P39 ?pos.
        ?pos pq:P1545 "1".
      })
    }
    LIMIT 5000
'''
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
    generator = list(generator)
    candidate = random.choice(generator)
    candidate_item = candidate.get(get_redirect=True)
    INITIAL_OFFICEHOLDER = candidate.id
    print('>> RANDOM CANDIDATE: https://www.wikidata.org/wiki/' + candidate.id)
    claim_list_pos = candidate_item['claims']['P39']
    predecessor = False
    for pos_item in claim_list_pos:

        pos_item_target = pos_item.getTarget()
        if pos_item_target.id != POSITION:
            print('-- ' + pos_item_target.id + ' is not the correct pos-claim, i skip that one')
            continue
        else:
            print('-- Correct pos-claim.')

        my_pos_data = pos_item.getTarget()
        if my_pos_data.id != POSITION:
            continue

        qualifiers = pos_item.qualifiers
        if not qualifiers:
            print('--- Skipping Entry for ' + pos_item.id + ' without qualifiers')
            continue

        if qualifiers[COMMON_PROP_KEY]:
            my_propval = qualifiers[COMMON_PROP_KEY][0].getTarget()
            print('-- There is a diocese: ' + my_propval.id)
            COMMON_PROP_VALUE = my_propval.id

        try:
            if qualifiers[KEY_PREDECESSOR]:
                print('-- There is a predecessor.')
                predecessor = True
        except:
            print('-- There is no predecessor.')
            continue

    if predecessor == False:
        exit()


if len(sys.argv) == 3:
    POSITION = sys.argv[1]
    COMMON_PROP_VALUE = sys.argv[2]
    QUERY = '''
    SELECT ?item ?itemLabel ?birthLabel ?deathLabel WHERE {
      ?item wdt:P39 wd:''' + POSITION + ''';
        p:P39 ?DBship.
      ?DBship pq:P708 wd:''' + COMMON_PROP_VALUE + '''.
      OPTIONAL { ?item wdt:P569 ?birth. }
      OPTIONAL { ?item wdt:P570 ?death. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],de". }
    }
    GROUP BY (?item) (?itemLabel) (?birthLabel) (?deathLabel)
    ORDER BY DESC (?birthLabel) (?deathLabel)
    LIMIT 10
    '''
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
    generator = list(generator)
    initial_candidate = False

    if not generator:
        print('No initial Candidate found.')
        exit()
    else:
        candidate_found = False
        for candidate in generator:
            if candidate_found:
                break
            candidate_item = candidate.get(get_redirect=True)
            print('>> RANDOM CANDIDATE: https://www.wikidata.org/wiki/' + candidate.id)
            claim_list_pos = candidate_item['claims']['P39']

            for pos_item in claim_list_pos:

                pos_item_target = pos_item.getTarget()
                if pos_item_target.id != POSITION:
                    print('-- ' + pos_item_target.id + ' is not the correct pos-claim (' + POSITION + '), i skip that one')
                    continue
                else:
                    print('-- Correct pos-claim.')

                my_pos_data = pos_item.getTarget()
                if my_pos_data.id != POSITION:
                    continue

                qualifiers = pos_item.qualifiers
                if not qualifiers:
                    print('--- Skipping Entry for ' + pos_item.id + ' without qualifiers')
                    continue

                try:
                    if qualifiers[COMMON_PROP_KEY]:
                        my_propval = qualifiers[COMMON_PROP_KEY][0].getTarget()
                        if(my_propval.id != COMMON_PROP_VALUE):
                            print('-- Skipping wrong diocese: ' + my_propval.id + '(Searching for: ' + COMMON_PROP_VALUE + ')')
                            continue
                except:
                    print('-- Entry has no diocese -> skipping.')
                    continue

                try:
                    if qualifiers[KEY_PREDECESSOR]:
                        print('-- There is a predecessor.')
                        candidate_found = True
                        initial_candidate = candidate.id
                except:
                    print('-- There is no predecessor.')
                    continue

        if candidate_found == False:
            print('No matching candidate for Position ' + POSITION + ' in Dio ' + COMMON_PROP_VALUE + ' found.')
            exit()

        INITIAL_OFFICEHOLDER = initial_candidate
        print('>>> Starting the Chain with: : https://www.wikidata.org/wiki/' + str(INITIAL_OFFICEHOLDER))


def set_successor(officeholder, office, pkey, pvalue, successor):
    print('--- Setting ' + successor + ' as successor of ' + officeholder)
    item = pywikibot.ItemPage(repo, officeholder)
    mywd = item.get(get_redirect=True)
    claim_list_pos = mywd['claims']['P39']
    for pos_item in claim_list_pos:
        my_pos_data = pos_item.getTarget()
        if my_pos_data.id != office:
            continue

        qualifiers = pos_item.qualifiers
        if not qualifiers:
            print('--- Skipping Entry for ' + office + ' without qualifiers')
            continue

        try:
            if qualifiers[pkey]:
                my_propval = qualifiers[pkey][0].getTarget()
                if my_propval.id != pvalue:
                    # key-value-macht not found
                    continue
        except:
            continue

        try:
            if qualifiers[KEY_SUCCESSOR]:
                print('!! There is already a successor. I skip that one.')
                continue
        except:
            q_succ = pywikibot.Claim(repo, KEY_SUCCESSOR, is_qualifier=True)
            succ_claim = pywikibot.ItemPage(repo, successor)
            q_succ.setTarget(succ_claim)
            pos_item.addQualifier(q_succ, summary=u'added successor reciprocally')


def get_predecessor(officeholder):
    print()
    print('>> CHECKING: https://www.wikidata.org/wiki/' + officeholder)
    item = pywikibot.ItemPage(repo, officeholder)
    try:
        mywd = item.get()
    except:
        print('-- Redirection found.')
        mywd = item.get(get_redirect=True)
    claim_list_pos = mywd['claims']['P39']

    for pos_item in claim_list_pos:
        found_predecessor = False
        my_predecessor_id = False
        my_pos_data = pos_item.getTarget()
        if my_pos_data.id == POSITION:
            print('- Target POS-Claim found: ' + POSITION)
            qualifiers = pos_item.qualifiers

            if not qualifiers:
                continue

            try:
                if qualifiers[COMMON_PROP_KEY]:
                    my_propval = qualifiers[COMMON_PROP_KEY][0].getTarget()
                    if my_propval.id == COMMON_PROP_VALUE:
                        print('- Qualifier-Match[' + COMMON_PROP_KEY + '] == ' + COMMON_PROP_VALUE)
                    else:
                        continue
            except:
                continue

            try:
                if qualifiers[KEY_SUCCESSOR]:
                    my_successor = qualifiers[KEY_SUCCESSOR][0].getTarget()
                    my_successor_id = my_successor.id
                    print('- Successor: ' + my_successor_id)
            except:
                print('- No Successor found. (For ' + officeholder + ' as ' + POSITION + ' of ' + COMMON_PROP_VALUE + ')')

            try:
                if qualifiers[KEY_PREDECESSOR]:
                    my_predecessor = qualifiers[KEY_PREDECESSOR][0].getTarget()
                    my_predecessor_id = my_predecessor.id
                    print('- Predecessor: ' + my_predecessor_id)
                    found_predecessor = True
            except:
                print('- No Predecessor found. (For ' + officeholder + ' as ' + POSITION + ' of ' + COMMON_PROP_VALUE + ')')
                return False

            if found_predecessor:
                return my_predecessor_id

# START THAT LOOP:


CURRENT_PREDECESSOR = INITIAL_OFFICEHOLDER

chain_running = True
CURRENT_PREDECESSOR = get_predecessor(INITIAL_OFFICEHOLDER)

if CURRENT_PREDECESSOR == False and POSITION == 'Q48629921':
    print('-- Trying to downgrade from Archbishop-Chain to Diocesanbishop-Chain')
    POSITION = 'Q1144278'
    CURRENT_PREDECESSOR = get_predecessor(INITIAL_OFFICEHOLDER)

if CURRENT_PREDECESSOR == False:
    chain_running = False
else:
    set_successor(CURRENT_PREDECESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, INITIAL_OFFICEHOLDER)


while chain_running:
    old_predecessor = CURRENT_PREDECESSOR
    CURRENT_PREDECESSOR = get_predecessor(CURRENT_PREDECESSOR)

    if CURRENT_PREDECESSOR == False and POSITION == 'Q48629921':
        print('-- Trying to downgrade from Archbishop to Diocesanbishop')
        POSITION = 'Q1144278'
        CURRENT_PREDECESSOR = get_predecessor(old_predecessor)

    if not CURRENT_PREDECESSOR:
        chain_running = False
    else:
        set_successor(CURRENT_PREDECESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, old_predecessor)

print('Done')
