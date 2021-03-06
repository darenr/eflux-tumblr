#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import requests_cache

one_week = 7 * 60 * 60 * 24
requests_cache.install_cache(
    'eflux_cache', backend='sqlite', expire_after=one_week)

import os
from bs4 import BeautifulSoup
import json
import codecs
import traceback
import re
import urllib
import sys
import urlparse
import datetime
import unicodedata

def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn').lower()

month_to_number = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12
}

month_matcher = re.compile(
    u'(.*?)(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})([–,-]|\s+.*$)', re.M | re.I | re.UNICODE)

exhibitions = []

matched = set([])

def mk_record(imgurl, alt, permalink, year, month):
    if alt:
        parts = [x.strip() for x in alt.split('\n')]
        title = parts.pop(0)
        end_date, start_date, description = None, None, None

        artist_name = None


        # scan title for mention of artist name
        for artist in all_artists:
            if strip_accents(artist) in strip_accents(title):
                matched.add(artist)
                artist_name = artist

        if parts and 'e-flux' not in title:

            if len(parts):
                description = ' / '.join(parts[0:-1])

            # extract day of month if possible
            if description:
                m = month_matcher.match(description)
                if m and len(m.groups()):
                    if m.group(2).lower() in month_to_number:
                        start_date = datetime.datetime.strptime(("%d/%d/%d" % (month_to_number[m.group(2).lower()], int(m.group(3)), year)), "%m/%d/%Y")

            if not start_date:
                # default to the year/month the tumblr post occured on
                start_date = datetime.datetime.strptime(("%d/%d/%d" % (month, 15, year)), "%m/%d/%Y")

            if imgurl and title and permalink:
                w = {
                    "permalink": permalink.strip(),
                    "title": title.strip(),
                    "image_url": imgurl.strip()
                }

                if start_date:
                    w["start_date"] = start_date.strftime('%m/%d/%Y')
                    w["end_date"] = (start_date + datetime.timedelta(days=90)).strftime('%m/%d/%Y')


                if artist_name:
                    w['artist_name'] = artist_name

                if description:
                    w['description'] = description

                print ' *', w['title']

                exhibitions.append(w)


def process_post(url, year, month):
    # print ' * fetching post...', url
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html5lib')

    for article in soup.find_all("article", {'class': 'type-photo'}):
        for img in article.find_all("img"):
            # find caption a hrefs and decode the redict url
            link = None
            for a in article.find_all("a"):
                # overwrite, keep only last link
                if 'redirect?' in a['href']:
                    link = a["href"]
            if link:
                d = urlparse.parse_qs(urlparse.urlsplit(link.decode('utf8')).query)
                if d and 'z' in d:
                    mk_record(img['src'], img['alt'], d['z'][0], year, month)


def process_month(year, month):
    url = "http://e-flux-e-flux.tumblr.com/archive/%d/%d" % (year, month)
    print " * fetching archive %02d/%d" % (month, year)
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html5lib')
    posts = []
    for section in soup.find_all("section", {'id': 'posts_%d%02d' % (year, month)}):
        for post in soup.find_all("div", {'class': 'post_glass'}):
            for a in post.find_all("a", {'class': 'hover'}):
                posts.append(a['href'])

    return posts


if __name__ == "__main__":

    with codecs.open('reference_data/artist_names.json', 'rb', 'utf-8') as f:
        all_artists = json.loads(f.read().encode('utf-8'))

    try:
        for year in range(2014, 2017):
            for month in range(1, 12):
                posts = process_month(year, month)
                if posts:
                    for post in posts:
                        process_post(post, year=year, month=month)

        output_filename = "data/eflux-exhibitions.json"
        with codecs.open(output_filename, 'wb', 'utf-8') as f:
            f.write(json.dumps(exhibitions, ensure_ascii=False, encoding='utf8'))
            print ' *', 'saved %d records to %s' % (len(exhibitions), output_filename)
            print ' *', 'matched %d artist names' % (len(matched))

    except Exception, e:
        traceback.print_exc()
        print str(e)
