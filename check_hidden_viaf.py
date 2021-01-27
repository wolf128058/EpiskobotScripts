#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name


import os
import re
from random import shuffle

import progressbar

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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


path4todo = 'data/todo_check4viaf.txt'
path4result = 'data/todo_newviafs.txt'
wikidata_site = pywikibot.Site('wikidata', 'wikidata')

if not (os.path.exists(path4todo) and os.path.getsize(path4todo) > 0):
    x = open('data/known-to-wikidata.txt').readlines()
    shuffle(x)
    with open(path4todo, 'wb') as fp:
        for item in x:
            fp.write("{}".format(item).encode())


lines = len(open(path4todo).readlines())

with progressbar.ProgressBar(max_value=lines, redirect_stdout=True) as bar:
    done_lines = 0
    while done_lines < lines:
        done_lines = lines - len(open(path4todo).readlines())
        bar.update(done_lines)
        with open(path4todo, 'r') as fin:
            data = fin.read().splitlines(True)
            mycathid = data[0].strip()
            chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
            print('>>> CHECKING: ' + mycathid)
            print('- url: ' + chorgurl)
            r = requests_retry_session().get(chorgurl)
            if r.status_code != 200:
                print('### HTTP-ERROR ON cath-id: ' + chorgurl)
                with open(path4todo, 'w') as fout:
                    fout.writelines(data[1:])
                continue

            viaf_match = re.findall(b'\(<a href="https:\/\/viaf.org\/viaf\/([0-9]+)">VIAF: ([0-9]+)<\/a>\)', r.content)
            if viaf_match:
                print('-- VIAF found on CH.')
                query = 'SELECT ?item WHERE { ?item wdt:P1047 "' + mycathid + '". } LIMIT 1'
                generator = pg.WikidataSPARQLPageGenerator(query, site=wikidata_site)
                generator = list(generator)
                wd_viafsubject_page = generator[0].get(get_redirect=True)
                wd_viafsubject_page_id = generator[0].id

                viaf_claims = False
                try:
                    viaf_claims = wd_viafsubject_page['claims']['P214']
                except KeyError:
                    print('- Viaf not yet set. Good one.')

                if viaf_claims:
                    print('-- Wikidata already has a viaf-claim for that one. I skip that one.')

                else:
                    viaf = False
                    try:
                        if isinstance(viaf_match[0].decode('utf-8'), str) and isinstance(viaf_match[1].decode('utf-8'), str) and viaf_match[0].decode('utf-8') == viaf_match[1].decode('utf-8'):
                            viaf = str(viaf_match[0].decode('utf-8'))
                    except AttributeError:
                        pass

                    if not viaf and isinstance(viaf_match[0], str) and isinstance(viaf_match[1], str) and viaf_match[0] == viaf_match[1]:
                        viaf = str(viaf_match[0])

                    if not viaf:
                        print('! - No viaf-Number found. I skip that one.')
                    else:
                        qs_line = wd_viafsubject_page_id + '\tP214\t"' + viaf + '"\tS1047\t"' + mycathid + "\"\n"
                        print(qs_line)
                        fq = open(path4result, "a")
                        fq.write(qs_line + "\n")
                        qs_line = ''
                        fq.close()

        with open(path4todo, 'w') as fout:
            fout.writelines(data[1:])
