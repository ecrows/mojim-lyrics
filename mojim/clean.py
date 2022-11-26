#!/usr/bin/env python
# coding: utf-8

import pandas as pd
from pprint import pprint
from bs4 import BeautifulSoup
import re
import random

__all__ = ["clean_lyrics"]

def clean_lyrics(raw_lyrics):
    soup = BeautifulSoup(raw_lyrics, features="html.parser")
    # artist = soup.findAll("dl", {"class": "fsZx1"})[0]
    # title = soup.findAll("dt", {"class": "fsZx2"})[0]
    try:
        body = soup.findAll("dd", {"class": "fsZx3"})[0]
    except IndexError:
        # print("Body does not contain expected lyric block")
        # print(raw_lyrics)
        return None
    
    string_lyrics = '\n'.join([str(c) for c in body.children])
    
    # Remove invalid characters
    string_lyrics = string_lyrics.replace('<br/>', '').replace('#', '').replace('*', '').replace('\u3000', ' ').replace('＃', '').replace('＊', '')
    
    re_mojim = re.compile(r"^更(.+)\n(.+)</a>$", re.MULTILINE) # Remove Mojim inserted text
    string_lyrics = re_mojim.sub('', string_lyrics)
    
    # Remove leading and trailing spaces
    string_lyrics = '\n'.join([s.strip() for s in string_lyrics.split('\n')])
    
    # Remove labels like the following, or for instrument credits
    # "作词" # Lyrics
    # "作曲" # Composer
    # "编曲" # Arranger
    start_labels = re.compile(r"^.+(：|:).+$", re.MULTILINE) # Remove lyrics, composer, and arranger labels
    string_lyrics = start_labels.sub('', string_lyrics).strip()
    
    # Remove lines of hyphens
    hyphen_line = re.compile(r"^-*$", re.MULTILINE)
    string_lyrics = hyphen_line.sub('', string_lyrics)
    
    # Remove lines that look like they contain HTML tags
    htmlish = re.compile(r"^.*<[A-z]*>.*$", re.MULTILINE)
    string_lyrics = htmlish.sub('', string_lyrics)
    
    # Compress newlines.  For many subsequent newlines, compress to a double newline
    double_newline = re.compile(r"\n\n", re.MULTILINE)
    many_newline = re.compile(r"\n[\n]+", re.MULTILINE)
    string_lyrics = double_newline.sub('\n', string_lyrics)
    string_lyrics = many_newline.sub('\n\n', string_lyrics)
    
    # Remove trailing newlines, whitespace
    string_lyrics = string_lyrics.strip()
    
    return string_lyrics

# Test on random index to gauge quality
# random_index = random.randint(0, df.shape[0])
# random_lyrics = clean_lyrics(df["song_lyrics"][random_index])
# print(random_lyrics)

