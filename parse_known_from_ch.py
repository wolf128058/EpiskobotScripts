#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long, bare-except, invalid-name

from string import ascii_lowercase
import re
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


def extract_chids(str_html):
    l_result = re.findall(b'\<a href="b([a-z_]{1,8}).html">', str_html)
    return l_result

L_CHIDS = []
L_ENTRIES = []
for c in ascii_lowercase:
    L_ENTRIES.append('http://www.catholic-hierarchy.org/bishop/la' + c + '.html')
L_ENTRIES.append('http://www.catholic-hierarchy.org/bishop/la_.html')

for entry in L_ENTRIES:
    print('>>> CHECKING: ' + entry)
    request_entry = requests_retry_session().get(entry)

    if request_entry.status_code != 200:
        print('### HTTP-ERROR ON cath-id: ' + entry)
        continue
    content_to_check = request_entry.content
    L_CHIDS += extract_chids(content_to_check)
    is_initial = True
    while is_initial or pagination_next:
        pagination_next = re.findall(b'\<a href="([^"]+)"><img.*alt="\[Next Page\]".*<\/a>', content_to_check)
        if pagination_next:
            print('- PaginationFollower:' + pagination_next[0].decode('utf8'))
            url_following_page = 'http://www.catholic-hierarchy.org/bishop/' + (pagination_next[0].decode('utf-8'))
            request_following_page = requests_retry_session().get(url_following_page)
            if request_following_page.status_code != 200:
                print('### HTTP-ERROR ON: ' + url_following_page)
                continue
            content_to_check = request_following_page.content
            L_CHIDS += extract_chids(content_to_check)
        is_initial = False

with open('data/known-on-ch.txt', 'w') as f:
    for line in L_CHIDS:
        if line.decode('utf8') != 'vacant':
            f.write(line.decode('utf8') + "\n")
