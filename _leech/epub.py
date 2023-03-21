"""
So, an epub is approximately a zipfile of HTML files, with
a bit of metadata thrown in for good measure.

This totally started from http://www.manuel-strehl.de/dev/simple_epub_ebooks_with_python.en.html
"""
from __future__ import annotations
import requests
import datetime
import xmltodict
import html
import os.path
from typing import Optional, Union, BinaryIO, List, Dict, Any
import zipfile
import uuid
import string
from dataclasses import dataclass, field
from _leech.cover import Cover
from _leech.story import Story


default_chapter_template = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
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
"""

default_frontmatter_template = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
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
        <dd>{started}</dd>
        <dt>Updated</dt>
        <dd>{updated}</dd>
        <dt>Downloaded on</dt>
        <dd>{now:%Y-%m-%d}</dd>
        {extra}
    </dl>
</div>
</body>
</html>
"""

default_cover_template = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
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
"""


@dataclass
class EpubFile:
    id: str
    path: str
    contents: Union[str, bytes]
    title: Optional[str] = None
    filetype: str = "application/xhtml+xml"


def sanitize_filename(s):
    """Take a string and return a valid filename constructed from the string.
    Uses a whitelist approach: any characters not present in valid_chars are
    removed. Also spaces are replaced with underscores.

    Note: this method may produce invalid filenames such as ``, `.` or `..`
    When I use this method I prepend a date string like '2009_01_15_19_46_32_'
    and append a file extension like '.txt', so I avoid the potential of using
    an invalid filename.

    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = "".join(c for c in s if c in valid_chars)
    filename = filename.replace(" ", "_")  # I don't like spaces in filenames.
    return filename


