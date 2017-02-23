
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap


def make_cover(title, author, width=600, height=800, fontname="Helvetica", fontsize=40, bgcolor=(120, 20, 20), textcolor=(255, 255, 255), wrapat=30):
    img = Image.new("RGBA", (width, height), bgcolor)
    draw = ImageDraw.Draw(img)

    title = textwrap.fill(title, wrapat)
    author = textwrap.fill(author, wrapat)

    font = ImageFont.truetype(font=fontname, size=fontsize)
    title_size = draw.textsize(title, font=font)
    draw_text_outlined(draw, ((width - title_size[0]) / 2, 100), title, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    font = ImageFont.truetype(font=fontname, size=fontsize - 2)
    author_size = draw.textsize(author, font=font)
    draw_text_outlined(draw, ((width - author_size[0]) / 2, 100 + title_size[1] + 70), author, textcolor, font=font)

    output = BytesIO()
    img.save(output, "PNG")
    output.name = 'cover.png'
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output


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
