#!/usr/bin/python3
# -*- coding: utf-8 -*-

import random

import re
import lxml.html
import progressbar
import requests
import os

import pywikibot
from pywikibot import pagegenerators as pg


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()

path4qs = 'log_quick_consefounds.txt'
path4todo = 'todo-consecheck.txt'

if(os.path.isfile(path4todo) == False):
    print('-!- ToDo-File not found!')
    QUERY_TODO = 'SELECT ?item ?chid WHERE { ?item wdt:P1047 ?chid. }'
    generator_todo = pg.WikidataSPARQLPageGenerator(QUERY_TODO, site=wikidata_site)
    generator_todo = list(generator_todo)
    l_todo = []

    with progressbar.ProgressBar(max_value=len(generator_todo)) as unknown_bar:
        for index, todo_item in enumerate(generator_todo):
            todo_wd = todo_item.get(get_redirect=True)
            todo_chid = todo_wd['claims']['P1047']
            l_todo.append(todo_chid[0].getTarget())
            unknown_bar.update(index)

    print('--- Found {} entries with catholic-hierarchy.org reference on WD.'.format(len(l_todo)))
    with open(path4todo, 'w') as f:
        with progressbar.ProgressBar(max_value=len(l_todo)) as bar:
            for index, item in enumerate(l_todo):
                f.write("%s\n" % item)
                bar.update(index)

    print('--- Wrote this list to ' + path4todo)


todo_file = open(path4todo, "r")
todo_lines = todo_file.readlines()
todo_file.close()
todo_lines = list(dict.fromkeys(todo_lines))
print('>>> Starting with a ToDoList having {} entries.'.format(len(todo_lines)))

random_cnr = random.randint(0, len(todo_lines) - 1)
candidate = todo_lines[random_cnr].strip()
print('-- Candidate chorig: ' + candidate)

chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + candidate + '.html'
print('-- Candidate URL on CH.org: ' + chorgurl)

SUBQUERY_MYSELF = 'SELECT ?item ?conse ?consecatid WHERE {  ?item wdt:P1047 "' + candidate + '". OPTIONAL { ?item wdt:P1598 ?conse. } OPTIONAL { ?conse wdt:P1047 ?consecatid. }}'
subgenerator_myself = pg.WikidataSPARQLPageGenerator(SUBQUERY_MYSELF, site=wikidata_site)

known_consids_wd = []
known_pconsids_wd = []
known_cconsids_wd = []

known_fail_pconsids_wd = []
known_fail_cconsids_wd = []

known_consids_chorg = []
claim_list_conse_len = 0

for item in subgenerator_myself:
    mywd = item.get(get_redirect=True)
    mywd_id = item.id
    claim_list_conse = {}
    print('-- Candidate URL on WD.org: https://www.wikidata.org/wiki/' + mywd_id)

    try:
        claim_list_conse = mywd['claims']['P1598']
    except:
        print('-- No Conse-Data on WD')

    for claim_list_conse_item in claim_list_conse:
        claim_list_conse_len += 1
        my_ci_data = claim_list_conse_item.getTarget()
        known_consids_wd.append(my_ci_data.id)
        qualifiers = claim_list_conse_item.qualifiers

        for qualifier in qualifiers:
            print('--- Qualifier for ' + my_ci_data.id + ' found: ' + qualifier)

            if (qualifier == 'P3831'):
                my_ci_function = claim_list_conse_item.qualifiers['P3831'][0].getTarget()
                print('-- Function@P3831:' + my_ci_function.id)
                if my_ci_function.id == 'Q18442817':
                    known_pconsids_wd.append(my_ci_data.id)
                    print('-- added correct p-conse ' + my_ci_data.id)
                elif my_ci_function.id == 'Q18442822':
                    known_cconsids_wd.append(my_ci_data.id)
                    print('-- added correct c-conse ' + my_ci_data.id)

            elif (qualifier == 'P2868'):
                myqual = claim_list_conse_item.qualifiers['P2868'][0]
                my_ci_function = myqual.getTarget()
                print('-- Function@P2868:' + my_ci_function.id)
                if my_ci_function.id == 'Q18442817':
                    known_fail_pconsids_wd.append(my_ci_data.id)
                    q_as = pywikibot.Claim(repo, 'P3831', is_qualifier=True)
                    principal_claim = pywikibot.ItemPage(repo, 'Q18442817')
                    q_as.setTarget(principal_claim)
                    claim_list_conse_item.removeQualifiers([myqual], summary='removed the principal-consecrator via P2868')
                    claim_list_conse_item.addQualifier(q_as, summary='replaced the principal-consecrator by role P3831(!)')

                    print('-- added incorrect p-conse ' + my_ci_data.id)
                elif my_ci_function.id == 'Q18442822':
                    known_fail_cconsids_wd.append(my_ci_data.id)
                    q_as = pywikibot.Claim(repo, 'P3831', is_qualifier=True)
                    principal_claim = pywikibot.ItemPage(repo, 'Q18442822')
                    q_as.setTarget(principal_claim)
                    claim_list_conse_item.removeQualifiers([myqual], summary='removed the co-consecrator via P2868')
                    claim_list_conse_item.addQualifier(q_as, summary='replaced the co-consecrator by role P3831(!)')

                    print('-- added incorrect c-conse ' + my_ci_data.id)


