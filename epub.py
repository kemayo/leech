#!/usr/bin/python

import os.path
import zipfile
import xml.etree.ElementTree as etree
import uuid

"""
So, an epub is approximately a zipfile of HTML files, with
a bit of metadata thrown in for good measure.

This totally started from http://www.manuel-strehl.de/dev/simple_epub_ebooks_with_python.en.html
"""


def make_epub(filename, html_files, meta):
    unique_id = meta.get('unique_id', False)
    if not unique_id:
        unique_id = 'leech_book_' + str(uuid.uuid4())

    epub = zipfile.ZipFile(filename, 'w')

    # The first file must be named "mimetype"
    epub.writestr("mimetype", "application/epub+zip")

    # We need an index file, that lists all other HTML files
    # This index file itself is referenced in the META_INF/container.xml
    # file
    container = etree.Element('container', version="1.0", xmlns="urn:oasis:names:tc:opendocument:xmlns:container")
    rootfiles = etree.SubElement(container, 'rootfiles')
    etree.SubElement(rootfiles, 'rootfile', {
        'full-path': "OEBPS/Content.opf",
        'media-type': "application/oebps-package+xml",
    })
    epub.writestr("META-INF/container.xml", etree.tostring(container))

    package = etree.Element('package', {
        'version': "2.0",
        'xmlns': "http://www.idpf.org/2007/opf",
        'unique-identifier': 'book_identifier',  # could plausibly be based on the name
    })

    # build the metadata
    metadata = etree.SubElement(package, 'metadata', {
        'xmlns:dc': "http://purl.org/dc/elements/1.1/",
        'xmlns:opf': "http://www.idpf.org/2007/opf",
    })
    identifier = etree.SubElement(metadata, 'dc:identifier', id='book_identifier')
    if unique_id.find('://') != -1:
        identifier.set('opf:scheme', "URI")
    identifier.text = unique_id
    etree.SubElement(metadata, 'dc:title').text = meta.get('title', 'Untitled')
    etree.SubElement(metadata, 'dc:language').text = meta.get('language', 'en')
    etree.SubElement(metadata, 'dc:creator', {'opf:role': 'aut'}).text = meta.get('author', 'Unknown')

    # we'll need a manifest and spine
    manifest = etree.SubElement(package, 'manifest')
    spine = etree.SubElement(package, 'spine', toc="ncx")

    # ...and the ncx index
    ncx = etree.Element('ncx', {
        'xmlns': "http://www.daisy.org/z3986/2005/ncx/",
        'version': "2005-1",
        'xml:lang': "en-US",
    })
    etree.SubElement(etree.SubElement(ncx, 'head'), 'meta', name="dtb:uid", content=unique_id)
    etree.SubElement(etree.SubElement(ncx, 'docTitle'), 'text').text = meta.get('title', 'Untitled')
    etree.SubElement(etree.SubElement(ncx, 'docAuthor'), 'text').text = meta.get('author', 'Unknown')
    navmap = etree.SubElement(ncx, 'navMap')

    # Write each HTML file to the ebook, collect information for the index
    for i, html in enumerate(html_files):
        basename = os.path.basename(html[1])
        file_id = 'file_%d' % (i + 1)
        etree.SubElement(manifest, 'item', {
            'id': file_id,
            'href': basename,
            'media-type': "application/xhtml+xml",
        })
        etree.SubElement(spine, 'itemref', idref=file_id)
        point = etree.SubElement(navmap, 'navPoint', {
            'class': "h1",
            'id': file_id,
        })
        etree.SubElement(etree.SubElement(point, 'navLabel'), 'text').text = html[0]
        etree.SubElement(point, 'content', src=basename)

        # and add the actual html to the zip
        if html[2]:
            epub.writestr('OEBPS/' + basename, html[2])
        else:
            epub.write(html[1], 'OEBPS/' + basename)

    # ...and add the ncx to the manifest
    etree.SubElement(manifest, 'item', {
        'id': 'ncx',
        'href': 'toc.ncx',
        'media-type': "application/x-dtbncx+xml",
    })
    epub.writestr('OEBPS/toc.ncx', etree.tostring(ncx))

    # Finally, write the index
    epub.writestr('OEBPS/Content.opf', etree.tostring(package))

    epub.close()

    return True

if __name__ == '__main__':
    make_epub('test.epub', [('Chapter 1', 'test/a.html'), ('Chapter 2', 'test/b.html')], {})
