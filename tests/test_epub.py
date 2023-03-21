from _leech.epub import make_epub, EpubFile


def test_epub():
    make_epub(
        "test.epub",
        [
            EpubFile(title="Chapter 1", path="a.html", contents="Test"),
            EpubFile(title="Chapter 2", path="test/b.html", contents="Still a test"),
        ],
        {},
    )
