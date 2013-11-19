#!/usr/bin/python

import gzip
import sqlite3

from io import BytesIO
from urllib.request import Request, urlopen

__version__ = 1
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__

class Fetch:
    """A store for values by date, sqlite-backed"""

    def __init__(self, storepath, cachetime = "+1 day"):
        """Initializes the store; creates tables if required

        storepath is the path to a sqlite database, and will be created
        if it doesn't already exist. (":memory:" will store everything
        in-memory, if you only need to use this as a temporary thing).
        """
        store = sqlite3.connect(storepath)
        self.store = store
        c = store.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS cache (url TEXT, content BLOB, time TEXT, PRIMARY KEY (url))""")
        self.store.commit()
        c.close()

        self.cachetime = cachetime

    def __call__(self, url, **kw):
        return self.get(url, **kw)

    def get(self, url, cached=True, **kw):
        """Fetch a given url's data

        type is a string to fetch all associated values for
        """
        if cached:
            c = self.store.cursor()
            c.execute("""SELECT content FROM cache WHERE url = ? AND datetime(time, ?) > datetime('now')""", (url, self.cachetime))
            row = c.fetchone()
            c.close()
            if row:
                return row[0]
        data = _fetch(url, **kw)
        self.__set(url, data)
        return data

    def __set(self, url, value):
        """Add a value to the store, at the current time

        url is a string that the value will be associated with
        value is the value to be stored
        """
        c = self.store.cursor()
        c.execute("""REPLACE INTO cache VALUES (?, ?, CURRENT_TIMESTAMP)""", (url, value,))
        self.store.commit()
        c.close()

def _fetch(url, data=None, ungzip=True):
    """A generic URL-fetcher, which handles gzipped content, returns a string"""
    request = Request(url)
    request.add_header('Accept-encoding', 'gzip')
    request.add_header('User-agent', USER_AGENT)
    try:
        f = urlopen(request, data)
    except Exception as e:
        return None
    data = f.read()
    if ungzip and f.headers.get('content-encoding', '') == 'gzip':
        data = gzip.GzipFile(fileobj=BytesIO(data), mode='r').read()
        try:
            data = data.decode()
        except UnicodeDecodeError:
            data = data.decode('latin1')
    f.close()
    return data