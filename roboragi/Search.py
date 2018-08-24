'''
Search.py
Returns a built comment created from multiple databases when given a search term.
'''

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

import MAL
import AnimePlanet as AniP
import AniDB
import Kitsu
import Anilist
import MU
import NU
import LNDB
from VNDB import VNDB

import CommentBuilder
import DatabaseHandler

import traceback
import time

import sqlite3
import json

import pprint

USERNAME = ''

try:
    import Config
    USERNAME = Config.username
except ImportError:
    pass

sqlConn = sqlite3.connect('synonyms.db')
sqlCur = sqlConn.cursor()

try:
    sqlCur.execute('SELECT dbLinks FROM synonyms WHERE type = "Manga" and lower(name) = ?', ["despair simulator"])
except sqlite3.Error as e:
    print(e)

#Builds a manga reply from multiple sources
def buildMangaReply(searchText, isExpanded, baseComment, blockTracking=False):
    try:       
        ani = {'search_function': Anilist.getMangaDetails,
                'title_function': Anilist.getTitles,
                'synonym_function': Anilist.getSynonyms,
                'checked_synonyms': [],
                'result': None}
        mal = {'search_function': MAL.getMangaDetails,
                'synonym_function': MAL.getSynonyms,
                'title_function': MAL.getTitles,
                'checked_synonyms': [],
                'result': None}
        kit = {'search_function': Kitsu.search_manga,
                'synonym_function': Kitsu.get_synonyms,
                'title_function': Kitsu.get_titles,
                'checked_synonyms': [],
                'result': None}
        mu = {'search_function': MU.getMangaURL,
                'result': None}
        ap = {'search_function': AniP.getMangaURL,
                'result': None}

        try:
            sqlCur.execute('SELECT dbLinks FROM synonyms WHERE type = "Manga" and lower(name) = ?', [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                malsyn = None
                if 'mal' in synonym and synonym['mal']:
                    malsyn = synonym['mal']

                anisyn = None
                if 'ani' in synonym and synonym['ani']:
                    anisyn = synonym['ani']

                kitsyn = None
                if 'kit' in synonym and synonym['kit']:
                    kitsyn = synonym['kit']

                musyn = None
                if 'mu' in synonym and synonym['mu']:
                    musyn = synonym['mu']

                apsyn = None
                if 'ap' in synonym and synonym['ap']:
                    apsyn = synonym['ap']

                mal['result'] = None
                ani['result'] = Anilist.getMangaDetailsById(anisyn) if anisyn else None
                kit['result'] = Kitsu.get_manga(kitsyn) if kitsyn else None
                mu['result'] = MU.getMangaURLById(musyn) if musyn else None
                ap['result'] = AniP.getMangaURLById(apsyn) if apsyn else None

        else:
            data_sources = [ani, kit]
            aux_sources = [mu, ap]

            synonyms = set([searchText])
            titles = set()

            for x in range(len(data_sources)):
                for source in data_sources:
                    if source['result']:
                        break
                    else:
                        for title in titles:
                            if title in source['checked_synonyms']:
                                break

                            if source['result']:
                                break

                            source['result'] = source['search_function'](title)
                            source['checked_synonyms'].append(title)

                            if source['result']:
                                break

                        for synonym in synonyms:
                            if synonym in source['checked_synonyms']:
                                break

                            if source['result']:
                                break

                            source['result'] = source['search_function'](synonym)
                            source['checked_synonyms'].append(synonym)

                            if source['result']:
                                break

                    if source['result']:
                        synonyms.update([synonym.lower() for synonym in source['synonym_function'](source['result'])])
                        titles.update([title.lower() for title in source['title_function'](source['result'])])

            for source in aux_sources:
                for title in titles:
                    source['result'] = source['search_function'](synonym)

                    if source['result']:
                        break

                if not source['result']:
                    for synonym in synonyms:
                        source['result'] = source['search_function'](synonym)

                        if source['result']:
                            break

        if ani['result'] or mal['result'] or kit['result']:
            try:
                titleToAdd = ''
                if ani['result']:
                    try:
                        titleToAdd = ani['result']['title_romaji']
                    except:
                        titleToAdd = ani['result']['title_english']
                elif mal['result']:
                    titleToAdd = mal['result']['title']
                elif kit['result']:
                    try:
                        titleToAdd = kit['result']['title_romaji']
                    except:
                        titleToAdd = kit['result']['title_english']
                

                if (str(baseComment.subreddit).lower is not 'nihilate') and (str(baseComment.subreddit).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Manga', baseComment.author.name, baseComment.subreddit)
            except:
                traceback.print_exc()
                pass
        
        if mal['result'] or ani['result'] or kit['result']:
            return CommentBuilder.buildMangaComment(isExpanded, mal['result'], ani['result'], mu['result'], ap['result'], kit['result'])
        else:
            print('No result found for ' + searchText)
            return None

    except Exception as e:
        traceback.print_exc()
        return None
        

#Builds a manga search for a specific series by a specific author
def buildMangaReplyWithAuthor(searchText, authorName, isExpanded, baseComment, blockTracking=False):
    try:        
        ani = Anilist.getMangaWithAuthor(searchText, authorName)
        mal = None
        mu = None
        ap = None
        
        if ani:
            ap = AniP.getMangaURL(ani['title_english'], authorName)
        else:
            ap = AniP.getMangaURL(searchText, authorName)

        mu = MU.getMangaWithAuthor(searchText, authorName)

        if ani:
            try:
                titleToAdd = ''
                if mal is not None:
                    titleToAdd = mal['title']
                else:
                    titleToAdd = ani['title_english']

                if (str(baseComment.subreddit).lower is not 'nihilate') and (str(baseComment.subreddit).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Manga', baseComment.author.name, baseComment.subreddit)
            except:
                traceback.print_exc()
                pass
            
            return CommentBuilder.buildMangaComment(isExpanded, mal, ani, mu, ap)
    
    except Exception as e:
        traceback.print_exc()
        return None

#Builds an anime reply from multiple sources
def buildAnimeReply(searchText, isExpanded, baseComment, blockTracking=False):
    try:
        mal = {'search_function': MAL.getAnimeDetails,
                'synonym_function': MAL.getSynonyms,
                'title_function': MAL.getTitles,
                'checked_synonyms': [],
                'result': None}
        kit = {'search_function': Kitsu.search_anime,
                'synonym_function': Kitsu.get_synonyms,
                'title_function': Kitsu.get_titles,
                'checked_synonyms': [],
                'result': None}
        ani = {'search_function': Anilist.getAnimeDetails,
                'synonym_function': Anilist.getSynonyms,
                'title_function': Anilist.getTitles,
                'checked_synonyms': [],
                'result': None}
        ap = {'search_function': AniP.getAnimeURL,
                'result': None}
        adb = {'search_function': AniDB.getAnimeURL,
                'result': None}
        
        try:
            sqlCur.execute('SELECT dbLinks FROM synonyms WHERE type = "Anime" and lower(name) = ?', [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                malsyn = None
                if 'mal' in synonym and synonym['mal']:
                    malsyn = synonym['mal']

                kitsyn = None
                if 'kit' in synonym and synonym['kit']:
                    kitsyn = synonym['kit']

                anisyn = None
                if 'ani' in synonym and synonym['ani']:
                    anisyn = synonym['ani']

                apsyn = None
                if 'ap' in synonym and synonym['ap']:
                    apsyn = synonym['ap']

                adbsyn = None
                if 'adb' in synonym and synonym['adb']:
                    adbsyn = synonym['adb']

                mal['result'] = None
                kit['result'] = Kitsu.get_anime(kitsyn) if kitsyn else None
                ani['result'] = Anilist.getAnimeDetailsById(anisyn) if anisyn else None
                ap['result'] = AniP.getAnimeURLById(apsyn) if apsyn else None
                adb['result'] = AniDB.getAnimeURLById(adbsyn) if adbsyn else None
                
        else:
            data_sources = [ani, kit]
            aux_sources = [ap]

            synonyms = set([searchText])
            titles = set()

            for x in range(len(data_sources)):
                for source in data_sources:
                    if source['result']:
                        break
                    else:
                        for synonym in (titles | synonyms):
                            if synonym in source['checked_synonyms']:
                                continue

                            source['result'] = source['search_function'](synonym)
                            source['checked_synonyms'].append(synonym)

                            if source['result']:
                                break

                    if source['result']:
                        synonyms.update([synonym.lower() for synonym in source['synonym_function'](source['result'])])
                        titles.update([title.lower() for title in source['title_function'](source['result'])])


            for source in aux_sources:
                for title in titles:
                    source['result'] = source['search_function'](synonym)

                    if source['result']:
                        break

                if not source['result']:
                    for synonym in synonyms:
                        source['result'] = source['search_function'](synonym)

                        if source['result']:
                            break

        if ani['result'] or mal['result'] or kit['result']:
            try:
                titleToAdd = ''
                if ani['result']:
                    if 'title_romaji' in ani['result']:
                        titleToAdd = ani['result']['title_romaji']
                elif mal['result']:
                    if 'title' in mal['result']:
                        titleToAdd = mal['result']['title']
                elif kit['result']:
                    if 'title_romaji' in kit['result']:
                        titleToAdd = kit['result']['title_romaji']

                if (str(baseComment.subreddit).lower is not 'nihilate') and (str(baseComment.subreddit).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Anime', baseComment.author.name, baseComment.subreddit)
            except:
                traceback.print_exc()
                pass
        
        if mal['result'] or ani['result'] or kit['result']:
            return CommentBuilder.buildAnimeComment(isExpanded, mal['result'], ani['result'], ap['result'], adb['result'], kit['result'])
        else:
            print('No result found for ' + searchText)
            return None

    except Exception as e:
        traceback.print_exc()
        return None

#Builds an LN reply from multiple sources
def buildLightNovelReply(searchText, isExpanded, baseComment, blockTracking=False):
    try:
        mal = {'search_function': MAL.getLightNovelDetails,
                'synonym_function': MAL.getSynonyms,
                'title_function': MAL.getTitles,
                'checked_synonyms': [],
                'result': None}
        ani = {'search_function': Anilist.getLightNovelDetails,
                'synonym_function': Anilist.getSynonyms,
                'title_function': Anilist.getTitles,
                'checked_synonyms': [],
                'result': None}
        kit = {'search_function': Kitsu.search_light_novel,
                'synonym_function': Kitsu.get_synonyms,
                'title_function': Kitsu.get_titles,
                'checked_synonyms': [],
                'result': None}
        nu = {'search_function': NU.getLightNovelURL,
                'result': None}
        lndb = {'search_function': LNDB.getLightNovelURL,
                'result': None}
        
        try:
            sqlCur.execute('SELECT dbLinks FROM synonyms WHERE type = "LN" and lower(name) = ?', [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                malsyn = None
                if 'mal' in synonym and synonym['mal']:
                    malsyn = synonym['mal']

                anisyn = None
                if 'ani' in synonym and synonym['ani']:
                    anisyn = synonym['ani']

                kitsyn = None
                if 'kit' in synonym and synonym['kit']:
                    kitsyn = synonym['kit']

                nusyn = None
                if 'nu' in synonym and synonym['nu']:
                    nusyn = synonym['nu']

                lndbsyn = None
                if 'lndb' in synonym and synonym['lndb']:
                    lndbsyn = synonym['lndb']

                mal['result'] = None
                ani['result'] = Anilist.getMangaDetailsById(anisyn) if anisyn else None
                kit['result'] = Kitsu.get_light_novel(kitsyn) if kitsyn else None
                nu['result'] = NU.getLightNovelById(nusyn) if nusyn else None
                lndb['result'] = LNDB.getLightNovelById(lndbsyn) if lndbsyn else None
                
        else:
            data_sources = [ani, kit]
            aux_sources = [nu, lndb]

            synonyms = set([searchText])
            titles = set()

            for x in range(len(data_sources)):
                for source in data_sources:
                    if source['result']:
                        break
                    else:
                        for synonym in (titles | synonyms):
                            if synonym in source['checked_synonyms']:
                                continue

                            source['result'] = source['search_function'](synonym)
                            source['checked_synonyms'].append(synonym)

                            if source['result']:
                                break

                    if source['result']:
                        synonyms.update([synonym.lower() for synonym in source['synonym_function'](source['result'])])
                        titles.update([title.lower() for title in source['title_function'](source['result'])])


            for source in aux_sources:
                for title in titles:
                    source['result'] = source['search_function'](synonym)

                    if source['result']:
                        break

                if not source['result']:
                    for synonym in synonyms:
                        source['result'] = source['search_function'](synonym)

                        if source['result']:
                            break

        if ani['result'] or mal['result'] or kit['result']:
            try:
                titleToAdd = ''
                if ani['result']:
                    try:
                        titleToAdd = ani['result']['title_romaji']
                    except:
                        titleToAdd = ani['result']['title_english']
                elif mal['result']:
                    titleToAdd = mal['result']['title']
                elif kit['result']:
                    try:
                        titleToAdd = kit['result']['title_romaji']
                    except:
                        titleToAdd = kit['result']['title_english']
                

                if (str(baseComment.subreddit).lower is not 'nihilate') and (str(baseComment.subreddit).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'LN', baseComment.author.name, baseComment.subreddit)
            except:
                traceback.print_exc()
                pass
        
        if mal['result'] or ani['result'] or kit['result']:
            return CommentBuilder.buildLightNovelComment(isExpanded, mal['result'], ani['result'], nu['result'], lndb['result'], kit['result'])
        else:
            print('No result found for ' + searchText)
            return None

    except Exception as e:
        traceback.print_exc()
        return None

#Builds an VN reply from VNDB
def buildVisualNovelReply(searchText, isExpanded, baseComment, blockTracking=False):
    try:
        vndb = VNDB()
        
        try:
            sqlCur.execute('SELECT dbLinks FROM synonyms WHERE type = "VN" and lower(name) = ?', [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                vndbsyn = None
                if 'vndb' in synonym and synonym['vndb']:
                    synonym = synonym['vndb']

                result = vndb.getVisualNovelDetailsById(synonym) if synonym else None
                
        else:
            result = vndb.getVisualNovelDetails(searchText)

        vndb.close()

        if result:
            try:
                titleToAdd = result['title']

                if (str(baseComment.subreddit).lower is not 'nihilate') and (str(baseComment.subreddit).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'VN', baseComment.author.name, baseComment.subreddit)
            except:
                traceback.print_exc()
                pass

            return CommentBuilder.buildVisualNovelComment(isExpanded, result)
        else:
            print('No result found for ' + searchText)
            return None

    except Exception as e:
        traceback.print_exc()
        return None

#Checks if the bot is the parent of this comment.
def isBotAParent(comment, reddit):
    try:
        parentComment = reddit.get_info(thing_id=comment.parent_id)

        if (parentComment.author.name == USERNAME):
            return True
        else:
            return False
            
    except:
        #traceback.print_exc()
        return False

#Checks if the comment is valid (i.e. not already seen, not a post by Roboragi and the parent commenter isn't Roboragi)
def isValidComment(comment, reddit):
    try:
        if (DatabaseHandler.commentExists(comment.id)):
            return False

        try:
            if (comment.author.name == USERNAME):
                DatabaseHandler.addComment(comment.id, comment.author.name, comment.subreddit, False)
                return False
        except:
            pass

        return True
        
    except:
        traceback.print_exc()
        return False

#Checks if a submission is valid (i.e. not already seen, not a submission by Roboragi). This WAS used before, but I have since removed the functionality it was relevant to.
def isValidSubmission(submission):
    try:
        if (DatabaseHandler.commentExists(submission.id)):
            return False

        try:
            if (submission.author.name == 'Roboragi'):
                DatabaseHandler.addComment(submission.id, submission.author.name, submission.subreddit, False)
                return False
        except:
            pass

        return True
        
    except:
        traceback.print_exc()
        return False
