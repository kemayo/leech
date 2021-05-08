FROM alpine:latest as install

# Package list taken from Pillow documentation:
# https://pillow.readthedocs.io/en/stable/installation.html#building-on-linux
RUN apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev \
    libxcb-dev libpng-dev gcc musl-dev python3 python3-dev  py3-pip py3-cryptography

FROM install as poetry

# We don't need poetry in the final container.
RUN pip install poetry

COPY . /leech

RUN cd /leech && poetry export > requirements.txt

FROM install

COPY --from=poetry /leech /leech
RUN pip3 install -r /leech/requirements.txt

WORKDIR /work

ENTRYPOINT ["/leech/leech.py"]
