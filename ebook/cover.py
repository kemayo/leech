
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap
import requests
import logging

logger = logging.getLogger(__name__)


def make_cover(title, author, width=600, height=800, fontname="Helvetica", fontsize=40, bgcolor=(120, 20, 20), textcolor=(255, 255, 255), wrapat=30):
    img = Image.new("RGBA", (width, height), bgcolor)
    draw = ImageDraw.Draw(img)

    title = textwrap.fill(title, wrapat)
    author = textwrap.fill(author, wrapat)

    font = _safe_font(fontname, size=fontsize)
    title_size = textsize(draw, title, font=font)
    draw_text_outlined(draw, ((width - title_size[0]) / 2, 100), title, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    font = _safe_font(fontname, size=fontsize - 2)
    author_size = textsize(draw, author, font=font)
    draw_text_outlined(draw, ((width - author_size[0]) / 2, 100 + title_size[1] + 70), author, textcolor, font=font)

    output = BytesIO()
    img.save(output, "PNG")
    output.name = 'cover.png'
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output


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
        cover = make_cover(title, author)

    return cover


def _convert_to_png(image_bytestream):
    png_image = BytesIO()
    Image.open(image_bytestream).save(png_image, format="PNG")
    png_image.name = 'cover.png'
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


def textsize(draw, text, **kwargs):
    left, top, right, bottom = draw.multiline_textbbox((0, 0), text, **kwargs)
    width, height = right - left, bottom - top
    return width, height


def draw_text_outlined(draw, xy, text, fill=None, font=None, anchor=None):
    x, y = xy

    # Outline
    draw.text((x - 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x + 1, y), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y - 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)
    draw.text((x, y + 1), text=text, fill=(0, 0, 0), font=font, anchor=anchor)

    # Fill
    draw.text(xy, text=text, fill=fill, font=font, anchor=anchor)


if __name__ == '__main__':
    f = make_cover('Test of a Title which is quite long and will require multiple lines', 'Some Dude')
    with open('output.png', 'wb') as out:
        out.write(f.read())
