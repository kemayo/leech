# Basically the same as cover.py with some minor differences
import PIL
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from base64 import b64decode
import textwrap
import requests
import logging

from typing import Tuple

logger = logging.getLogger(__name__)


def make_image(
    message: str,
    width=600,
    height=300,
    fontname="Helvetica",
    font_size=40,
    bg_color=(0, 0, 0),
    textcolor=(255, 255, 255),
    wrap_at=30
):
    """
    This function should only be called if get_image_from_url() fails
    """
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    message = textwrap.fill(message, wrap_at)

    font = _safe_font(fontname, size=font_size)
    message_size = draw.textsize(message, font=font)
    draw_text_outlined(
        draw, ((width - message_size[0]) / 2, 100), message, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    output = BytesIO()
    img.save(output, "JPEG")
    output.name = 'cover.jpeg'
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output


def PIL_Image_to_bytes(
    pil_image: PIL.Image.Image,
    image_format: str
) -> bytes:
    out_io = BytesIO()
    if image_format.lower().startswith("gif"):
        frames = []
        current = pil_image.convert('RGBA')
        while True:
            try:
                frames.append(current)
                pil_image.seek(pil_image.tell() + 1)
                current = Image.alpha_composite(current, pil_image.convert('RGBA'))
            except EOFError:
                break
        frames[0].save(out_io, format=image_format, save_all=True, append_images=frames[1:], optimize=True, loop=0)
        return out_io.getvalue()

    elif image_format.lower() in ["jpeg", "jpg"]:
        pil_image = pil_image.convert("RGB")

    pil_image.save(out_io, format=image_format, optimize=True, quality=95)
    return out_io.getvalue()


def get_image_from_url(url: str, image_format: str = "JPEG") -> Tuple[bytes, str, str]:
    """
    Based on make_cover_from_url(), this function takes in the image url usually gotten from the `src` attribute of
    an image tag and returns the image data, the image format and the image mime type

    @param url: The url of the image
    @param image_format: The format to convert the image to if it's not in the supported formats
    @return: A tuple of the image data, the image format and the image mime type
    """
    try:
        if url.startswith("https://www.filepicker.io/api/"):
            logger.warning("Filepicker.io image detected, converting to Fiction.live image. This might fail.")
            url = f"https://cdn3.fiction.live/fp/{url.split('/')[-1]}?&quality=95"
        elif url.startswith("data:image") and 'base64' in url:
            logger.info("Base64 image detected")
            head, base64data = url.split(',')
            file_ext = head.split(';')[0].split('/')[1]
            imgdata = b64decode(base64data)
            if file_ext.lower() not in ["jpg", "jpeg", "png", "gif"]:
                logger.info(f"Image format {file_ext} not supported by EPUB2.0.1, converting to {image_format}")
                return _convert_to_new_format(imgdata, image_format).read(), image_format.lower(), f"image/{image_format.lower()}"
            return imgdata, file_ext, f"image/{file_ext}"

        print(url)
        img = requests.Session().get(url)
        image = BytesIO(img.content)
        image.seek(0)

        PIL_image = Image.open(image)
        img_format = PIL_image.format

        if img_format.lower() == "gif":
            PIL_image = Image.open(image)
            if PIL_image.info['version'] not in [b"GIF89a", "GIF89a"]:
                PIL_image.info['version'] = b"GIF89a"
            return PIL_Image_to_bytes(PIL_image, "GIF"), "gif", "image/gif"

        return PIL_Image_to_bytes(PIL_image, image_format), image_format, f"image/{image_format.lower()}"

    except Exception as e:
        logger.info("Encountered an error downloading image: " + str(e))
        cover = make_image("There was a problem downloading this image.").read()
        return cover, "jpeg", "image/jpeg"


def _convert_to_new_format(image_bytestream, image_format):
    new_image = BytesIO()
    try:
        Image.open(image_bytestream).save(new_image, format=image_format.upper())
        new_image.name = f'cover.{image_format.lower()}'
        new_image.seek(0)
    except Exception as e:
        logger.info(f"Encountered an error converting image to {image_format}\nError: {e}")
        new_image = make_image("There was a problem converting this image.")
    return new_image


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


if __name__ == '__main__':
    f = make_image(
        'Test of a Title which is quite long and will require multiple lines')
    with open('output.png', 'wb') as out:
        out.write(f.read())
