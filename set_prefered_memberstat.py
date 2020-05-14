#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

from random import shuffle

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


diocese = False
position = False


QUERY = """
SELECT ?item WHERE {
  ?item wdt:P1866 ?statement;
    wdt:P2124 ?members.
  FILTER(?members > 0 )
}
GROUP BY ?item
"""

QUERY = """
SELECT ?item (COUNT(?item) AS ?cnt) WHERE {
  ?item wdt:P1866 ?statement;
    wdt:P2124 ?members.
  FILTER(?members > 0 )
}
group by (?item) (?itemLabel)
order by desc (?cnt)
"""

wikidata_site = pywikibot.Site('wikidata', 'wikidata')
repo = wikidata_site.data_repository()

generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)
generator = list(generator)
print('>>> Starting with ' + str(len(generator)) + ' entries')
# shuffle(generator)


with progressbar.ProgressBar(max_value=len(generator), redirect_stdout=True) as bar:
    for index, item in enumerate(generator):
        print('')
        bar.update(index)
        itemdetails = item.get(get_redirect=True)
        itemdetails_id = item.id
        my_chdioid = ''
        changed = False

        claim_list_members = []
        print('>> CHECKING: Wikidata-Item: https://www.wikidata.org/wiki/' + itemdetails_id)
        try:
            claim_list_members = itemdetails['claims']['P2124']
        except KeyError:
            print('-- No Member-Numbers found. I skip that one')
            continue

        claim_list_chdioid = []
        try:
            claim_list_chdioid = itemdetails['claims']['P1866']
        except KeyError:
            print('-- Not Dio-Id for CH found. I skip that one')
            continue

        my_chdioid = claim_list_chdioid[0].getTarget()
        if not my_chdioid:
            print('-- Not Dio-Id for CH found. I skip that one')
            continue

        print('-- that is on ch: http://www.catholic-hierarchy.org/diocese/d' + my_chdioid + '.html')

        latest_claim = False
        for member_claim in claim_list_members:
            if not latest_claim:
                if 'P585' not in member_claim.qualifiers:
                    print('-- Skipping one memberstat due to missing point in time.')
                    continue
                latest_claim = member_claim

            else:
                member_pit = member_claim.qualifiers['P585'][0].getTarget()
                latest_pit = latest_claim.qualifiers['P585'][0].getTarget()

                if member_pit.year > latest_pit.year:
                    latest_claim = member_claim
                elif member_pit.year == latest_pit.year and member_pit.month > latest_pit.month:
                    latest_claim = member_claim
                elif member_pit.year == latest_pit.year and member_pit.month == latest_pit.month and member_pit.day > latest_pit.day:
                    latest_claim = member_claim

        if not latest_claim:
            print('!-- No latest point in time found. I skip.')
            continue
        else:
            print('--- Latest claim in ' + str(latest_claim.qualifiers['P585'][0].getTarget().year) + ' found.')

        for member_claim in claim_list_members:
            if member_claim == latest_claim:
                if member_claim.rank == "preferred":
                    continue
                else:
                    latest_claim.changeRank("preferred", summary=u'changed rank of member-amount')
            else:
                if member_claim.rank == "normal":
                    continue
                else:
                    latest_claim.changeRank("normal", summary=u'changed rank of member-amount')


print('Done!')
