#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import os
import re
import locale

import sys
import getopt

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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


wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()

a_downgradelist = ['Q48629921', 'Q1144278', 'Q15253909', 'Q1993358', 'Q65924966']

automode = False
singleautomode = False
diocese = False
dioid = False
position = False
officeholder = False
officeholder_wd = False
officeholder_ch = False


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
                    continue
        except:
            continue

        try:
            if qualifiers['P1365']:
                print('!! There is already a predecessor. I skip that one.')
                continue
        except:
            print('--- Saving on WD.')
            q_prede = pywikibot.Claim(repo, 'P1365', is_qualifier=True)
            prede_claim = pywikibot.ItemPage(repo, predecessor)
            q_prede.setTarget(prede_claim)
            pos_item.addQualifier(q_prede, summary=u'added predecessor')
            return True

    return False


def get_predecessor(item, position, diocese, dioid):
    print('----- Item:     ' + item)
    print('----- Position: ' + position)
    print('----- Diocese:  ' + str(diocese))
    print('----- Diocese-Id:  ' + dioid)
    target_page = pywikibot.ItemPage(repo, item)
    itemdetails = target_page.get(get_redirect=True)
    list_positions = itemdetails['claims']['P39']

    for single_position in list_positions:
        my_pos_data = single_position.getTarget()
        pos_id = my_pos_data.id
        # print('------ PosID: ' + pos_id)

        if not pos_id == position:
            # print('----- not interested in position: ' + pos_id + ' (searching for ' + position + ')')
            continue

        a_qualis = single_position.qualifiers

        if 'P708' not in a_qualis:
            continue

        if 'P708' in a_qualis:
            if not a_qualis['P708'][0].getTarget().id == diocese:
                continue

        if 'P1365' in a_qualis:
            return a_qualis['P1365'][0].getTarget().id

    if position in a_downgradelist and a_downgradelist.index(position) < len(a_downgradelist) - 1:
        new_position = a_downgradelist[a_downgradelist.index(position) + 1]
        print('-- Trying to downgrade position ' + position + ' to ' + new_position)
        get_predecessor(item, new_position, diocese, dioid)

    return False


def main(argv):
    opts, args = getopt.getopt(argv, "hd:i:o:p:a:s:", ["diocese=", 'id=', 'officeholder=', 'position=', 'auto=', 'single='])
    ret = {}
    for opt, arg in opts:
        if opt == '-h':
            print('check_bishopstart_on_chorg.py -d <diocese> -i <id> -o <officeholder> -p <position> -a <auto> -s <singleautomode>')
            sys.exit()
        elif opt in ("-d", "--diocese"):
            diocese = arg
            if diocese.isnumeric():
                diocese = 'Q' + diocese
            ret['diocese'] = diocese
        elif opt in ("-i", "--id"):
            dioid = arg
            ret['dioid'] = dioid
        elif opt in ("-o", "--officeholder"):
            officeholder = arg
            ret['officeholder'] = arg
        elif opt in ("-p", "--position"):
            position = arg
            ret['position'] = arg
        elif opt in ("-a", "--auto"):
            ret['auto'] = arg
        elif opt in ("-s", "--single"):
            ret['single'] = arg
    return ret


if __name__ == "__main__":
    mainret = main(sys.argv[1:])
    if 'diocese' in mainret:
        diocese = mainret['diocese']
    if 'dioid' in mainret:
        dioid = mainret['dioid']
    if 'officeholder' in mainret:
        officeholder = mainret['officeholder']
    if 'position' in mainret:
        position = mainret['position']
    if 'auto' in mainret:
        automode = mainret['auto']
        if automode != 0 and automode != 'no' and automode != 'false' and automode != 'n':
            automode = True
        else:
            automode = False
    if 'single' in mainret:
        singleautomode = mainret['single']
        if singleautomode != 0 and singleautomode != 'no' and singleautomode != 'false' and singleautomode != 'n':
            singleautomode = True
        else:
            singleautomode = False


print()
print('---------------------------------------------------------------------------------')
print('- Automode: ' + str(automode))

if (diocese == False and dioid == False) or officeholder == False or position == False:
    print('!! NO DIOCESE/OFFICEHOLDER/POSITION GIVEN. I quit.')

itemdetails = False
target_page = False

