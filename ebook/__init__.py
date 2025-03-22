from .epub import make_epub, EpubFile
from .cover import make_cover, make_cover_from_url
from .image import get_image_from_url

import html
import unicodedata
import datetime
from attrs import define, asdict

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


@define
class CoverOptions:
    fontname: str = None
    fontsize: int = None
    width: int = None
    height: int = None
    wrapat: int = None
    bgcolor: tuple = None
    textcolor: tuple = None
    cover_url: str = None


@define
class ImageOptions:
    image_fetch: bool = False
    image_format: str = "JPEG"
    always_convert_images: bool = False
    compress_images: bool = False
    max_image_size: int = 1_000_000


def chapter_html(
    story,
    image_options,
    titleprefix=None,
    normalize=False,
    session=None
):
    images = {}
    chapters = []
    for i, chapter in enumerate(story):
        title = chapter.title or f'#{i}'
        if hasattr(chapter, '__iter__'):
            # This is a Section
            chapters.extend(chapter_html(
                chapter, image_options=image_options, titleprefix=title, normalize=normalize, session=session
            ))
        else:
            contents = chapter.contents
            images.update(chapter.images)

            title = titleprefix and f'{titleprefix}: {title}' or title
            if normalize:
                title = unicodedata.normalize('NFKC', title)
                contents = unicodedata.normalize('NFKC', contents)
            chapters.append(EpubFile(
                title=title,
                path=f'{story.id}/chapter{i + 1}.html',
                contents=html_template.format(
                    title=html.escape(title), text=contents)
            ))

    if story.footnotes:
        chapters.append(EpubFile(title="Footnotes", path=f'{story.id}/footnotes.html', contents=html_template.format(
            title="Footnotes", text=story.footnotes.contents)))
        images.update(story.footnotes.images)

    for image in images.values():
        img_contents = get_image_from_url(
            image.url,
            image_format=image_options.get('image_format'),
            compress_images=image_options.get('compress_images'),
            max_image_size=image_options.get('max_image_size'),
            always_convert=image_options.get('always_convert_images'),
            session=session
        )
        path = f'{story.id}/{image.path()}'
        for chapterfile in chapters:
            if chapterfile.path == path:
                break
        else:
            chapters.append(
                EpubFile(path=path, contents=img_contents[0], filetype=img_contents[2])
            )

    return chapters


def generate_epub(story, cover_options={}, image_options={}, output_filename=None, output_dir=None, normalize=False, allow_spaces=False, session=None, parser='lxml'):
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

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
    })
    if story.url:
        session.headers.update({
            'Referer': story.url,
        })

    if story.summary:
        extra_metadata['Summary'] = story.summary
    if story.tags:
        extra_metadata['Tags'] = ', '.join(story.tags)

    if extra_metadata:
        metadata['extra'] = '\n        '.join(
            f'<dt>{k}</dt><dd>{v}</dd>' for k, v in extra_metadata.items())

    valid_image_options = ('image_fetch', 'image_format', 'compress_images',
                           'max_image_size', 'always_convert_images')
    image_options = ImageOptions(
        **{k: v for k, v in image_options.items() if k in valid_image_options})
    image_options = asdict(image_options, filter=lambda k, v: v is not None)

    valid_cover_options = ('fontname', 'fontsize', 'width',
                           'height', 'wrapat', 'bgcolor', 'textcolor', 'cover_url')
    cover_options = CoverOptions(
        **{k: v for k, v in cover_options.items() if k in valid_cover_options})
    cover_options = asdict(cover_options, filter=lambda k, v: v is not None)

    if cover_options and "cover_url" in cover_options:
        image = make_cover_from_url(
            cover_options["cover_url"], story.title, story.author)
    elif story.cover_url:
        image = make_cover_from_url(story.cover_url, story.title, story.author)
    else:
        image = make_cover(story.title, story.author, **cover_options)

    return make_epub(
        output_filename or story.title + '.epub',
        [
            # The cover is static, and the only change comes from the image which we generate
            EpubFile(title='Cover', path='cover.html', contents=cover_template),
            EpubFile(title='Front Matter', path='frontmatter.html', contents=frontmatter_template.format(
                now=datetime.datetime.now(), **metadata)),
            *chapter_html(
                story,
                image_options=image_options,
                normalize=normalize,
                session=session
            ),
            EpubFile(
                path='Styles/base.css',
                contents=session.get(
                    'https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css').text,
                filetype='text/css'
            ),
            EpubFile(path='images/cover.png',
                     contents=image.read(), filetype='image/png'),
        ],
        metadata,
        output_dir=output_dir,
        allow_spaces=allow_spaces
    )
