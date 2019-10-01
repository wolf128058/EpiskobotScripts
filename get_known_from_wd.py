#!/usr/bin/python3
# -*- coding: utf-8 -*-

from SPARQLWrapper import SPARQLWrapper, JSON
import json

endpoint_url = "https://query.wikidata.org/sparql"

query = """# by cat-id
SELECT ?cat_id WHERE {
  ?item wdt:P1047 ?cat_id
}
"""


def get_results(endpoint_url, query):
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


results = get_results(endpoint_url, query)

aCatIds = []

for result in results["results"]["bindings"]:
    aCatIds.append(result['cat_id']['value'])

aCatIds = set(aCatIds)
aCatIds = list(aCatIds)
aCatIds.sort()

outFile = open("data/known-to-wikidata.txt", "w")
outFile.write('\n'.join(aCatIds))
outFile.close()