print('-- WD-Consecrator-Amount: {}.'.format(claim_list_conse_len))
print('-- WD-Princ-Consecrator-Amount: {}.'.format(len(known_pconsids_wd)))
print('-- WD-Co-Consecrator-Amount: {}.'.format(len(known_cconsids_wd)))
if len(known_fail_pconsids_wd) > 0:
    print('--! WD-Princ-Consecrator-Amount(Subject): {}.'.format(len(known_fail_pconsids_wd)))
if len(known_fail_cconsids_wd) > 0:
    print('--! WD-Co-Consecrator-Amount(Subject): {}.'.format(len(known_fail_cconsids_wd)))
print('-- Candidate URL on WD.org: https://www.wikidata.org/wiki/' + mywd_id)


r = requests.head(chorgurl)

if r.status_code != 200:
    print('### ERROR ON cath-id: ' + mycathid)
    exit

t = lxml.html.parse(chorgurl)
mylistitems = t.findall(".//li")

for listitem in mylistitems:
    if listitem.text == 'Principal Consecrator:':
        firstlink = listitem.find('.//a[@href]')
        firsthref = firstlink.attrib['href']
        conse_match = re.match('b([0-9a-z]+)\.html', firsthref)
        if conse_match:
            print('-- candidate\'s principal-conse: ' + conse_match.groups()[0])
            SUBQUERY_CONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + conse_match.groups()[
                0] + '". }'
            subgenerator_conse = pg.WikidataSPARQLPageGenerator(
                SUBQUERY_CONSE, site=wikidata_site)
            count_conse_found = 0
            for item in subgenerator_conse:
                count_conse_found += 1
                conse_setter_id = item.id
            if count_conse_found == 1:
                print('!!! Conse found: ' + conse_setter_id + ' => ' + mywd_id)

                if (conse_setter_id in known_consids_wd) or (conse_setter_id in known_fail_pconsids_wd) or (conse_setter_id in known_fail_cconsids_wd):
                    print('-- ' + conse_setter_id + ' is an already known pconse.')
                    if conse_setter_id not in known_pconsids_wd and conse_setter_id not in known_fail_pconsids_wd:
                        print('-- but has the not yet known function principal-conse.')
                        fq = open(path4qs, "a")
                        fq.write("\n" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442817")
                        fq.close()
                    elif (conse_setter_id in known_fail_pconsids_wd) or (conse_setter_id in known_fail_cconsids_wd):
                        print('-- wrongly set as subject, yet corrected...')

                else:
                    print('-- ' + conse_setter_id + ' is a not yet known conse.')
                    fq = open(path4qs, "a")
                    if conse_setter_id in known_fail_pconsids_wd:
                        fq.write("\n-" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP2868\tQ18442817")
                    fq.write("\n" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442817")
                    fq.close()

    elif listitem.text == 'Principal Co-Consecrators:':
        coconse_matches = []
        conselinks = listitem.findall('.//a[@href]')
        for conselink in conselinks:
            href = conselink.attrib['href']
            coconse_match = re.match('b([0-9a-z]+)\.html', href)
            try:
                coconse_match_gr = coconse_match.groups()[0]
                if (len(coconse_match_gr) > 0):
                    coconse_matches.append(coconse_match_gr)
            except:
                print('-- No matching co-conse-link')

        for coconse_match in coconse_matches:
            print('-- co-conse: ' + coconse_match)
            SUBQUERY_COCONSE = 'SELECT ?item WHERE { ?item wdt:P1047 "' + coconse_match + '". }'
            subgenerator_coconse = pg.WikidataSPARQLPageGenerator(
                SUBQUERY_COCONSE, site=wikidata_site)
            count_coconse_found = 0
            for item in subgenerator_coconse:
                count_coconse_found += 1
                conse_setter_id = item.id
                if count_coconse_found >= 1:
                    print('!!! Co-Conse found: ' + conse_setter_id + ' => ' + mywd_id)

                    if conse_setter_id in known_consids_wd:
                        print('-- ' + conse_setter_id + ' is an already known cconse.')
                        if conse_setter_id not in known_cconsids_wd and conse_setter_id not in known_fail_cconsids_wd:
                            print('-- but has the not yet known function co-conse.')
                            fq = open(path4qs, "a")
                            fq.write("\n" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442822")
                            fq.close()
                    elif (conse_setter_id in known_fail_cconsids_wd):
                        print('-- wrongly set as subject, yet corrected...')

                    else:
                        print('-- ' + conse_setter_id + ' is a not yet known conse.')
                        fq = open(path4qs, "a")
                        if conse_setter_id in known_fail_cconsids_wd:
                            fq.write("\n-" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP2868\tQ18442822")
                        fq.write("\n" + mywd_id + "\tP1598\t" + conse_setter_id + "\tP3831\tQ18442822")
                        fq.close()

del todo_lines[random_cnr]
todo_lines = list(dict.fromkeys(todo_lines))

with open(path4todo, 'w') as f:
    for todo_line in todo_lines:
        f.write("%s\n" % todo_line.strip())

print('Done!' + "\n")
