Leech
===

Let's say you want to read some sort of fiction. You're a fan of it, perhaps. But mobile websites are kind of non-ideal, so you'd like a proper ebook made from whatever you're reading.

Setup
---

You need Python 3.7+ and poetry.

My recommended setup process is:

    $ pip install poetry
    $ poetry install
    $ poetry shell

...adjust as needed. Just make sure the dependencies from `pyproject.toml` get installed somehow.

Usage
---

Basic

    $ python3 leech.py [[URL]]

A new file will appear named `Title of the Story.epub`.

This is equivalent to the slightly longer

    $ python3 leech.py download [[URL]]

Flushing the cache

    $ python3 leech.py flush

If you want to put it on a Kindle you'll have to convert it. I'd recommend [Calibre](http://calibre-ebook.com/), though you could also try using [kindlegen](http://www.amazon.com/gp/feature.html?docId=1000765211) directly.

Supports
---

 * Fanfiction.net
 * FictionPress
 * ArchiveOfOurOwn
   * Yes, it has its own built-in EPUB export, but the formatting is horrible
 * Various XenForo-based sites: SpaceBattles and SufficientVelocity, most notably
 * RoyalRoad
 * Fiction.live (Anonkun)
 * DeviantArt galleries/collections
 * Sta.sh
 * Completely arbitrary sites, with a bit more work (see below)

Configuration
---

A very small amount of configuration is possible by creating a file called `leech.json` in the project directory. Currently you can define login information for sites that support it, and some options for book covers.

Example:

```
{
    "logins": {
        "QuestionableQuesting": ["username", "password"]
    },
    "cover": {
        "fontname": "Comic Sans MS",
        "fontsize": 30,
        "bgcolor": [20, 120, 20],
        "textcolor": [180, 20, 180],
        "cover_url": "https://website.com/image.png"
    },
    "output_dir": "/tmp/ebooks",
    "site_options": {
        "RoyalRoad": {
            "output_dir": "/tmp/litrpg_isekai_trash"
        }
    }
}
```

Arbitrary Sites
---

If you want to just download a one-off story from a site, you can create a definition file to describe it. This requires investigation and understanding of things like CSS selectors, which may take some trial and error.

Example `practical.json`:

```
{
    "url": "https://practicalguidetoevil.wordpress.com/table-of-contents/",
    "title": "A Practical Guide To Evil: Book 1",
    "author": "erraticerrata",
    "chapter_selector": "#main .entry-content > ul:nth-of-type(1) > li > a",
    "content_selector": "#main .entry-content",
    "filter_selector": ".sharedaddy, .wpcnt, style",
    "cover_url": "https://gitlab.com/Mikescher2/A-Practical-Guide-To-Evil-Lyx/raw/master/APGTE_1/APGTE_front.png"
}
```

Run as:

    $ ./leech.py practical.json

This tells leech to load `url`, follow the links described by `chapter_selector`, extract the content from those pages as described by `content_selector`, and remove any content from *that* which matches `filter_selector`. Optionally, `cover_url` will replace the default cover with the image of your choice.

If `chapter_selector` isn't given, it'll create a single-chapter book by applying `content_selector` to `url`.

This is a fairly viable way to extract a story from, say, a random Wordpress installation with a convenient table of contents. It's relatively likely to get you at least *most* of the way to the ebook you want, with maybe some manual editing needed.

A more advanced example with JSON would be:

```
{
    "url": "https://practicalguidetoevil.wordpress.com/2015/03/25/prologue/",
    "title": "A Practical Guide To Evil: Book 1",
    "author": "erraticerrata",
    "content_selector": "#main .entry-wrapper",
    "content_title_selector": "h1.entry-title",
    "content_text_selector": ".entry-content",
    "filter_selector": ".sharedaddy, .wpcnt, style",
    "next_selector": "a[rel=\"next\"]:not([href*=\"prologue\"])",
    "cover_url": "https://gitlab.com/Mikescher2/A-Practical-Guide-To-Evil-Lyx/raw/master/APGTE_1/APGTE_front.png"
}
```

Because there's no `chapter_selector` here, leech will keep on looking for a link which it can find with `next_selector` and following that link. We also see more advanced metadata acquisition here, with `content_title_selector` and `content_text_selector` being used to find specific elements from within the content.

If multiple matches for `content_selector` are found, leech will assume multiple chapters are present on one page, and will handle that. If you find a story that you want on a site which has all the chapters in the right order and next-page links, this is a notably efficient way to download it. See `examples/dungeonkeeperami.json` for this being used.

If you need more advanced behavior, consider looking at...

Adding new site handers
---

To add support for a new site, create a file in the `sites` directory that implements the `Site` interface. Take a look at `ao3.py` for a minimal example of what you have to do.

Docker
---

You can build the project's Docker container like this:

```shell
docker build . -t kemayo/leech:snapshot
```

The container's entrypoint runs `leech` directly and sets the current working directory to `/work`, so you can mount any directory there:

```shell
docker run -it --rm -v ${DIR}:/work kemayo/leech:snapshot download [[URL]]
```

Contributing
---

If you submit a pull request to add support for another reasonably-general-purpose site, I will nigh-certainly accept it.

Run [EpubCheck](https://github.com/IDPF/epubcheck) on epubs you generate to make sure they're not breaking.
