Leech
===

Let's say you want to read some sort of fiction. You're a fan of it, perhaps. But mobile websites are kind of non-ideal, so you'd like a proper ebook made from whatever you're reading.

Usage
---

You'll need python3 and BeautifulSoup.

    $ python3 leech.py [[URL]]

A new file will appear named `Title of the Story.epub`.

If you want to put it on a Kindle you'll have to convert it. I'd recommend [Calibre](http://calibre-ebook.com/), though you could also try using [kindlegen](http://www.amazon.com/gp/feature.html?docId=1000765211) directly.

Supports
---

 * Fanfiction.net

Contributing
---

If you submit a pull request to add support for another site, I will nigh-certainly accept it.