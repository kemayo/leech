
from PIL import Image, ImageDraw
from io import BytesIO
import textwrap
import requests
import logging
from . import image

logger = logging.getLogger(__name__)


def make_cover(title, author, width=600, height=800, fontname="Helvetica", fontsize=40, bgcolor=(120, 20, 20), textcolor=(255, 255, 255), wrapat=30):
    img = Image.new("RGBA", (width, height), bgcolor)
    draw = ImageDraw.Draw(img)

    title = textwrap.fill(title, wrapat)
    author = textwrap.fill(author, wrapat)

    font = image._safe_font(fontname, size=fontsize)
    title_size = image.textsize(draw, title, font=font)
    image.draw_text_outlined(draw, ((width - title_size[0]) / 2, 100), title, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    font = image._safe_font(fontname, size=fontsize - 2)
    author_size = image.textsize(draw, author, font=font)
    image.draw_text_outlined(draw, ((width - author_size[0]) / 2, 100 + title_size[1] + 70), author, textcolor, font=font)

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
            cover = image._convert_to_new_format(cover, "PNG")
    except Exception as e:
        logger.info("Encountered an error downloading cover: " + str(e))
        cover = make_cover(title, author)

    return cover


if __name__ == '__main__':
    f = make_cover('Test of a Title which is quite long and will require multiple lines', 'Some Dude')
    with open('output.png', 'wb') as out:
        out.write(f.read())