@dataclass
class Epub:
    title: str
    cover: EpubFile
    cover_image: EpubFile
    frontmatter: EpubFile
    chapters: List[EpubFile]
    footnotes: EpubFile
    style: EpubFile
    meta: Dict

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    frontmatter_template: str = default_frontmatter_template
    cover_template: str = default_cover_template
    chapter_template: str = default_chapter_template

    mimetype_filename = "mimetype"
    container_xml_filename = "META-INF/container.xml"
    toc_ncx_filename = "OEBPS/toc.ncx"
    content_opf_filename = "OEBPS/Content.opf"

    @classmethod
    def from_story(
        cls,
        story: Story,
        normalize: bool = False,
        cover_options: Optional[dict[str, Any]] = None,
    ) -> Epub:
        cover = Cover.from_options(cover_options)
        metadata = story.metadata
        return cls(
            title=story.title,
            id=metadata.get("unique_id"),
            cover=EpubFile(
                id="cover_html",
                title="Cover",
                path="cover.html",
                contents=cls.cover_template,
            ),
            cover_image=EpubFile(
                id="cover_image",
                path="images/cover.png",
                contents=cover.generate_image(story),
                filetype="image/png",
            ),
            footnotes=EpubFile(
                id="footnotes",
                title="Footnotes",
                path="chapter/footnotes.html",
                contents=cls.chapter_template.format(
                    title="Footnotes",
                    text="\n\n".join(story.footnotes),
                ),
            ),
            frontmatter=EpubFile(
                id="frontmatter",
                title="Front Matter",
                path="frontmatter.html",
                contents=cls.frontmatter_template.format(
                    now=datetime.datetime.now(),
                    **metadata,
                ),
            ),
            style=EpubFile(
                id="style",
                path="Styles/base.css",
                contents=requests.Session()
                .get(
                    "https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css"
                )
                .text,
                filetype="text/css",
            ),
            chapters=[
                EpubFile(
                    id=f"chapter_{chapter.number}",
                    title=chapter.get_title(normalize=normalize),
                    path=f"chapter/{chapter.number}.html",
                    contents=cls.chapter_template.format(
                        title=html.escape(chapter.get_title(normalize=normalize)),
                        text=chapter.get_content(normalize=normalize),
                    ),
                )
                for chapter in story.chapters
            ],
            meta=metadata,
        )

    def write(
        self,
        output_file: Union[str, BinaryIO, None] = None,
        *,
        load_from: Optional[str] = None,
        output_dir: Optional[str] = None,
        compress: bool = True,
    ):
        if output_file is None:
            output_file = self.title + ".epub"

        if isinstance(output_file, str):
            output_file = sanitize_filename(output_file)

            if output_dir:
                output_file = os.path.join(output_dir, output_file)

        from_zf = None
        if load_from:
            from_zf = zipfile.ZipFile(
                load_from,
                "r",
                compression=compress and zipfile.ZIP_DEFLATED or zipfile.ZIP_STORED,
            )

        to_zf = zipfile.ZipFile(
            output_file,
            "w",
            compression=compress and zipfile.ZIP_DEFLATED or zipfile.ZIP_STORED,
        )

        id = self.meta.get("identifier", self.id)
        title = self.meta.get("title", "Untitled")
        author = self.meta.get("author", "Unknown")

        self.write_mimetype(to_zf, from_zf=from_zf)
        self.write_container(to_zf, from_zf=from_zf)
        self.write_toc_ncx(to_zf, id, title, author, from_zf=from_zf)
        self.write_content_opf(to_zf, id, title, author, from_zf=from_zf)

        content_files = [
            self.cover,
            self.cover_image,
            self.frontmatter,
            self.footnotes,
            self.style,
            *self.chapters,
        ]
        for file in content_files:
            to_zf.writestr("OEBPS/" + file.path, file.contents)

        self.replicate_other_files(to_zf, from_zf)

        return to_zf.filename

    def write_mimetype(
        self, zf: zipfile.ZipFile, *, from_zf: Optional[zipfile.ZipFile] = None
    ):
        """The first file must be named "mimetype", and shouldn't be compressed."""
        write_content(
            zf,
            self.mimetype_filename,
            content="application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
            from_zf=from_zf,
        )

    def write_container(
        self, zf: zipfile.ZipFile, *, from_zf: Optional[zipfile.ZipFile] = None
    ):
        """We need an index file, that lists all other HTML files.

        This index file itself is referenced in the META_INF/container.xml file.
        """
        container_xml = {
            "container": {
                "@version": "1.0",
                "@xmlns": "urn:oasis:names:tc:opendocument:xmlns:container",
                "rootfiles": {
                    "rootfile": {
                        "@full-path": self.content_opf_filename,
                        "@media-type": "application/oebps-package+xml",
                    }
                },
            }
        }
        write_content(
            zf,
            self.container_xml_filename,
            content=container_xml,
            compress_type=zipfile.ZIP_STORED,
            from_zf=from_zf,
        )

    def write_toc_ncx(
        self,
        zf: zipfile.ZipFile,
        id: str,
        title: str,
        author: str,
        *,
        from_zf: Optional[zipfile.ZipFile] = None,
    ):
        toc_ncx = {
            "ncx": {
                "@xlmns": "http://www.daisy.org/z3986/2005/ncx/",
                "@version": "2005-1",
                "@xml:lang": "en-US",
                "head": {
                    "meta": {
                        "@name": "dtb:uid",
                        "@content": id,
                    },
                },
                "docTitle": {"text": title},
                "docAuthor": {"text": author},
                "navMap": {
                    "navPoint": [
                        {
                            "@class": "h1",
                            "@id": file.id,
                            "navLabel": {"text": file.title},
                            "content": {"@src": file.path},
                        }
                        for file in [
                            self.cover,
                            self.frontmatter,
                            *self.chapters,
                            self.footnotes,
                        ]
                    ]
                },
            }
        }
        write_content(
            zf,
            self.toc_ncx_filename,
            content=toc_ncx,
            from_zf=from_zf,
        )

    def write_content_opf(
        self,
        zf: zipfile.ZipFile,
        id: str,
        title: str,
        author: str,
        from_zf: Optional[zipfile.ZipFile] = None,
    ):
        chapters = [
            {
                "@id": file.id,
                "@href": file.path,
                "@media-type": "application/xhtml+xml",
            }
            for file in self.chapters
        ]
        spine_items = [{"@idref": file.id} for file in self.chapters]

        content_opf = {
            "package": {
                "@version": "2.0",
                "@xmlns": "http://www.idpf.org/2007/opf",
                "@unique-identifier": "book_identifier",
                "metadata": {
                    "@xmlns:dc": "http://purl.org/dc/elements/1.1/",
                    "@xmlns:opf": "http://www.idpf.org/2007/opf",
                    "dc:identifier": {
                        "@id": "book_identifier",
                        "#text": id,
                    },
                    "dc:title": title,
                    "dc:language": "en",
                    "dc:creator": {"@opf:role": "aut", "#text": author},
                    "meta": [
                        {"@name": "generator", "@content": "leech"},
                        {"@name": "cover", "@content": "cover_image"},
                    ],
                },
                "manifest": {
                    "item": [
                        {
                            "@id": "cover_html",
                            "@href": "cover.html",
                            "@media-type": "application/xhtml+xml",
                        },
                        {
                            "@id": "cover_image",
                            "@href": "images/cover.png",
                            "@media-type": "image/png",
                        },
                        *chapters,
                        {
                            "@id": "footnotes",
                            "@href": "footnotes.html",
                            "@media-type": "application/xhtml+xml",
                        },
                        {
                            "@id": "frontmatter",
                            "@href": "frontmatter.html",
                            "@media-type": "application/xhtml+xml",
                        },
                        {
                            "@id": "style",
                            "@href": "Styles/base.css",
                            "@media-type": "text/css",
                        },
                        {
                            "@id": "ncx",
                            "@href": "toc.ncx",
                            "@media-type": "application/x-dtbncx+xml",
                        },
                    ]
                },
                "spine": {
                    "@toc": "ncx",
                    "itemref": [
                        {"@idref": "cover_html", "@linear": "no"},
                        *spine_items,
                    ],
                },
                "guide": {
                    "reference": {
                        "@type": "cover",
                        "@title": "Cover",
                        "@href": "cover.html",
                    }
                },
            }
        }
        write_content(
            zf,
            self.content_opf_filename,
            content=content_opf,
            from_zf=from_zf,
        )

    def replicate_other_files(
        self, zf: zipfile.ZipFile, from_zf: Optional[zipfile.ZipFile] = None
    ):
        """Add files from the `from_zf` to the destination oneself.

        Updating an existing zipfile in-place isn't supported. So we need to copy
        over any other files.
        """
        if from_zf is None:
            return

        files = set(zf.namelist())
        from_files = set(from_zf.namelist())
        missing_files = from_files - files
        for missing_file in missing_files:
            zf.writestr(missing_file, from_zf.read(missing_file))


def write_content(
    zf: zipfile.ZipFile,
    filename: str,
    *,
    content: Union[str, dict],
    compress_type=None,
    from_zf: Optional[zipfile.ZipFile] = None,
    full_document: bool = True,
):
    # existing_content_str = None
    # if from_zf:
    #     existing_content_str = from_zf.read(filename)

    if isinstance(content, str):
        zf.writestr(filename, content, compress_type=compress_type)

    elif isinstance(content, dict):
        # existing_content = xmltodict.parse(existing_content_str)

        content_str = xmltodict.unparse(
            content, pretty=True, indent="  ", full_document=full_document
        )

        zf.writestr(filename, content_str, compress_type=compress_type)
