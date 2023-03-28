import requests
from textwrap import dedent
from responses import RequestsMock

from _leech.chapter import Chapter
from _leech.story import Story
from sites.arbitrary import Arbitrary, SiteDefinition

site = Arbitrary(
    story=Story(
        url="http://basic.com/",
        title="Basic",
        author="Basic",
    ),
    definition=SiteDefinition(
        url="http://basic.com/",
        title="Basic",
        author="Basic",
        content_selector="#main",
        content_title_selector="h1.title",
        content_text_selector=".entry-content",
        filter_selector=".skipme",
        next_selector='a[rel="next"]:not([href*="prologue"])',
    ),
)

chapter1 = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta property="og:type" content="article" />
    <meta property="og:title" content="Chapter 1" />
    <meta property="article:published_time" content="2020-01-01T00:00:00+00:00" />
    <meta property="article:modified_time" content="2020-01-02T00:00:00+00:00" />
    <meta property="og:site_name" content="Example" />
  </head>

  <body>
    <div class="site-content">
      <div id="primary" class="content-area">
        <main id="main" class="site-main" role="main">
          <article class="content">
            <header class="entry-header">
              <h1 class="title">Chapter 1</h1>
            </header>

            <div class="entry-content">
              <p>
                <span>Example</span><br />
                <div class="skipme">
                  <span>I get skipped</span>
                </div>
              </p>
            </div>
            <span>Some content afterwards</span>
          </article>
          <nav class="navigation post-navigation" role="navigation">
            <div class="nav-links">
              <a href="http://basic.com/chapter2" rel="next">Chapter 2</a>
            </div>
          </nav>
        </main>
      </div>
    </div>
  </body>
</html>
"""

chapter2 = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta property="og:type" content="article" />
    <meta property="og:title" content="Chapter 2" />
    <meta property="article:published_time" content="2020-01-01T00:00:00+00:00" />
    <meta property="article:modified_time" content="2020-01-02T00:00:00+00:00" />
  </head>

  <body>
    <article id="main">
      <div class="content">
        <h1 class="title">Chapter 2</h1>
        <div class="entry-content">
          <p>
            <span>Example 2</span>
            <div class="skipme">
              <span>I get skipped</span>
            </div>
          </p>
        </div>
      </div>
    </article>
  </body>
</html>
"""


def test_collect(responses: RequestsMock):
    responses.add(responses.GET, "http://basic.com/", body=chapter1)
    responses.add(responses.GET, "http://basic.com/chapter2", body=chapter2)

    session = requests.Session()
    story = site.collect(session)
    assert story == Story(
        title="Basic",
        author="Basic",
        url="http://basic.com/",
        chapters=[
            Chapter(
                number=1,
                title="Chapter 1",
                date="2023-03-27",
                content=dedent(
                    """\
                    <div class="entry-content">
                     <p>
                      <span>
                       Example
                      </span>
                      <br/>
                     </p>
                     <p>
                     </p>
                    </div>
                    """
                ),
                url="http://basic.com/",
            ),
            Chapter(
                number=2,
                title="Chapter 2",
                date="2023-03-27",
                content=dedent(
                    """\
                    <div class="entry-content">
                     <p>
                      <span>
                       Example 2
                      </span>
                     </p>
                     <p>
                     </p>
                    </div>
                    """
                ),
                url="http://basic.com/chapter2",
            ),
        ],
        cover_url=None,
        summary=None,
        footnotes=[],
        tags=[],
    )
