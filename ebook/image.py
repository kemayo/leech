# Basically the same as cover.py with some minor differences
import PIL
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from base64 import b64decode
import math
import textwrap
import requests
import logging

from typing import Tuple

logger = logging.getLogger(__name__)


def get_size_format(b, factor=1000, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def compress_image(image: BytesIO, target_size: int, image_format: str) -> PIL.Image.Image:
    image_size = get_size_format(len(image.getvalue()))
    logger.info(f"Image size: {image_size}")

    big_photo = Image.open(image).convert("RGBA")

    target_pixel_count = 2.8114 * target_size
    if len(image.getvalue()) > target_size:
        logger.info(f"Image is greater than {get_size_format(target_size)}, compressing")
        scale_factor = target_pixel_count / math.prod(big_photo.size)
        if scale_factor < 1:
            x, y = tuple(int(scale_factor * dim) for dim in big_photo.size)
            logger.info(f"Resizing image dimensions from {big_photo.size} to ({x}, {y})")
            sml_photo = big_photo.resize((x, y), resample=Image.LANCZOS)
        else:
            sml_photo = big_photo
        compressed_image_size = get_size_format(len(PIL_Image_to_bytes(sml_photo, image_format)))
        logger.info(f"Compressed image size: {compressed_image_size}")
        return sml_photo
    else:
        logger.info(f"Image is less than {get_size_format(target_size)}, not compressing")
        return big_photo


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
        # Create a new image with a white background
        background_img = Image.new('RGBA', pil_image.size, "white")

        # Paste the image on top of the background
        background_img.paste(pil_image.convert("RGBA"), (0, 0), pil_image.convert("RGBA"))
        pil_image = background_img.convert('RGB')

    pil_image.save(out_io, format=image_format, optimize=True, quality=95)
    return out_io.getvalue()


def get_image_from_url(
    url: str,
    image_format: str = "JPEG",
    compress_images: bool = False,
    max_image_size: int = 1_000_000
) -> Tuple[bytes, str, str]:
    """
    Based on make_cover_from_url(), this function takes in the image url usually gotten from the `src` attribute of
    an image tag and returns the image data, the image format and the image mime type

    @param url: The url of the image
    @param image_format: The format to convert the image to if it's not in the supported formats
    @param compress_images: Whether to compress the image or not
    @param max_image_size: The maximum size of the image in bytes
    @return: A tuple of the image data, the image format and the image mime type
    """
    try:
        if url.startswith("https://www.filepicker.io/api/"):
            logger.warning("Filepicker.io image detected, converting to Fiction.live image. This might fail.")
            url = f"https://cdn3.fiction.live/fp/{url.split('/')[-1]}?&quality=95"
        elif url.startswith("https://cdn3.fiction.live/images/") or url.startswith("https://ddx5i92cqts4o.cloudfront.net/images/"):
            logger.warning("Converting url to cdn6. This might fail.")
            url = f"https://cdn6.fiction.live/file/fictionlive/images/{url.split('/images/')[-1]}"
        elif url.startswith("data:image") and 'base64' in url:
            logger.info("Base64 image detected")
            head, base64data = url.split(',')
            file_ext = str(head.split(';')[0].split('/')[1])
            imgdata = b64decode(base64data)
            if compress_images:
                if file_ext.lower() == "gif":
                    logger.info("GIF images should not be compressed, skipping compression")
                else:
                    compressed_base64_image = compress_image(BytesIO(imgdata), max_image_size, file_ext)
                    imgdata = PIL_Image_to_bytes(compressed_base64_image, file_ext)

            if file_ext.lower() not in ["jpg", "jpeg", "png", "gif"]:
                logger.info(f"Image format {file_ext} not supported by EPUB2.0.1, converting to {image_format}")
                return _convert_to_new_format(imgdata, image_format).read(), image_format.lower(), f"image/{image_format.lower()}"
            return imgdata, file_ext, f"image/{file_ext}"

        print(url)
        img = requests.Session().get(url)
        image = BytesIO(img.content)
        image.seek(0)

        PIL_image = Image.open(image)

        if str(PIL_image.format).lower() == "gif":
            PIL_image = Image.open(image)
            if PIL_image.info['version'] not in [b"GIF89a", "GIF89a"]:
                PIL_image.info['version'] = b"GIF89a"
            return PIL_Image_to_bytes(PIL_image, "GIF"), "gif", "image/gif"

        if compress_images:
            PIL_image = compress_image(image, max_image_size, str(PIL_image.format))

        return PIL_Image_to_bytes(PIL_image, image_format), image_format, f"image/{image_format.lower()}"

    except Exception as e:
        logger.info("Encountered an error downloading image: " + str(e))
        image = make_fallback_image("There was a problem downloading this image.").read()
        return image, "jpeg", "image/jpeg"


def make_fallback_image(
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
    message_size = textsize(draw, message, font=font)
    draw_text_outlined(
        draw, ((width - message_size[0]) / 2, 100), message, textcolor, font=font)
    # draw.text(((width - title_size[0]) / 2, 100), title, textcolor, font=font)

    output = BytesIO()
    img.save(output, "JPEG")
    # writing left the cursor at the end of the file, so reset it
    output.seek(0)
    return output


def _convert_to_new_format(image_bytestream, image_format: str):
    new_image = BytesIO()
    try:
        Image.open(image_bytestream).save(new_image, format=image_format.upper())
        new_image.seek(0)
    except Exception as e:
        logger.info(f"Encountered an error converting image to {image_format}\nError: {e}")
        new_image = make_fallback_image("There was a problem converting this image.")
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
    f = make_fallback_image(
        'Test of a Title which is quite long and will require multiple lines',
        'output.png'
    )
    with open('output.png', 'wb') as out:
        out.write(f.read())
