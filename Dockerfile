FROM alpine:latest

# Package list taken from Pillow documentation:
# https://pillow.readthedocs.io/en/stable/installation.html#building-on-linux
RUN apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev \
    libxcb-dev libpng-dev gcc musl-dev python3 python3-dev py3-pip py3-cryptography \
    && pip install poetry

COPY . /leech

RUN cd /leech \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev

WORKDIR /work

ENTRYPOINT ["/leech/leech.py"]

