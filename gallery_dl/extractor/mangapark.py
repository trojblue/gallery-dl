# -*- coding: utf-8 -*-

# Copyright 2015-2023 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://mangapark.net/"""

from .common import ChapterExtractor, Extractor, Message
from .. import text, util
import re

BASE_PATTERN = r"(?:https?://)?(?:www\.)?mangapark\.(?:net|com|org|io|me)"


class MangaparkBase():
    """Base class for mangapark extractors"""
    category = "mangapark"
    _match_title = None

    def _parse_chapter_title(self, title):
        if not self._match_title:
            MangaparkBase._match_title = re.compile(
                r"(?i)"
                r"(?:vol(?:\.|ume)?\s*(\d+)\s*)?"
                r"ch(?:\.|apter)?\s*(\d+)([^\s:]*)"
                r"(?:\s*:\s*(.*))?"
            ).match
        match = self._match_title(title)
        return match.groups() if match else (0, 0, "", "")


class MangaparkChapterExtractor(MangaparkBase, ChapterExtractor):
    """Extractor for manga-chapters from mangapark.net"""
    pattern = BASE_PATTERN + r"/title/[^/?#]+/(\d+)"
    test = (
        ("https://mangapark.net/title/114972-aria/6710214-en-ch.60.2", {
            "count": 70,
            "pattern": r"https://[\w-]+\.mpcdn\.org/comic/2002/e67"
                       r"/61e29278a583b9227964076e/\d+_\d+_\d+_\d+\.jpeg"
                       r"\?acc=[^&#]+&exp=\d+",
            "keyword": {
                "artist": [],
                "author": ["Amano Kozue"],
                "chapter": 60,
                "chapter_id": 6710214,
                "chapter_minor": ".2",
                "count": 70,
                "date": "dt:2022-01-15 09:25:03",
                "extension": "jpeg",
                "filename": str,
                "genre": ["adventure", "comedy", "drama", "sci_fi",
                          "shounen", "slice_of_life"],
                "lang": "en",
                "language": "English",
                "manga": "Aria",
                "manga_id": 114972,
                "page": int,
                "source": "Koala",
                "title": "Special Navigation - Aquaria Ii",
                "volume": 12,
            },
        }),
        ("https://mangapark.com/title/114972-aria/6710214-en-ch.60.2"),
        ("https://mangapark.org/title/114972-aria/6710214-en-ch.60.2"),
        ("https://mangapark.io/title/114972-aria/6710214-en-ch.60.2"),
        ("https://mangapark.me/title/114972-aria/6710214-en-ch.60.2"),
    )

    def __init__(self, match):
        self.root = text.root_from_url(match.group(0))
        url = "{}/title/_/{}".format(self.root, match.group(1))
        ChapterExtractor.__init__(self, match, url)

    def metadata(self, page):
        data = util.json_loads(text.extr(
            page, 'id="__NEXT_DATA__" type="application/json">', '<'))
        chapter = (data["props"]["pageProps"]["dehydratedState"]
                   ["queries"][0]["state"]["data"]["data"])
        manga = chapter["comicNode"]["data"]
        source = chapter["sourceNode"]["data"]

        self._urls = chapter["imageSet"]["httpLis"]
        self._params = chapter["imageSet"]["wordLis"]
        vol, ch, minor, title = self._parse_chapter_title(chapter["dname"])

        return {
            "manga"     : manga["name"],
            "manga_id"  : manga["id"],
            "artist"    : source["artists"],
            "author"    : source["authors"],
            "genre"     : source["genres"],
            "volume"    : text.parse_int(vol),
            "chapter"   : text.parse_int(ch),
            "chapter_minor": minor,
            "chapter_id": chapter["id"],
            "title"     : chapter["title"] or title or "",
            "lang"      : chapter["lang"],
            "language"  : util.code_to_language(chapter["lang"]),
            "source"    : chapter["srcTitle"],
            "date"      : text.parse_timestamp(chapter["dateCreate"] // 1000),
        }

    def images(self, page):
        return [
            (url + "?" + params, None)
            for url, params in zip(self._urls, self._params)
        ]


class MangaparkMangaExtractor(MangaparkBase, Extractor):
    """Extractor for manga from mangapark.net"""
    subcategory = "manga"
    pattern = BASE_PATTERN + r"/title/(\d+)(?:-[^/?#]*)?/?$"
    test = (
        ("https://mangapark.net/title/114972-aria", {
            "count": 141,
            "pattern": MangaparkChapterExtractor.pattern,
            "keyword": {
                "chapter": int,
                "chapter_id": int,
                "chapter_minor": str,
                "date": "type:datetime",
                "lang": "en",
                "language": "English",
                "manga_id": 114972,
                "source": "re:Horse|Koala",
                "title": str,
                "volume": int,
            },
        }),
        ("https://mangapark.com/title/114972-"),
        ("https://mangapark.com/title/114972"),
        ("https://mangapark.com/title/114972-aria"),
        ("https://mangapark.org/title/114972-aria"),
        ("https://mangapark.io/title/114972-aria"),
        ("https://mangapark.me/title/114972-aria"),
    )

    def __init__(self, match):
        self.root = text.root_from_url(match.group(0))
        self.manga_id = int(match.group(1))
        Extractor.__init__(self, match)

    def items(self):
        for chapter in self.chapters():
            chapter = chapter["data"]
            url = self.root + chapter["urlPath"]

            vol, ch, minor, title = self._parse_chapter_title(chapter["dname"])
            data = {
                "manga_id"  : self.manga_id,
                "volume"    : text.parse_int(vol),
                "chapter"   : text.parse_int(ch),
                "chapter_minor": minor,
                "chapter_id": chapter["id"],
                "title"     : chapter["title"] or title or "",
                "lang"      : chapter["lang"],
                "language"  : util.code_to_language(chapter["lang"]),
                "source"    : chapter["srcTitle"],
                "date"      : text.parse_timestamp(
                    chapter["dateCreate"] // 1000),
                "_extractor": MangaparkChapterExtractor,
            }
            yield Message.Queue, url, data

    def chapters(self):
        source = self.config("source")
        if source:
            return self.chapters_source(source)
        return self.chapters_all()

    def chapters_all(self):
        pnum = 0
        variables = {
            "select": {
                "comicId": self.manga_id,
                "range"  : None,
                "isAsc"  : not self.config("chapter-reverse"),
            }
        }

        while True:
            data = self._request_graphql(
                "get_content_comicChapterRangeList", variables)

            for item in data["items"]:
                yield from item["chapterNodes"]

            if not pnum:
                pager = data["pager"]
            pnum += 1

            try:
                variables["select"]["range"] = pager[pnum]
            except IndexError:
                return

    def chapters_source(self, source_id):
        variables = {
            "sourceId": source_id,
        }

        yield from self._request_graphql(
            "get_content_source_chapterList", variables)

    def _request_graphql(self, opname, variables):
        url = self.root + "/apo/"
        data = {
            "query"        : QUERIES[opname],
            "variables"    : util.json_dumps(variables),
            "operationName": opname,
        }
        return self.request(
            url, method="POST", json=data).json()["data"][opname]


QUERIES = {
    "get_content_comicChapterRangeList": """
  query get_content_comicChapterRangeList($select: Content_ComicChapterRangeList_Select) {
    get_content_comicChapterRangeList(
      select: $select
    ) {
      reqRange{x y}
      missing
      pager {x y}
      items{
        serial
        chapterNodes {

  id
  data {


  id
  sourceId

  dbStatus
  isNormal
  isHidden
  isDeleted
  isFinal

  dateCreate
  datePublic
  dateModify
  lang
  volume
  serial
  dname
  title
  urlPath

  srcTitle srcColor

  count_images

  stat_count_post_child
  stat_count_post_reply
  stat_count_views_login
  stat_count_views_guest

  userId
  userNode {

  id
  data {

id
name
uniq
avatarUrl
urlPath

verified
deleted
banned

dateCreate
dateOnline

stat_count_chapters_normal
stat_count_chapters_others

is_adm is_mod is_vip is_upr

  }

  }

  disqusId


  }

          sser_read
        }
      }

    }
  }
""",

    "get_content_source_chapterList": """
  query get_content_source_chapterList($sourceId: Int!) {
    get_content_source_chapterList(
      sourceId: $sourceId
    ) {

  id
  data {


  id
  sourceId

  dbStatus
  isNormal
  isHidden
  isDeleted
  isFinal

  dateCreate
  datePublic
  dateModify
  lang
  volume
  serial
  dname
  title
  urlPath

  srcTitle srcColor

  count_images

  stat_count_post_child
  stat_count_post_reply
  stat_count_views_login
  stat_count_views_guest

  userId
  userNode {

  id
  data {

id
name
uniq
avatarUrl
urlPath

verified
deleted
banned

dateCreate
dateOnline

stat_count_chapters_normal
stat_count_chapters_others

is_adm is_mod is_vip is_upr

  }

  }

  disqusId


  }

    }
  }
""",
}
