
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
    draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    font = ImageFont.truetype(font=fontname, size=fontsize - 2)
    author_size = draw.textsize(author, font=font)
    draw.text(((width - author_size[0]) / 2, 100 + title_size[1] + 70), author, textcolor, font=font)

    draw = ImageDraw.Draw(img)

    output = BytesIO()
    img.save(output, "PNG")
    output.name = 'cover.png'
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output

if __name__ == '__main__':
    f = make_cover('Test of a Title which is quite long and will require multiple lines', 'Some Dude')
    with open('output.png', 'wb') as out:
        out.write(f.read())
