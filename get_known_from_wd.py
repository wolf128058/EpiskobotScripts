#!/usr/bin/python3
# -*- coding: utf-8 -*-

from SPARQLWrapper import SPARQLWrapper, JSON
import json

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


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


endpoint_url = "https://query.wikidata.org/sparql"

query = "SELECT ?item ?cat_id WHERE { ?item wdt:P1047 ?cat_id. }"

aCatIds = []


def get_results(endpoint_url, query):
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


try:
    results = get_results(endpoint_url, query)
    for result in results["results"]["bindings"]:
        aCatIds.append(result['cat_id']['value'])
except:
    print('### Failed by Sparl-Wrapper')


if(len(aCatIds) == 0):
    r = requests_retry_session().get('https://query.wikidata.org/sparql?query=SELECT%20%3Fcat_id%20WHERE%20{%0A%20%20%3Fitem%20wdt%3AP1047%20%3Fcat_id%0A}&format=json')
    if r.status_code != 200:
        print('### Failed on getting by URL: ' + chorgurl)
    else:
        print('--- Success on getting by URL')
        json_content = json.loads(r.content)
        for result in json_content["results"]["bindings"]:
            aCatIds.append(result['cat_id']['value'])


aCatIds = set(aCatIds)
aCatIds = list(aCatIds)
aCatIds.sort()


if(len(aCatIds) > 0):
    outFile = open("data/known-to-wikidata.txt", "w")
    outFile.write('\n'.join(aCatIds))
    outFile.close()
