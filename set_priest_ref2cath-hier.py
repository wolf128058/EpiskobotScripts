#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import argparse
import datetime
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

QUERY = ''


def main():
    parser = argparse.ArgumentParser(
        description='Set reference to catholic hierarchy for a priest-job')
    parser.add_argument('-s', '--select', default='empty', help=r'select entries with empty/wp/all references')
    args = parser.parse_args()

    global QUERY
    global SELECT
    SELECT = args.select

    if args.select == 'empty':
        QUERY = '''
        SELECT ?item ?cathid WHERE {
        ?item wdt:P106 wd:Q250867;
            wdt:P1047 ?cathid.
        FILTER(NOT EXISTS {
            ?item p:P106 _:b80.
            _:b80 ps:P106 ?relsub2;
            prov:wasDerivedFrom _:b30.
        })}'''
    else:
        QUERY = '''
        SELECT ?item ?cathid WHERE (
        ?item wdt:P106 wd:Q250867;
            wdt:P1047 ?cathid.
        )'''

    wikidata_site = pywikibot.Site('wikidata', 'wikidata')

    generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
    generator = list(generator)
    shuffle(generator)

    repo = wikidata_site.data_repository()

    with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
        bar.update(0)
        for index, item in enumerate(generator):

            now = datetime.datetime.utcnow()
            my_date4wd = pywikibot.WbTime(
                year=now.year,
                month=now.month,
                day=now.day,
                precision=11,
                calendarmodel='http://www.wikidata.org/entity/Q1985727')

            itemdetails = item.get(get_redirect=True)
            mycathid = ''
            mywd_id = item.id
            print("\n" + '>> Checking WD-ID: ' + mywd_id)
            print('-- WD-URL: https://www.wikidata.org/wiki/' + mywd_id)

            claim_list_jobs = itemdetails['claims']['P106']
            claim_list_cathid = itemdetails['claims']['P1047']

            for cathids in claim_list_cathid:
                mycathid = cathids.getTarget()
                chorgurl = 'http://www.catholic-hierarchy.org/bishop/b' + mycathid + '.html'
                print('-- Catholic-Hierarchy-Id: ' + mycathid)
                print('-- URL: ' + chorgurl)

            for job_claim in claim_list_jobs:
                yet_set_complete = False
                trgt = job_claim.getTarget()
                print('-- Claim for {} found.'.format(trgt.id))
                if trgt.id == 'Q250867':
                    job_claim_sources = job_claim.getSources()
                    if len(job_claim_sources) == 0:
                        r = requests_retry_session().get(chorgurl)
                        priest_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Ordained Priest</td>.*</tr>", r.content)

                        if r.status_code == 200 and len(priest_tr) > 0:
                            print('-- Status 200 received for: ' + chorgurl)
                            source_claim_statedin = pywikibot.Claim(repo, 'P248')
                            source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                            source_claim_catid = pywikibot.Claim(repo, 'P1047')
                            source_claim_catid.setTarget(mycathid)
                            source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                            source_claim_retrieved.setTarget(my_date4wd)
                            job_claim.addSources([source_claim_statedin, source_claim_catid, source_claim_retrieved],
                                                 summary='add catholic-hierarchy as source for beeing catholic priest')
                            cath_id_src = True

                    else:
                        cath_id_src = False
                        wp_found = 0
                        count_src = 0
                        for job_claim_source in job_claim_sources:
                            count_src += 1
                            print('-- Found claim for beeing catholic priest')
                            if 'P1047' in job_claim_source:
                                if 'P248' in job_claim_source:
                                    print(job_claim_sources)
                                    yet_set_complete = True
                                    continue

                                cath_id_src = True
                                print('--- Cath-Id-Src found')
                                if SELECT == 'all':
                                    try:
                                        claimTarget = job_claim_source['P1047']
                                        job_claim.removeSources([claimTarget[0]],
                                                        summary='remove source (will be replaced immediately, if still valid)')
                                        cath_id_src = False
                                    except:
                                        print('!! - Error on source-claim removal')
                            else:
                                print('--- Other than Cath-Id-Src found:')
                                print(job_claim_source)
                                if 'P143' in job_claim_source:
                                    wp_found += 1
                                    print('--- Wikipedia-Source found')

                        if not cath_id_src and not yet_set_complete and (SELECT == 'all' or (SELECT == 'wp' and count_src == wp_found)):
                            r = requests_retry_session().get(chorgurl)
                            priest_tr = re.findall(b"<tr><td[^>]+>(.*)</td><td>.*</td><td>Ordained Priest</td>.*</tr>", r.content)
                                
                            if len(priest_tr) == 0:
                                print('-- Not proven on catholic-hierarchy.org')

                            if r.status_code == 200 and len(priest_tr) > 0:
                                print('-- Status 200 received for: ' + chorgurl)
                                source_claim_statedin = pywikibot.Claim(repo, 'P248')
                                source_claim_statedin.setTarget(pywikibot.ItemPage(repo, 'Q3892772'))
                                source_claim_catid = pywikibot.Claim(repo, 'P1047')
                                source_claim_catid.setTarget(mycathid)
                                source_claim_retrieved = pywikibot.Claim(repo, 'P813')
                                source_claim_retrieved.setTarget(my_date4wd)
                                job_claim.addSources(
                                    [source_claim_statedin, source_claim_catid, source_claim_retrieved],
                                    summary='add catholic-hierarchy as source for beeing catholic priest')
            bar.update(index)
    print('Done!')


if __name__ == '__main__':
    main()
