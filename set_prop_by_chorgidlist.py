#!/usr/bin/python3
# -*- coding: utf-8 -*-

import random

import sys
import progressbar


import pywikibot
from pywikibot import pagegenerators as pg


print('>>> Property-Setter by CH.org-ID-List')

if sys.argv:
    try:
        myinputfile = sys.argv[1]
    except:
        print('- No input file for cat-ids given. I quit.')
        exit()

try:
    todo_file = open(myinputfile, "r")
    todo_lines = todo_file.readlines()
    todo_file.close()
    todo_lines = list(dict.fromkeys(todo_lines))
    print('- Starting with a ToDoList having {} entries.'.format(len(todo_lines)))
except:
    print('- Error on opening input-file "' + myinputfile + '". I quit.')
    exit()

if len(sys.argv) > 1:
    try:
        my_order = sys.argv[2]
        print('- I received the order to set "' + my_order + '"')
    except:
        print('- No Order. I quit.')
        exit()

wikidata_site = pywikibot.Site('wikidata', 'wikidata')

random.shuffle(todo_lines)
order_list = []

with progressbar.ProgressBar(max_value=len(todo_lines), redirect_stdout=True) as bar:
    for index, todo_line in enumerate(todo_lines):
        bar.update(index)
        todo_line = todo_line.strip()

        print("\n" + '-- CatId:' + todo_line)
        TODO_QUERY = 'SELECT ?item WHERE { ?item wdt:P1047 "' + todo_line + '". }'

        try:
            generator = pg.WikidataSPARQLPageGenerator(TODO_QUERY, site=wikidata_site)
        except:
            print('!!! query failed. i skip.')
            continue

        for item in generator:
            mywd = item.get(get_redirect=True)
            my_prop = my_order.split()[0].strip()
            my_claim = my_order.split()[1].strip()
            if len(my_order.split()) > 2:
                for x in range(2, len(my_order.split())):
                    my_claim = my_claim + "\t" + my_order.split()[x].strip()

            print('--- WD-Item found: ' + item.id)
            print('--- WD-Item URL: https://www.wikidata.org/wiki/' + item.id)
            print('--- Order: ' + my_order)
            print('--- Order-Len: {}' . format(len(my_order.split())))
            print('--- Prop: ' + my_prop)
            print('--- Claim: ' + my_claim)

            try:
                claim_list = mywd['claims'][my_prop]
                claim_isset = False

                for claim_item in claim_list:
                    claim_item_data = claim_item.getTarget()
                    if claim_item_data.id == my_claim:
                        print('-- Desired Claim is already set. I skip that one.')
                        claim_isset = True

                if(claim_isset == False):
                    print('-- No claim ' + my_prop + ' found on ' + item.id + ' will set the desired one.')
                    new_orderlist_item = item.id + "\t" + my_prop + "\t" + my_claim
                    order_list.append(new_orderlist_item)
                    # reciproke participation
                    if my_prop == 'P1344':
                        order_list.append(my_claim + '\tP710\t' + item.id)

            except:
                print('-- No claim ' + my_prop + ' found at all on ' + item.id + ' will set the desired one.')
                new_orderlist_item = item.id + "\t" + my_prop + "\t" + my_claim
                order_list.append(new_orderlist_item)
                # reciproke participation
                if my_prop == 'P1344':
                    order_list.append(my_claim + '\tP710\t' + item.id)
###

with open('property_result.txt', 'w') as f:
    for order_list_item in order_list:
        f.write("%s\n" % order_list_item)
print(('Done!' + "\n"))
