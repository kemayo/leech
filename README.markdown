Leech
===

Let's say you want to read some sort of fiction. You're a fan of it, perhaps. But mobile websites are kind of non-ideal, so you'd like a proper ebook made from whatever you're reading.

Setup
---

You need Python 3.

My recommended setup process is:

    $ pyvenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

...adjust as needed. Just make sure the dependencies from `requirements.txt` get installed somehow.

Usage
---

    $ python3 leech.py [[URL]]

A new file will appear named `Title of the Story.epub`.

If you want to put it on a Kindle you'll have to convert it. I'd recommend [Calibre](http://calibre-ebook.com/), though you could also try using [kindlegen](http://www.amazon.com/gp/feature.html?docId=1000765211) directly.

Supports
---

 * Fanfiction.net
 * FictionPress
 * ArchiveOfOurOwn
   * Yes, it has its own built-in EPUB export, but the formatting is horrible
 * Various XenForo-based sites: SpaceBattles and SufficientVelocity, most notably
 * DeviantArt galleries/collections
 * Sta.sh

Configuration
---

A very small amount of configuration is possible by creating a file called `leech.json` in the project directory. Currently you can define login information for sites that support it.

Example:

```
{
    "logins": {
        "QuestionableQuesting": ["username", "password"]
    }
}
```

Extending
---

To add support for a new site, create a file in the `sites` directory that implements the `Site` interface. Take a look at `ao3.py` for a minimal example of what you have to do.

Contributing
---

If you submit a pull request to add support for another reasonably-general-purpose site, I will nigh-certainly accept it.

Run [EpubCheck](https://github.com/IDPF/epubcheck) on epubs you generate to make sure they're not breaking.
