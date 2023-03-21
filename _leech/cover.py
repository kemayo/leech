from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap
import requests
import logging
from dataclasses import dataclass, fields, asdict

if TYPE_CHECKING:
    from _leech.story import Story


@dataclass
class Cover:
    fontname: Optional[str] = None
    fontsize: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    wrapat: Optional[int] = None
    bgcolor: Optional[tuple] = None
    textcolor: Optional[tuple] = None
    cover_url: Optional[str] = None

    @classmethod
    def from_options(cls, options: Optional[dict[str, Any]] = None):
        if options is None:
            return cls()

        return cls(
            **{
                field.name: options[field.name]
                for field in fields(cls)
                if field.name in options
            }
        )

    @classmethod
    def default(cls):
        return cls()

    def generate_image(self, story: Story):
        if self.cover_url:
            return make_cover_from_url(self.cover_url, story.title, story.author)
        elif story.cover_url:
            return make_cover_from_url(story.cover_url, story.title, story.author)

        return make_cover_image(story.title, story.author, **asdict(self))


logger = logging.getLogger(__name__)


def make_cover_image(
    title,
    author,
    width=600,
    height=800,
    fontname="Helvetica",
    fontsize=40,
    bgcolor=(120, 20, 20),
    textcolor=(255, 255, 255),
    wrapat=30,
):
    img = Image.new("RGBA", (width, height), bgcolor)
    draw = ImageDraw.Draw(img)

    title = textwrap.fill(title, wrapat)
    author = textwrap.fill(author, wrapat)

    font = _safe_font(fontname, size=fontsize)
    title_size = draw.textsize(title, font=font)
    draw_text_outlined(
        draw, ((width - title_size[0]) / 2, 100), title, textcolor, font=font
    )
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    font = _safe_font(fontname, size=fontsize - 2)
    author_size = draw.textsize(author, font=font)
    draw_text_outlined(
        draw,
        ((width - author_size[0]) / 2, 100 + title_size[1] + 70),
        author,
        textcolor,
        font=font,
    )

    output = BytesIO()
    img.save(output, "PNG")
    output.name = "cover.png"
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output.read()


def make_cover_from_url(url, title, author):
    try:
        logger.info("Downloading cover from " + url)
        img = requests.Session().get(url)
        cover = BytesIO(img.content)

        imgformat = Image.open(cover).format
        # The `Image.open` read a few bytes from the stream to work out the
        # format, so reset it:
        cover.seek(0)

        if imgformat != "PNG":
            cover = _convert_to_png(cover)
    except Exception as e:
        logger.info("Encountered an error downloading cover: " + str(e))
        cover = make_cover_image(title, author)

    return cover.read()


def _convert_to_png(image_bytestream):
    png_image = BytesIO()
    Image.open(image_bytestream).save(png_image, format="PNG")
    png_image.name = "cover.png"
    png_image.seek(0)

    return png_image


def _safe_font(preferred, *args, **kwargs):
    for font in (preferred, "Helvetica", "FreeSans", "Arial"):
        try:
            return ImageFont.truetype(*args, font=font, **kwargs)
        except IOError:
            pass

    # This is pretty terrible, but it'll work regardless of what fonts the
    # system has. Worst issue: can't set the size.
    return ImageFont.load_default()


def draw_text_outlined(draw, xy, text, fill=None, font=None, anchor=None):
    x, y = xy

    # Outline
    draw.text((x - 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x + 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y - 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y + 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)

    # Fill
    draw.text(xy, text=text, fill=fill, font=font, anchor=anchor)


if __name__ == "__main__":
    f = make_cover_image(
        "Test of a Title which is quite long and will require multiple lines",
        "Some Dude",
    )
    with open("output.png", "wb") as out:
        out.write(f)
