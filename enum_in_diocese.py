#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long, C0103, W0702, C0116, C0114

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
KEY_SERIESNR = 'P1545'
QS_OUTPUT = ''
CANDIDATE_FOUND = False

site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

if len(sys.argv) == 4:
    POSITION = sys.argv[1]
    COMMON_PROP_VALUE = sys.argv[2]
    INITIAL_OFFICEHOLDER = sys.argv[3]

if len(sys.argv) == 3:
    POSITION = sys.argv[1]
    COMMON_PROP_VALUE = sys.argv[2]
    QUERY4FIRST = 'SELECT ?item WHERE {  ?item wdt:P39 wd:' + POSITION + '; p:P39 [ ps:P39 ?pos; pq:P708 wd:' + COMMON_PROP_VALUE + '; ps:P39 wd:' + POSITION + '; pq:P1545 \'1\'].}'
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    generator = pg.WikidataSPARQLPageGenerator(QUERY4FIRST, site=wikidata_site)
    generator = list(generator)
    if len(generator) == 0:
        print('Found no candidate with position = 1')
    elif len(generator) == 1:
        INITIAL_OFFICEHOLDER = generator[0].id
        CANDIDATE_FOUND = True
        print('>> INITIAL CANDIDATE: https://www.wikidata.org/wiki/' + INITIAL_OFFICEHOLDER)

