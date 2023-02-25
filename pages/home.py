from pathlib import Path

from dash import html
import dash_bootstrap_components as dbc
import dash
from typing import List, Dict
from datetime import datetime
from .internal.web.scraper import MultiScraper
from .css import *
from .internal.web import interfaces as inter
from .internal.web.schema import Post
from alive_progress import alive_bar

DEFAULT_BOOKMARKS = Path(__file__).resolve().parent.parent / "bookmarks.txt"
BASE_ROUTE = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_LINK = "https://www.hckrnws.com/stories/{id}"
ROW_LEN = 5

dash.register_page(__name__, path="/")


def get_bookmarks(path: Path = DEFAULT_BOOKMARKS) -> Dict[datetime, str]:
    with open(path) as fp:
        bookmarks = "".join(fp.readlines())
    bookmarks = bookmarks.split("-")
    output = {}

    print(f"Querying cached bookmarks...")
    with alive_bar(len(bookmarks)) as bar:
        for x in range(len(bookmarks)):
            parsed = bookmarks[x].split("q")
            if not inter.DBMi.session.query(Post).filter(Post.id == parsed[0]).count():
                output[
                    datetime.fromtimestamp(float(parsed[1]) / 1e3)
                ] = BASE_ROUTE.format(id=parsed[0])
            bar()

    return output


def make_card(link: Post):
    # Ellipses for long descriptions
    description: str = ""
    if link.text is not None:
        description = link.text
        temp = description.split(" ")
        if len(temp) > 100:
            description = " ".join(temp[:50]) + "..."

    inner_links = [
        dbc.Button(
            "Show HN",
            href=HN_LINK.format(id=link.id),
            target="_blank",
        )
    ]

    if link.url is not None:
        inner_links.append(
            dbc.Button("Show Post", href=link.url, target="_blank")
        )

    links = dbc.ButtonGroup(inner_links)

    return dbc.Card(
        [
            dbc.CardImg(src=link.img, top=True, className="img-fluid rounded-start"),
            dbc.CardBody(
                [
                    html.H4(link.title, className="card-title"),
                    html.Hr(),
                    html.P(description, className="card-text"),
                    links,
                    html.Hr(),
                    html.H6(f"Date Added: {link.date_added.strftime('%d %B, %Y')}"),
                    html.H6(f"Date Created: {link.time.strftime('%d %B, %Y')}"),
                ]
            ),
        ],
    )


def get_card_row(links: List[Post]):
    cards = []
    for card in links:
        if card is not None:
            cards += [make_card(card)]
    return dbc.Row(dbc.CardGroup(cards))


def get_page():
    # Update Datebase with new bookmarks
    MultiScraper(get_bookmarks())

    # Query DB
    bookmarks: List[Post] = inter.DBMi.session.query(Post).all()

    # Construct Bookmarks
    padded_bookmarks = bookmarks + [None] * (len(bookmarks) % ROW_LEN)
    chunked = []
    for x in range(len(padded_bookmarks) // ROW_LEN):
        row = []
        for y in range(ROW_LEN):
            row.append(padded_bookmarks[(x * ROW_LEN) + y])
        chunked.append(row)
    return dbc.Container([get_card_row(row) for row in chunked], id="home-page")


def layout():
    return get_page()
