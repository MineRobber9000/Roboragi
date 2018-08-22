# -*- coding: utf-8 -*-

"""
MAL.py
Handles all of the connections to MyAnimeList.
"""

# Copyright (C) 2018  Nihilate
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import xml.etree.cElementTree as ET
import requests
import traceback
import pprint
import difflib

try:
    import Config
    MALUSERAGENT = Config.maluseragent
    MALAUTH = Config.malauth
except ImportError:
    pass

mal = requests.Session()

#Sets up the connection to MAL.
def setup():
    mal.headers.update({'Authorization': MALAUTH, 'User-Agent': MALUSERAGENT})

def getSynonyms(request):
    synonyms = []
    synonyms.extend(request['synonyms']) if request['synonyms'] else None
    return synonyms

def getTitles(request):
    titles = []
    titles.append(request['title']) if request['title'] else None
    titles.append(request['english']) if request['english'] else None
    return titles

#Returns the closest anime (as a Json-like object) it can find using the given searchtext. MAL returns XML (bleh) so we have to convert it ourselves.
def getAnimeDetails(searchText, animeId=None):
    try:
        try:
            request = mal.get('https://myanimelist.net/api/anime/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()
        except:
            setup()
            request = mal.get('https://myanimelist.net/api/anime/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()
        
        convertedRequest = convertShittyXML(request.text)
        rawList = ET.fromstring(convertedRequest)

        animeList = []
        
        for anime in rawList.findall('./entry'):
            animeID = anime.find('id').text
            title = anime.find('title').text
            title_english = anime.find('english').text

            synonyms = None
            if anime.find('synonyms').text is not None:
                synonyms = anime.find('synonyms').text.split(";")

            episodes = anime.find('episodes').text
            animeType = anime.find('type').text
            status = anime.find('status').text
            start_date = anime.find('start_date').text
            end_date = anime.find('end_date').text
            synopsis = anime.find('synopsis').text
            image = anime.find('image').text

            data = {'id': animeID,
                    'title': title,
                    'english': title_english,
                    'synonyms': synonyms,
                    'episodes': episodes,
                    'type': animeType,
                    'status': status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'synopsis': synopsis,
                    'image': image}

            animeList.append(data)

        if animeId:
            closestAnime = getThingById(animeId, animeList)
        else:
            closestAnime = getClosestAnime(searchText, animeList)

        return closestAnime
        
    except Exception:
        #traceback.print_exc()
        mal.close()
        return None

#Given a list, it finds the closest anime series it can.
def getClosestAnime(searchText, animeList):
    try:
        nameList = []
        
        for anime in animeList:
            nameList.append(anime['title'].lower())

            
            if anime['english'] is not None:
                nameList.append(anime['english'].lower())

            if anime['synonyms']:
                for synonym in anime['synonyms']:
                    nameList.append(synonym.lower())

        closestNameFromList = difflib.get_close_matches(searchText.lower(), nameList, 1, 0.90)[0]

        for anime in animeList:
            if anime['title']:
                if anime['title'].lower() == closestNameFromList.lower():
                    return anime
            if anime['english']:
                if anime['english'].lower() == closestNameFromList.lower():
                    return anime
            for synonym in anime['synonyms']:
                if synonym.lower() == closestNameFromList.lower():
                    return anime

        return None
    except Exception:
        #traceback.print_exc()
        return None

#MAL's XML is a piece of crap. It needs to be escaped twice because they do shit like this: &amp;sup2;
def convertShittyXML(text):
    import html.parser

   

    #It pains me to write shitty code, but MAL needs to improve their API and I'm sick of not being able to parse shit
    text = text.replace('&psi;','Ψ').replace('&Eacute;', 'É').replace('&times;', 'x').replace('&rsquo;', "'").replace('&lsquo;', "'").replace('&hellip', '...').replace('&le', '<').replace('<;', '; ').replace('&hearts;', '♥').replace('&mdash;', '-')
    text = text.replace('&eacute;', 'é').replace('&ndash;', '-').replace('&Aacute;', 'Á').replace('&acute;', 'à').replace('&ldquo;', '"').replace('&rdquo;', '"').replace('&Oslash;', 'Ø').replace('&frac12;', '½').replace('&infin;', '∞')
    text = text.replace('&agrave;', 'à').replace('&egrave;', 'è').replace('&dagger;', '†').replace('&sup2;', '²').replace('&#039;', "'")

    #text = text.replace('&', '&amp;')

    return text


    text=html.parser.HTMLParser().unescape(text)
    return html.parser.HTMLParser().unescape(text)

#Used to check if two descriptions are relatively close. This is used in place of author searching because MAL don't give authors at any point.
def getClosestFromDescription(mangaList, descriptionToCheck):
    try:
        descList = []
        for manga in mangaList:
            descList.append(manga['synopsis'].lower())

        closestNameFromList = difflib.get_close_matches(descriptionToCheck.lower(), descList, 1, 0.1)[0]

        for manga in mangaList:
            if closestNameFromList == manga['synopsis'].lower():
                return manga
        
    except:
        return None

#Since MAL doesn't give me an author, I make a search using similar descriptions instead. Super janky.
def getMangaCloseToDescription(searchText, descriptionToCheck):
    try:
        try:
            request = mal.get('https://myanimelist.net/api/manga/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()
        except:
            setup()
            request = mal.get('https://myanimelist.net/api/manga/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()

        convertedRequest = convertShittyXML(request.text)
        rawList = ET.fromstring(convertedRequest)

        mangaList = []
        
        for manga in rawList.findall('./entry'):
            mangaID = manga.find('id').text
            title = manga.find('title').text
            title_english = manga.find('english').text

            synonyms = None
            if manga.find('synonyms').text is not None:
                synonyms = manga.find('synonyms').text.split(";")

            chapters = manga.find('chapters').text
            volumes = manga.find('volumes').text
            mangaType = manga.find('type').text
            status = manga.find('status').text
            start_date = manga.find('start_date').text
            end_date = manga.find('end_date').text
            synopsis = manga.find('synopsis').text
            image = manga.find('image').text

            data = {'id': mangaID,
                    'title': title,
                    'english': title_english,
                    'synonyms': synonyms,
                    'chapters': chapters,
                    'volumes': volumes,
                    'type': mangaType,
                    'status': status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'synopsis': synopsis,
                    'image': image}

            mangaList.append(data)

        closeManga = getListOfCloseManga(searchText, mangaList)

        return getClosestFromDescription(closeManga, descriptionToCheck)
    except:
        mal.close()
        #traceback.print_exc()
        return None
    
def getLightNovelDetails(searchText, lnId=None):
    return getMangaDetails(searchText, lnId, True)

#Returns the closest manga series given a specific search term. Again, MAL returns XML, so we conver it ourselves
def getMangaDetails(searchText, mangaId=None, isLN=False):
    try:
        try:
            request = mal.get('https://myanimelist.net/api/manga/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()
        except:
            setup()
            request = mal.get('https://myanimelist.net/api/manga/search.xml?q=' + searchText.rstrip(), timeout=10)
            mal.close()

        convertedRequest = convertShittyXML(request.text)
        rawList = ET.fromstring(convertedRequest)

        mangaList = []
        
        for manga in rawList.findall('./entry'):
            mangaID = manga.find('id').text
            title = manga.find('title').text
            title_english = manga.find('english').text

            synonyms = None
            if manga.find('synonyms').text is not None:
                synonyms = manga.find('synonyms').text.split(";")

            chapters = manga.find('chapters').text
            volumes = manga.find('volumes').text
            mangaType = manga.find('type').text
            status = manga.find('status').text
            start_date = manga.find('start_date').text
            end_date = manga.find('end_date').text
            synopsis = manga.find('synopsis').text
            image = manga.find('image').text

            data = {'id': mangaID,
                     'title': title,
                     'english': title_english,
                     'synonyms': synonyms,
                     'chapters': chapters,
                     'volumes': volumes,
                     'type': mangaType,
                     'status': status,
                     'start_date': start_date,
                     'end_date': end_date,
                     'synopsis': synopsis,
                     'image': image }

            #ignore or allow LNs
            if 'novel' in mangaType.lower():
                if isLN:
                    mangaList.append(data)
            else:
                if not isLN:
                    mangaList.append(data)

        if mangaId:
            closestManga = getThingById(mangaId, mangaList)
        else:
            closestManga = getClosestManga(searchText, mangaList)

        if closestManga:
            return closestManga
        else:
            return None

    except:
        mal.close()
        #traceback.print_exc()
        return None

#Returns a list of manga with titles very close to the search text. Current unused because MAL's API is shit and doesn't return author names.
def getListOfCloseManga(searchText, mangaList):
    try:
        ratio = 0.90
        returnList = []
        
        for manga in mangaList:          
            if round(difflib.SequenceMatcher(lambda x: x == "", manga['title'].lower(), searchText.lower()).ratio(), 3) >= ratio:
                returnList.append(manga)
            elif manga['english'] is not None:
                if round(difflib.SequenceMatcher(lambda x: x == "", manga['english'].lower(), searchText.lower()).ratio(), 3) >= ratio:
                    returnList.append(manga)
            elif manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    if round(difflib.SequenceMatcher(lambda x: x == "", synonym, searchText.lower()).ratio(), 3) >= ratio:
                        returnList.append(manga)
                        break

        return returnList
        
    except Exception:
        #traceback.print_exc()
        return None

#Used to determine the closest manga to a given search term in a list
def getClosestManga(searchText, mangaList):
    try:
        nameList = []
        
        for manga in mangaList:
            nameList.append(manga['title'].lower())
            
            if manga['english'] is not None:
                nameList.append(manga['english'].lower())
                
            if manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    nameList.append(synonym.lower().strip())
        
        closestNameFromList = difflib.get_close_matches(searchText.lower(), nameList, 1, 0.90)[0]

        for manga in mangaList:
            if manga['title'].lower() == closestNameFromList.lower():
                return manga
            elif manga['english'] is not None:
                if manga['english'].lower() == closestNameFromList.lower():
                    return manga

        for manga in mangaList:
            if manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    if synonym.lower().strip() == closestNameFromList.lower():
                        return manga

        return None
    except Exception:
        #traceback.print_exc()
        return None


#Used to find thing by an id
def getThingById(thingId, thingList):
    try:       
        for thing in thingList:
            if int(thing['id']) == int(thingId):
                return thing
            
        return None
    except Exception:
        #traceback.print_exc()
        return None

setup()