if len(sys.argv) == 2:
    POSITION = sys.argv[1]
    QUERY = '''
    SELECT ?item WHERE {
      ?item wdt:P39 wd:''' + POSITION + ''' .
      FILTER(NOT EXISTS {?item wdt:P39 wd:Q157037})
      FILTER(EXISTS {
        ?item p:P39 ?pos.
        ?pos pq:''' + KEY_SUCCESSOR + ''' ?statement.
      })
      FILTER(NOT EXISTS {
        ?item p:P39 ?pos.
        ?pos pq:''' + KEY_PREDECESSOR + ''' ?statement.
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
    QUERY = '''
        SELECT ?item  (COUNT(?bishop) AS ?cnt)  WHERE {
        ?bishop wdt:P39 wd:''' + POSITION + ''';
                p:P39 [ ps:P39 ?pos; pq:P708 ?item; ps:P39 wd:''' + POSITION + ''' ].
        FILTER(NOT EXISTS {?pos pq:P1545 ?statement})
        FILTER(NOT EXISTS {?item wdt:P31 wd:Q15217609})
        }
        group by (?item)
        having (?cnt > 1 && ?cnt < 6)
    '''
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    dio_generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
    dio_generator = list(dio_generator)
    print('>> Found ' + str(len(dio_generator)) + ' dioceses.')
    found_dio = False
    while not found_dio:
        dio_candidate = random.choice(dio_generator)
        dio_candidate_item = dio_candidate.get(get_redirect=True)
        print('>> RANDOM DIOCESE: https://www.wikidata.org/wiki/' + dio_candidate.id)
        QUERY4FIRST = 'SELECT ?item WHERE {  ?item wdt:P39 wd:' + POSITION + '; p:P39 [ ps:P39 ?pos; pq:P708 wd:' + dio_candidate.id + '; pq:P1366 ?successor ; ps:P39 wd:' + POSITION + '; pq:P1545 \'1\'].}'
        wikidata_site = pywikibot.Site('wikidata', 'wikidata')
        generator = pg.WikidataSPARQLPageGenerator(QUERY4FIRST, site=wikidata_site)
        generator = list(generator)
        if len(generator) > 0:
            found_dio = True
            holder = generator[0]
            print('>> FIRST CANDIDATE: https://www.wikidata.org/wiki/' + holder.id)
            INITIAL_OFFICEHOLDER = holder.id

    holder_item = holder.get(get_redirect=True)
    claim_list_pos = holder_item['claims']['P39']
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
            if qualifiers[KEY_SUCCESSOR]:
                print('-- There is a successor.')
                predecessor = True
        except:
            print('-- There is no successor.')
            continue

    if not predecessor:
        exit()

if len(sys.argv) == 3 and CANDIDATE_FOUND == False:
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
        CANDIDATE_FOUND = False
        for candidate in generator:
            if CANDIDATE_FOUND:
                break
            candidate_item = candidate.get(get_redirect=True)
            print('>> RANDOM CANDIDATE: https://www.wikidata.org/wiki/' + candidate.id)
            claim_list_pos = candidate_item['claims']['P39']

            for pos_item in claim_list_pos:

                pos_item_target = pos_item.getTarget()
                if pos_item_target.id != POSITION:
                    print(
                        '-- ' + pos_item_target.id + ' is not the correct pos-claim (' + POSITION + '), i skip that one')
                    continue
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
                        if my_propval.id != COMMON_PROP_VALUE:
                            print(
                                '-- Skipping wrong diocese: ' + my_propval.id + '(Searching for: ' + COMMON_PROP_VALUE + ')')
                            continue
                except:
                    print('-- Entry has no diocese -> skipping.')
                    continue

                try:
                    if qualifiers[KEY_SUCCESSOR]:
                        print('-- There is a successor.')
                        CANDIDATE_FOUND = True
                        initial_candidate = candidate.id
                except:
                    print('-- There is no successor.')
                    continue

        if not CANDIDATE_FOUND:
            print('No matching candidate for Position ' + POSITION + ' in Dio ' + COMMON_PROP_VALUE + ' found.')
            exit()

        INITIAL_OFFICEHOLDER = initial_candidate
        print('>>> Starting the Chain with: : https://www.wikidata.org/wiki/' + str(INITIAL_OFFICEHOLDER))


def set_predecessor(officeholder, office, pkey, pvalue, predecessor):
    print('--- Setting ' + predecessor + ' as predecessor of ' + officeholder)
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
            if qualifiers[KEY_PREDECESSOR]:
                print('!! There is already a predecessor. I skip that one.')
                continue
        except:
            q_succ = pywikibot.Claim(repo, KEY_PREDECESSOR, is_qualifier=True)
            succ_claim = pywikibot.ItemPage(repo, predecessor)
            q_succ.setTarget(succ_claim)
            pos_item.addQualifier(q_succ, summary=u'added predecessor reciprocally')


def get_successor(officeholder):
    print()
    print('>> CHECKING (SUCC): https://www.wikidata.org/wiki/' + officeholder)
    item = pywikibot.ItemPage(repo, officeholder)
    try:
        mywd = item.get()
    except:
        print('-- Redirection found.')
        mywd = item.get(get_redirect=True)

    claim_list_pos = mywd['claims']['P39']

    for pos_item in claim_list_pos:
        found_successor = False
        my_successor_id = False
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
                        print('- NO Qualifier-Match[' + my_propval.id + ']')
                        continue
            except:
                continue

            try:
                if qualifiers[KEY_PREDECESSOR]:
                    my_predecessor = qualifiers[KEY_PREDECESSOR][0].getTarget()
                    my_predecessor_id = my_predecessor.id
                    print('- Successor: ' + my_predecessor_id)
            except:
                print(
                    '- No Successor found. (For ' + officeholder + ' as ' + POSITION + ' of ' + COMMON_PROP_VALUE + ')')

            try:
                if qualifiers[KEY_SUCCESSOR]:
                    my_successor = qualifiers[KEY_SUCCESSOR][0].getTarget()
                    my_successor_id = my_successor.id
                    print('- successor: ' + my_successor_id)
                    found_successor = True
            except:
                print(
                    '- No successor found. (For ' + officeholder + ' as ' + POSITION + ' of ' + COMMON_PROP_VALUE + ')')
                return False

            if found_successor:
                print('-- Successor is: ' + my_successor_id)
                return my_successor_id


def get_seriesnr(officeholder):
    print()
    print('>> CHECKING (SERIESNR): https://www.wikidata.org/wiki/' + officeholder)
    item = pywikibot.ItemPage(repo, officeholder)
    try:
        mywd = item.get()
    except:
        print('-- Redirection found.')
        mywd = item.get(get_redirect=True)

    claim_list_pos = mywd['claims']['P39']

    for pos_item in claim_list_pos:
        found_successor = False
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
                        print('- NO Qualifier-Match[' + my_propval.id + ']')
                        continue
            except:
                continue

            try:
                if qualifiers[KEY_SERIESNR]:
                    my_seriesnr = qualifiers[KEY_SERIESNR][0].getTarget()
                    print('-- SeriesNr: ' + my_seriesnr)
                    found_successor = True
            except:
                print(
                    '- No SeriesNr found. (For ' + officeholder + ' as ' + POSITION + ' of ' + COMMON_PROP_VALUE + ')')
                return False

            if found_successor:
                print('-- Found SeriesNr is: ' + my_seriesnr)
                return int(my_seriesnr)


# ---

def set_seriesnr(officeholder, office, pkey, pvalue, seriesnr):
    print('--- Setting ' + officeholder + ' to nr ' + str(seriesnr) + ' of series.')
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
            if qualifiers[KEY_SERIESNR]:
                print('!! There is already a seriesnr. I skip that one.')
                continue
        except:
            q_seriesnr = pywikibot.Claim(repo, KEY_SERIESNR, is_qualifier=True)
            q_seriesnr.setTarget(str(seriesnr))
            pos_item.addQualifier(q_seriesnr, summary=u'added seriesnr of position')


# ---

# START THAT LOOP:


CURRENT_SUCCESSOR = INITIAL_OFFICEHOLDER

chain_running = True
CURRENT_SUCCESSOR = get_successor(INITIAL_OFFICEHOLDER)
CURRENT_SERIESNR = get_seriesnr(INITIAL_OFFICEHOLDER)

if not CURRENT_SUCCESSOR and POSITION == 'Q48629921':
    print('-- Trying to downgrade from Archbishop-Chain to Diocesanbishop-Chain')
    POSITION = 'Q1144278'
    CURRENT_SUCCESSOR = get_successor(INITIAL_OFFICEHOLDER)

if not CURRENT_SUCCESSOR or not CURRENT_SERIESNR:
    chain_running = False
else:
    print([CURRENT_SUCCESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, INITIAL_OFFICEHOLDER])
    CURRENT_SERIESNR = int(CURRENT_SERIESNR) + 1
    set_seriesnr(CURRENT_SUCCESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, int(CURRENT_SERIESNR))
    set_predecessor(CURRENT_SUCCESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, INITIAL_OFFICEHOLDER)

while chain_running:
    old_succesor = CURRENT_SUCCESSOR
    CURRENT_SUCCESSOR = get_successor(CURRENT_SUCCESSOR)

    if not CURRENT_SUCCESSOR and POSITION == 'Q48629921':
        print('-- Trying to downgrade from Archbishop to Diocesanbishop')
        POSITION = 'Q1144278'
        CURRENT_SUCCESSOR = get_successor(old_succesor)

    if not CURRENT_SUCCESSOR:
        print('No Successor: Chain stopped')
        chain_running = False
    elif get_seriesnr(CURRENT_SUCCESSOR) and get_seriesnr(CURRENT_SUCCESSOR) != int(CURRENT_SERIESNR + 1):
        print('Enumeration of series not consistant (' + str(get_seriesnr(CURRENT_SUCCESSOR)) + ' != ' + str(
            CURRENT_SERIESNR + 1) + '): Chain stopped')
        print()
        chain_running = False
    else:
        CURRENT_SERIESNR = int(CURRENT_SERIESNR) + 1
        set_seriesnr(CURRENT_SUCCESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, int(CURRENT_SERIESNR))
        set_predecessor(CURRENT_SUCCESSOR, POSITION, COMMON_PROP_KEY, COMMON_PROP_VALUE, old_succesor)

print('Done')
