#!/bin/bash

grep -v -F -x -f data/known-to-wikidata.txt data/known-on-ch.txt > data/not-yet-known.txt