if diocese:
    target_page = pywikibot.ItemPage(repo, diocese)
    itemdetails = target_page.get(get_redirect=True)
    list_currentdioids = itemdetails['claims']['P1866']
    dioid_found = False
    if len(list_currentdioids) == 1:
        diocese = target_page.id
        print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
        dioid = list_currentdioids[0].getTarget()

    elif len(list_currentdioids) > 1:
        diocese = target_page.id
        print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
        for listitem_currentdioids in list_currentdioids:
            candidate = listitem_currentdioids.getTarget()
            print('---------- candidate: ' + candidate + ' vs. dioid: ' + dioid)
            if candidate != dioid:
                continue
            else:
                dioid_found = True
                dioid = candidate
                break
    if len(list_currentdioids) != 1 and (dioid_found == False or dioid == False):
        print('! Length of P1866 (Claim for Catholic Hierarchy diocese ID) == ' + str(len(list_currentdioids)))
        exit()
elif not diocese and dioid:
    SPARQL = "SELECT ?item WHERE { ?item p:P1866 ?statement. ?statement ps:P1866 ?dioid. FILTER(?dioid = \"" + dioid + "\")}"
    my_generator = pg.WikidataSPARQLPageGenerator(SPARQL, site=wikidata_site)
    my_generator = list(my_generator)
    if len(my_generator) != 1 and dioid == False:
        print('!!!- Found ' + str(len(my_generator)) + ' Results for DioId="' + dioid + '" that works only with an exact match.')
        exit()
    else:
        target_page = my_generator[0]
        itemdetails = target_page.get(get_redirect=True)
        dioid_found = False
        list_currentdioids = itemdetails['claims']['P1866']
        if len(list_currentdioids) == 1:
            diocese = target_page.id
            print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
            dioid = list_currentdioids[0].getTarget()

        elif len(list_currentdioids) > 1:
            diocese = target_page.id
            print('-- Diocese found: https://www.wikidata.org/wiki/{}'.format(diocese))
            for listitem_currentdioids in list_currentdioids:
                candidate = listitem_currentdioids.getTarget()
                if candidate != dioid:
                    continue
                else:
                    dioid_found = True
                    dioid = candidate
                    break
        if len(list_currentdioids) != 1 and (dioid_found == False or diocese == False):
            print('! Length of P1866 (Claim for Catholic Hierarchy diocese ID) == ' + str(len(list_currentdioids)))
            exit()


chorgurl = 'http://www.catholic-hierarchy.org/diocese/d' + dioid + '.html'


_rex_wd = re.compile("^Q[0-9]+")
_rex_ch = re.compile("^[a-z]{2,8}$")

if _rex_wd.fullmatch(officeholder):
    print('-- WikiData-Id 4 Officeholder: https://www.wikidata.org/wiki/' + officeholder)
    target_page = pywikibot.ItemPage(repo, officeholder)
    itemdetails = target_page.get(get_redirect=True)
    list_currentchid = itemdetails['claims']['P1047']

    if len(list_currentchid) >= 1:
        officeholder_wd = target_page.id
        print('-- Diocese match: https://www.wikidata.org/wiki/{}'.format(diocese))
        officeholder_ch = list_currentchid[0].getTarget()
    else:
        print('! Length of P1047 (Claim for Catholic Hierarchy diocese ID) !=1')
        exit()

elif _rex_ch.fullmatch(officeholder):
    print('-- CH-Id 4 Officeholder: ' + officeholder)
    officeholder_ch = officeholder

    SPARQL = "SELECT ?item WHERE { ?item wdt:P1047 \"" + officeholder + "\". }"
    my_generator = pg.WikidataSPARQLPageGenerator(SPARQL, site=wikidata_site)
    my_generator = list(my_generator)
    if len(my_generator) != 1:
        print('!!!- Found ' + str(len(my_generator)) + ' Results for Ch-Id="' + officeholder + '" that works only with an exact match.')
        if len(my_generator) == 0:
            os.system('echo "' + officeholder + '" >> data/not-yet-known.txt')
            os.system('sort -u data/not-yet-known.txt -o data/not-yet-known.txt')
        exit()
    else:
        target_page = my_generator[0]
        itemdetails = target_page.get(get_redirect=True)
        officeholder_wd = target_page.id
        print('-- WD-Id found: https://www.wikidata.org/wiki/' + officeholder_wd)

else:
    print('!! - No valid Officeholder found. I quit.')
    exit()

if not _rex_wd.fullmatch(position):
    print('!! - No valid position given. I quit.')
    exit()

