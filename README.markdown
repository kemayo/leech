Leech
===

Let's say you want to read some sort of fiction. You're a fan of it, perhaps. But mobile websites are kind of non-ideal, so you'd like a proper ebook made from whatever you're reading.

Setup
---

You'll need python3, BeautifulSoup, and html5lib. If you don't have them, this will make them show up:

    $ pip install -r requirements.txt

Usage
---

    $ python3 leech.py [[URL]]

A new file will appear named `Title of the Story.epub`.

If you want to put it on a Kindle you'll have to convert it. I'd recommend [Calibre](http://calibre-ebook.com/), though you could also try using [kindlegen](http://www.amazon.com/gp/feature.html?docId=1000765211) directly.

Supports
---

 * Fanfiction.net
 * Sta.sh
 * DeviantArt galleries/collections

Contributing
---

If you submit a pull request to add support for another site, I will nigh-certainly accept it.

Run [EpubCheck](https://github.com/IDPF/epubcheck) on epubs you generate to make sure they're not breaking.
