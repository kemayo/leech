from .epub import make_epub, EpubFile
from .cover import make_cover
from .cover import make_cover_from_url

import html
import unicodedata
import datetime
import requests
import attr

html_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="../Styles/base.css" />
</head>
<body>
<h1>{title}</h1>
{text}
</body>
</html>
'''

cover_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover">
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="100%" height="100%" viewBox="0 0 573 800" preserveAspectRatio="xMidYMid meet">
<image width="600" height="800" xlink:href="images/cover.png" />
</svg>
</div>
</body>
</html>
'''

frontmatter_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Front Matter</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover title">
    <h1>{title}<br />By {author}</h1>
    <dl>
        <dt>Source</dt>
        <dd>{unique_id}</dd>
        <dt>Started</dt>
        <dd>{started:%Y-%m-%d}</dd>
        <dt>Updated</dt>
        <dd>{updated:%Y-%m-%d}</dd>
        <dt>Downloaded on</dt>
        <dd>{now:%Y-%m-%d}</dd>
        {extra}
    </dl>
</div>
</body>
</html>
'''


@attr.s
class CoverOptions:
    fontname = attr.ib(default=None, converter=attr.converters.optional(str))
    fontsize = attr.ib(default=None, converter=attr.converters.optional(int))
    width = attr.ib(default=None, converter=attr.converters.optional(int))
    height = attr.ib(default=None, converter=attr.converters.optional(int))
    wrapat = attr.ib(default=None, converter=attr.converters.optional(int))
    bgcolor = attr.ib(default=None, converter=attr.converters.optional(tuple))
    textcolor = attr.ib(default=None, converter=attr.converters.optional(tuple))
    cover_url = attr.ib(default=None, converter=attr.converters.optional(str))


def chapter_html(story, titleprefix=None, normalize=False):
    chapters = []
    for i, chapter in enumerate(story):
        title = chapter.title or f'#{i}'
        if hasattr(chapter, '__iter__'):
            # This is a Section
            chapters.extend(chapter_html(chapter, titleprefix=title, normalize=normalize))
        else:
            title = titleprefix and f'{titleprefix}: {title}' or title
            contents = chapter.contents
            if normalize:
                title = unicodedata.normalize('NFKC', title)
                contents = unicodedata.normalize('NFKC', contents)
            chapters.append(EpubFile(
                title=title,
                path=f'{story.id}/chapter{i + 1}.html',
                contents=html_template.format(title=html.escape(title), text=contents)
            ))
    if story.footnotes:
        chapters.append(EpubFile(title="Footnotes", path=f'{story.id}/footnotes.html', contents=html_template.format(title="Footnotes", text='\n\n'.join(story.footnotes))))
    return chapters


def generate_epub(story, cover_options={}, output_filename=None, normalize=False):
    dates = list(story.dates())
    metadata = {
        'title': story.title,
        'author': story.author,
        'unique_id': story.url,
        'started': min(dates),
        'updated': max(dates),
        'extra': '',
    }
    extra_metadata = {}

    if story.summary:
        extra_metadata['Summary'] = story.summary
    if story.tags:
        extra_metadata['Tags'] = ', '.join(story.tags)

    if extra_metadata:
        metadata['extra'] = '\n        '.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in extra_metadata.items())

    valid_cover_options = ('fontname', 'fontsize', 'width', 'height', 'wrapat', 'bgcolor', 'textcolor', 'cover_url')
    cover_options = CoverOptions(**{k: v for k, v in cover_options.items() if k in valid_cover_options})
    cover_options = attr.asdict(cover_options, filter=lambda k, v: v is not None, retain_collection_types=True)

    # The cover is static, and the only change comes from the image which we generate
    files = [EpubFile(title='Cover', path='cover.html', contents=cover_template)]

    if cover_options and "cover_url" in cover_options:
        image = make_cover_from_url(cover_options["cover_url"], story.title, story.author)
    elif story.cover_url:
        image = make_cover_from_url(story.cover_url, story.title, story.author)
    else:
        image = make_cover(story.title, story.author, **cover_options)

    cover_image = EpubFile(path='images/cover.png', contents=image.read(), filetype='image/png')

    files.append(EpubFile(title='Front Matter', path='frontmatter.html', contents=frontmatter_template.format(now=datetime.datetime.now(), **metadata)))

    files.extend(chapter_html(story, normalize=normalize))

    css = EpubFile(path='Styles/base.css', contents=requests.Session().get('https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css').text, filetype='text/css')

    files.extend((css, cover_image))

    output_filename = output_filename or story.title + '.epub'

    output_filename = make_epub(output_filename, files, metadata)

    return output_filename