predecessor = get_predecessor(officeholder_wd, position, diocese, dioid)
if predecessor:
    print('>> predecessor https://www.wikidata.org/wiki/' + predecessor + ' already known. i go on to that item in chain.')
    os.system('python3 set_predecessor.py -i ' + dioid + ' -o ' + predecessor + ' -p ' + position + ' -a ' + str(automode))
    exit()

try:
    r = requests_retry_session().get(chorgurl)
except:
    print('!!! Could not request url:' + chorgurl)
    exit()

if r.status_code != 200:
    print('### ERROR ON http-call for : ' + chorgurl)
if r.status_code == 200:
    print('-- Catholic-Hierarchy-URL of Dio: ' + chorgurl)


bytes_regex = str.encode('<h2 align=center><a name="former">Past and Present Ordinaries<\/a><\/h2>\n(<ul[\s\S]*<\/ul>)')
list_ordinaries = re.findall(bytes_regex, r.content)

if list_ordinaries:
    print('--- Ordinaries-Table found.')
else:
    print('!!- Ordinaries-Table not found. 2nd attempt...')
    bytes_regex = str.encode('<h2 align=center><a name="former">Past Ordinaries<\/a><\/h2>\n(<ul[\s\S]*<\/ul>)')
    list_ordinaries = re.findall(bytes_regex, r.content)
    if list_ordinaries:
        print('--- Ordinaries-Table found.')
    else:
        print('!!- Ordinaries-Table not found. 2nd attempt failed.')
        exit()

if not itemdetails:
    print('!!- Could not load WD-Item')
    exit()

bytes_regex = str.encode('<li[^\>]*><a href="\/bishop\/b([a-z]{2,8})\.html"')
list_ordinaries_entries = re.findall(bytes_regex, list_ordinaries[0])

# print(list_ordinaries_entries)

if officeholder_ch.encode('utf-8') in list_ordinaries_entries:
    print('- found myself (' + officeholder_ch + ') on list with ' + str(len(list_ordinaries_entries)) + ' entries.')
    my_listpos = list_ordinaries_entries.index(officeholder_ch.encode('utf-8'))
    print('- position:' + str(my_listpos))
    if my_listpos == 0:
        print('- i am the first, known on ch. i quit.')
        exit()
    else:
        print('-- my predecessor is: ' + list_ordinaries_entries[my_listpos - 1].decode('utf-8'))
        SPARQL = "SELECT ?item WHERE { ?item wdt:P1047 \"" + list_ordinaries_entries[my_listpos - 1].decode('utf-8') + "\". }"
        my_generator = pg.WikidataSPARQLPageGenerator(SPARQL, site=wikidata_site)
        my_generator = list(my_generator)
        if len(my_generator) != 1:
            print('!!!- Found ' + str(len(my_generator)) + ' Results for CH-Id="' + list_ordinaries_entries[my_listpos - 1].decode('utf-8') + '" that works only with an exact match.')
            if len(my_generator) == 0:
                os.system('echo "' + list_ordinaries_entries[my_listpos - 1].decode('utf-8') + '" >> data/not-yet-known.txt')
                os.system('sort -u data/not-yet-known.txt -o data/not-yet-known.txt')
            exit()
        else:
            target_page = my_generator[0]
            itemdetails = target_page.get(get_redirect=True)
            predecessor_id = target_page.id
            print('-- predecessor found: https://www.wikidata.org/wiki/{}'.format(predecessor_id))

            answer = None
            while answer not in ("yes", "no"):
                if automode or singleautomode:
                    answer = "yes"
                else:
                    answer = input(">>> MAY I SET THIS ONE ON WikiData? (y/n)")
                if answer == "no" or answer == 'n' or answer == 'N':
                    print('-- Okay. Then I quit.')
                    exit()
                elif answer == "yes" or answer == 'y' or answer == 'Y':
                    print('-- Okay. I will set that.')
                    result = set_predecessor(officeholder, position, 'P708', diocese, predecessor_id)
                    if result:
                        if automode:
                            if dioid:
                                os.system('python3 set_predecessor.py -d ' + diocese + ' -i ' + dioid + ' -o ' + officeholder + ' -p ' + position + ' -a ' + str(automode))
                            else:
                                os.system('python3 set_predecessor.py -d ' + diocese + ' -o ' + officeholder + ' -p ' + position + ' -a ' + str(automode))
                        exit()
                    else:
                        print('-- Error on setting predecessorship.')
                        exit()
                else:
                    print("Please enter yes or no.")
