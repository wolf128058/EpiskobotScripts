#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

import re
import random
from random import shuffle

from datetime import datetime

import progressbar

import pywikibot
from pywikibot import pagegenerators as pg

QUERY = """
SELECT ?item ?date WHERE {
  ?item (p:P569/psv:P569) ?datevalue.
  ?datevalue wikibase:timeValue ?date.
  FILTER(EXISTS { ?item wdt:P1047 ?statement. })
  FILTER(?date < "+1582-10-15T00:00:00Z"^^xsd:dateTime)
  ?datevalue wikibase:timePrecision ?dateprecision.
  FILTER(?dateprecision >= 9 )
  ?datevalue wikibase:timeCalendarModel wd:Q1985727.
}
ORDER BY (?date)
LIMIT 25
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')
shuffle(generator)

my_succ_dio_id = False

with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        print('')
        bar.update(index + 1)
        itemdetails = item.get(get_redirect=True)
        itemdetails_id = item.id
        mycathid = ''
        changed = False

        print('>> CHECKING: Wikidata-Item: https://www.wikidata.org/wiki/' + itemdetails_id)
        try:
            claim_list_cathid = itemdetails['claims']['P1047']
        except:
            print('-- No Catholic-Hierarchy-Id found. I skip that one')
            continue
        mycathid = claim_list_cathid[0].getTarget()
        if not mycathid:
            print('-- No Catholic-Hierarchy-Id found. I skip that one')
            continue

        try:
            claim_list_born = itemdetails['claims']['P569']
        except:
            print('-- No Birth-Date found. I skip that one')
            continue

        claim_birthdate = pywikibot.Claim(repo, 'P569')

        for single_date in claim_list_born:
            trgt_date = single_date.getTarget()
            to_json = single_date.toJSON()
            try:
                if 'calendarmodel' in to_json['mainsnak']['datavalue']['value'] and \
                        to_json['mainsnak']['datavalue']['value'][
                            'calendarmodel'] != 'http://www.wikidata.org/entity/Q1985786':
                    print('Found incorrect non-julian calendar for : ' + to_json['mainsnak']['datavalue']['value']['time'])
                    try:
                        time_in_datetime = datetime.strptime(to_json['mainsnak']['datavalue']['value']['time'],
                                                             "+0000000%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        try:
                            time_in_datetime = datetime.strptime(to_json['mainsnak']['datavalue']['value']['time'],
                                                                 "+0000000%Y-%m-00T%H:%M:%SZ")
                        except ValueError:
                            time_in_datetime = datetime.strptime(to_json['mainsnak']['datavalue']['value']['time'],
                                                                 "+0000000%Y-00-00T%H:%M:%SZ")

                    my_date4wd = pywikibot.WbTime(
                        year=time_in_datetime.year,
                        month=time_in_datetime.month,
                        day=time_in_datetime.day,
                        hour=time_in_datetime.hour,
                        minute=time_in_datetime.minute,
                        second=time_in_datetime.second,
                        precision=to_json['mainsnak']['datavalue']['value']['precision'],
                        before=to_json['mainsnak']['datavalue']['value']['before'],
                        after=to_json['mainsnak']['datavalue']['value']['after'],
                        timezone=to_json['mainsnak']['datavalue']['value']['timezone'],
                        calendarmodel='http://www.wikidata.org/entity/Q1985786')

                    sources = single_date.getSources()
                    if sources and 2 == 4:
                        print('-- skipping because there are sources')
                        continue
                    else:
                        single_date.changeTarget(my_date4wd, summary=u'switched calendarmodel to julian')
                        qualifiers = single_date.qualifiers
                        if qualifiers and 'P31' in qualifiers:
                            for is_a in qualifiers['P31']:
                                is_a_target = is_a.getTarget()
                                print(is_a_target)
                                if is_a_target.id == 'Q26961029':
                                    single_date.removeQualifier(is_a, summary=u'removed obsolete gregorian tag')
            except KeyError:
                continue

print('Done!')
