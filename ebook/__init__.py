from .epub import make_epub, EpubFile
from .cover import make_cover, make_cover_from_url
from .image import get_image_from_url
from sites import Image
from bs4 import BeautifulSoup

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
    textcolor = attr.ib(
        default=None, converter=attr.converters.optional(tuple))
    cover_url = attr.ib(default=None, converter=attr.converters.optional(str))


def chapter_html(
    story,
    image_fetch=False,
    image_format="JPEG",
    compress_images=False,
    max_image_size=1_000_000,
    titleprefix=None,
    normalize=False
):
    chapters = []
    for i, chapter in enumerate(story):
        title = chapter.title or f'#{i}'
        if hasattr(chapter, '__iter__'):
            # This is a Section
            chapters.extend(chapter_html(
                chapter, titleprefix=title, normalize=normalize))
        else:
            soup = BeautifulSoup(chapter.contents, 'html5lib')
            if image_fetch:
                all_images = soup.find_all('img', src=True)
                len_of_all_images = len(all_images)
                # print(f"Found {len_of_all_images} images in chapter {i}")

                for count, img in enumerate(all_images):
                    print(f"[{chapter.title}] Image ({count+1} out of {len_of_all_images}). Source: ", end="")
                    img_contents = get_image_from_url(img['src'], image_format, compress_images, max_image_size)
                    chapter.images.append(Image(
                        path=f"images/ch{i}_leechimage_{count}.{img_contents[1]}",
                        contents=img_contents[0],
                        content_type=img_contents[2]
                    ))
                    img['src'] = f"../images/ch{i}_leechimage_{count}.{img_contents[1]}"
                    if not img.has_attr('alt'):
                        img['alt'] = f"Image {count} from chapter {i}"
                # Add all pictures on this chapter as well.
                for image in chapter.images:
                    # For/else syntax, check if the image path already exists, if it doesn't add the image.
                    # Duplicates are not allowed in the format.
                    for other_file in chapters:
                        if other_file.path == image.path:
                            break
                    else:
                        chapters.append(EpubFile(
                            path=image.path, contents=image.contents, filetype=image.content_type))
            else:
                # Remove all images from the chapter so you don't get that annoying grey background.
                for img in soup.find_all('img'):
                    if img.parent.name.lower() == "figure":
                        img.parent.decompose()
                    else:
                        img.decompose()

            title = titleprefix and f'{titleprefix}: {title}' or title
            contents = str(soup)
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
            title="Footnotes", text='\n\n'.join(story.footnotes))))
    return chapters


def generate_epub(story, cover_options={}, image_options=None,  output_filename=None, output_dir=None, normalize=False):
    if image_options is None:
        image_options = {
            'image_fetch': False,
            'image_format': 'JPEG',
            'compress_images': False,
            'max_image_size': 1_000_000
        }
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
        metadata['extra'] = '\n        '.join(
            f'<dt>{k}</dt><dd>{v}</dd>' for k, v in extra_metadata.items())

    valid_cover_options = ('fontname', 'fontsize', 'width',
                           'height', 'wrapat', 'bgcolor', 'textcolor', 'cover_url')
    cover_options = CoverOptions(
        **{k: v for k, v in cover_options.items() if k in valid_cover_options})
    cover_options = attr.asdict(
        cover_options, filter=lambda k, v: v is not None, retain_collection_types=True)

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
                image_fetch=image_options.get('image_fetch'),
                image_format=image_options.get('image_format'),
                compress_images=image_options.get('compress_images'),
                max_image_size=image_options.get('max_image_size'),
                normalize=normalize
            ),
            EpubFile(
                path='Styles/base.css',
                contents=requests.Session().get(
                    'https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css').text,
                filetype='text/css'
            ),
            EpubFile(path='images/cover.png',
                     contents=image.read(), filetype='image/png'),
        ],
        metadata,
        output_dir=output_dir
    )
