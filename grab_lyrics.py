#!/usr/bin/env python
# coding: utf-8

# Collect Chinese Lyrics from Mojim

import pathlib
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from glob import glob
from pathlib import Path
import click

from mojim.clean import clean_lyrics

# Base URL for the Mojim website
base_url = 'https://mojim.com/'

# Specify user-agent for scraping (want to make sure we get the desktop version, in case it makes a difference)
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
headers = {'User-Agent': user_agent}

def get_artist_urls(start_urls):
    """
    Given a list of starting URLs (e.g. popular male artists, popular female artists, popular groups)
    build a list of artist URLs
    """
    artists = []

    for url in start_urls:
        response = requests.get(url,headers=headers)
        html = response.content.decode('utf-8')
        soup = BeautifulSoup(html, features="html.parser")
        artist_list = soup.find_all("ul", class_="s_listA")[0].children
        
        for artist in artist_list:
            entry = {}
            detail = list(artist.children)[0]
            entry["link_title"] = detail.get('title')
            entry["link_url"] = detail.get('href')
            entry["artist_name"] = detail.text
            artists.append(entry)

    return artists

def get_song_urls(artists):
    """
    Given a dataframe of artist URLs, scrape the corresponding song URLs
    """
    songs = []

    for artist in artists:
        url = base_url + artist['link_url']
        response = requests.get(url,headers=headers)
        html = response.content.decode('utf-8')
        soup = BeautifulSoup(html, features="html.parser")
        hc3 = soup.find_all("span", class_="hc3")
        
        song_links = []

        for box in hc3:
            song_links.extend(box.findChildren('a', recursive=True))

        for sl in song_links:
            song_entry = {}
            song_entry['artist_name'] = artist['artist_name']
            song_entry['artist_url'] = artist['link_url']
            song_entry['song_url'] = sl.get('href')
            #song_entry['song_link_title'] = sl.get('title')
            song_entry['song_name'] = sl.text
            songs.append(song_entry)

    return pd.DataFrame(songs)

def get_lyrics(songs, ignore):
    """
    Given a dataframe of songs URLs, scrape the corresponding lyrics
    """
    song_lyrics = []

    for song_index, song in songs.iterrows():
        if song['song_url'] in ignore:
            #print('skipping' + song['song_url'])
            continue

        if song_index % 100 == 0:
            print("Scraping song " + str(song_index))
            #print(f"Scraping song {song_index}...")

        if song_index % 1000 == 0:
            if (len(song_lyrics) > 0):
                lyric_df = pd.DataFrame(song_lyrics)
                lyric_repr = lyric_df.copy()
                lyric_repr['song_lyrics'] = lyric_df['song_lyrics'].map(lambda a: repr(a))
                lyric_repr.to_json("./scraped/lyrics_recent.json")

        entry = {}
        entry['artist_name'] = song['artist_name']
        entry['artist_url'] = song['artist_url']
        entry['song_url'] = song['song_url']
        entry['song_name'] = song['song_name']

        url = base_url + song['song_url']
        response = requests.get(url,headers=headers)

        try:
            content = response.content
            html = content.decode('utf-8')
        except UnicodeDecodeError as e:
            print('Failed to decode ' + entry['song_url'])

        soup = BeautifulSoup(html, features="html.parser")
        lyric_body = soup.find("div", class_="fsZ")
        entry['song_lyrics'] = lyric_body

        song_lyrics.append(entry)
        
    return pd.DataFrame(song_lyrics)
      
def get_previously_scraped_urls():
    """Build list of URLs to ignore from previously scraped files"""
    past_scrapes = glob("./scraped/lyrics*.json")
    
    if len(past_scrapes) == 0:
      return []
    
    past = pd.DataFrame()

    for f in past_scrapes:
        past = pd.concat([past, pd.read_json(f)])

    past.reset_index(drop=True, inplace=True)
    return set(past['song_url'].values)

  
def combine_scraped_files(lyrics):
    """
    Combines all JSON files in the path "./scraped" that start with "lyrics"
    """
    past_scrapes = glob("./scraped/lyrics*.json")
    combined = pd.DataFrame()

    for f in past_scrapes:
        combined = pd.concat([combined, pd.read_json(f)])
        
    combined = pd.concat([combined, lyrics])
    combined.reset_index(drop=True, inplace=True)
    combined.drop_duplicates('song_url', inplace=True)
    combined = combined[combined['song_lyrics'].notnull()]
    
    combined.to_json("./scraped/lyrics_combined.json")
    print("Wrote combined lyric files to ./scraped/lyrics_combined.json.  You can remove any other 'lyrics*' files in scraped.")
    
    return combined
    

@click.command()
@click.option('--resume', default=True, help='Whether to resume a scrape in progress')
@click.option('--combine_only', default=False, help='Skip scraping and just combine scraped files')
def perform_scrape(resume, combine_only):
    """Performs a scrape of Mojim.com to get the most popular singers, and scrape their songs"""
    
    Path("./scraped").mkdir(parents=True, exist_ok=True)
    
    SONG_URL_PATH = "./scraped/song_urls.json"
    
    # These starting URLs list the top male, female, and group artists respectively
    start_urls = ["https://mojim.com/cnza2.htm", "https://mojim.com/cnzb2.htm", "https://mojim.com/cnzc2.htm"]
    
    if not combine_only:
        # Only scrape song URLs if we don't already have a list
        if not pathlib.Path(SONG_URL_PATH).exists() or not resume:
          print("Scraping new song list...")
          artists = get_artist_urls(start_urls)
          songs = get_song_urls(artists)
          songs.to_json(SONG_URL_PATH)
          print("Saved new song list as " + SONG_URL_PATH)
        else:
          print("Using previously scraped song list.  To use a new list, pass --resume=False")
          songs = pd.read_json(SONG_URL_PATH)

        print("Song list contains " + str(songs.shape[0]) + " songs")

        ignore = get_previously_scraped_urls()
        if len(ignore) != 0:
          print("Found " + str(len(ignore)) + " previously scraped URLs.  Ignoring these.")
        else:
          print("No previous scraped lyric files, starting from scratch.")

        lyrics = get_lyrics(songs, ignore)

    # Combine scraped files together
    df = combine_scraped_files(pd.DataFrame())
        
    # Clean the lyrics
    print("Cleaning scraped lyric HTML")
    lyrics_cleaned = df.apply(lambda x: clean_lyrics(x['song_lyrics']), axis=1)
    
    # Add cleaned lyrics column
    df['cleaned_lyrics'] = lyrics_cleaned
    
    print("Dropping anything empty")
    df = df[df["cleaned_lyrics"].str.len() > 0]
    
    print("Dropping anything on exclude list")
    
    try:
        with open("exclude_list.txt", "rb") as xf:
            exclude_list = xf.read().splitlines()
            exclude_list = [e.decode() for e in exclude_list]

        df = df[~df["cleaned_lyrics"].isin(exclude_list)]
    except Exception as e:
        print("Encountered exception processing exclusions")
        print(e)

    # Drop raw lyrics column
    df = df.drop('song_lyrics', axis=1)

    # Remove lines with empty lyrics
    df = df[df['cleaned_lyrics'].notnull()]
    df = df.reset_index(drop=True)
    
    with open('./top_song_lyrics_cleaned_cn.jsonl', 'w', encoding='utf-8') as file:
        df.to_json(file, lines=True, orient="records", force_ascii=False)

    
if __name__ == '__main__':
    perform_scrape()
    
