#!/usr/bin/python

import sqlite3
import http.cookiejar

import requests

__version__ = 1
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__


class Fetch:
    """A store for values by date, sqlite-backed"""

    def __init__(self, storepath, cachetime="+1 day"):
        """Initializes the store; creates tables if required

        storepath is the path to a sqlite database, and will be created
        if it doesn't already exist. (":memory:" will store everything
        in-memory, if you only need to use this as a temporary thing).
        """
        store = sqlite3.connect(storepath + '.db')
        self.store = store
        c = store.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS cache (url TEXT, content BLOB, time TEXT, PRIMARY KEY (url))""")
        self.store.commit()
        c.close()

        self.cachetime = cachetime

        lwp_cookiejar = http.cookiejar.LWPCookieJar()
        try:
            lwp_cookiejar.load(storepath + '.cookies', ignore_discard=True)
        except Exception as e:
            pass

        self.session = requests.Session()
        self.session.cookies = lwp_cookiejar
        self.session.headers.update({
            'User-agent': USER_AGENT
        })

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
        data = self.session.get(url, **kw)
        self.__set(url, data.text)
        return data.text

    def __set(self, url, value):
        """Add a value to the store, at the current time

        url is a string that the value will be associated with
        value is the value to be stored
        """
        c = self.store.cursor()
        c.execute("""REPLACE INTO cache VALUES (?, ?, CURRENT_TIMESTAMP)""", (url, value,))
        self.store.commit()
        c.close()

    def flush(self, cachetime="-7 days"):
        c = self.store.execute("""DELETE FROM cache WHERE time < datetime('now', ?)""", (cachetime,))
        self.store.commit()
        self.store.execute("""VACUUM""")
        return c.rowcount
