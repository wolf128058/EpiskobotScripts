#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime
import os
from random import shuffle

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import progressbar
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


path4todo = 'data/todo_check4humanref.txt'
wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()

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
#       now = datetime.datetime.now()
        now = datetime.datetime.utcnow()
        my_date4wd = pywikibot.WbTime(
            year=now.year,
            month=now.month,
            day=now.day,
            precision=11,
            calendarmodel='http://www.wikidata.org/entity/Q1985727')

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

            query = 'SELECT ?item WHERE { ?item wdt:P1047 "' + mycathid + '". } LIMIT 1'
            generator = pg.WikidataSPARQLPageGenerator(query, site=wikidata_site)
            generator = list(generator)
            wd_subject_page = generator[0].get(get_redirect=True)
            wd_subject_page_id = generator[0].id
            print('-- WD: https://www.wikidata.org/wiki/' + wd_subject_page_id)

            try:
                rel_claims = wd_subject_page['claims']['P31']
            except KeyError:
                print('- No Religion set. I skip that one.')
                continue

            for rel_claim in rel_claims:
                trgt = rel_claim.getTarget()
                if trgt.id == 'Q5':
                    rel_claim_sources = rel_claim.getSources()
                    if len(rel_claim_sources) == 0:
                        # add source
                        r = requests_retry_session().head(chorgurl)
                        if r.status_code == 200:
                            print('-- Status 200 received for: ' + chorgurl)
                            source_claim_statedin = pywikibot.Claim(repo, 'P248')
                            source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                            source_claim_catid = pywikibot.Claim(repo, 'P1047')
                            source_claim_catid.setTarget(mycathid)
                            source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                            source_claim_retrieved.setTarget(my_date4wd)
                            rel_claim.addSources([source_claim_statedin, source_claim_catid, source_claim_retrieved],
                                                 summary='add catholic-hierarchy as source for beeing human')
                    else:
                        for rel_claim_source in rel_claim_sources:
                            if 'P1047' not in rel_claim_source:
                                continue
                            claimTarget = rel_claim_source['P1047']
                            is_cath_id_src = True
                            print('--- Cath-Id-Src found')
                            # print(claimTarget[0])
                            if 'P813' in rel_claim_source and 'P248' in rel_claim_source:
                                continue
                            rel_claim.removeSources([claimTarget[0]],
                                                    summary='remove source (will be replaced immediately, if still valid)')
                            r = requests_retry_session().head(chorgurl)
                            if r.status_code == 200:
                                print('-- Status 200 received for: ' + chorgurl)
                                source_claim_statedin = pywikibot.Claim(repo, 'P248')
                                source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                                source_claim_catid = pywikibot.Claim(repo, 'P1047')
                                source_claim_catid.setTarget(mycathid)
                                source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                                source_claim_retrieved.setTarget(my_date4wd)
                                rel_claim.addSources(
                                    [source_claim_statedin, source_claim_catid, source_claim_retrieved],
                                    summary='extended catholic-hierarchy as source for beeing human')

        with open(path4todo, 'w') as fout:
            fout.writelines(data[1:])

print('Done!')
