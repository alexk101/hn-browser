from pathlib import Path

from dash import dcc, html
import dash_bootstrap_components as dbc
import dash
from typing import List
from .internal.web.scraper import Scraper
from .css import *

DEFAULT_BOOKMARKS = Path(__file__).resolve().parent.parent / 'bookmarks.txt'
BASE_ROUTE = 'https://news.ycombinator.com/item?id='
ROW_LEN = 5

dash.register_page(__name__, path="/")

def get_bookmarks(path: Path=DEFAULT_BOOKMARKS):
    with open(path) as fp:
        bookmarks = ''.join(fp.readlines())
    bookmarks = bookmarks.split('-')

    for x in range(len(bookmarks)):
        bookmarks[x] = BASE_ROUTE + bookmarks[x].split('q')[0]
    return bookmarks

def get_image():
    pass

def make_card(link: Scraper):
    style = {'visibility': 'hidden'} if link is None else {}
    # if link.preview is None:
    #     return dbc.Card()
 
    # Ellipses for long descriptions
    description: str = link.preview.description
    temp = description.split(' ')
    if (len(temp) > 100):
        description = ' '.join(temp) + '...'

    return dbc.Card(
        [
            dbc.CardImg(src=link.preview.absolute_image, top=True),
            dbc.CardBody(
                [
                    html.H4(link.hn_title, className="card-title"),
                    html.P(description, className="card-text"),
                    dbc.ButtonGroup(
                        [
                            dbc.Button("Show HN", href=link.hn_link), 
                            dbc.Button("Show Post", href=link.content_link)
                        ]
                    )
                ]
            ),
        ],
        style=style
    )

def scrape(bookmarks: List[str]) -> List[Scraper]:
    return [Scraper(link) for link in bookmarks]

def get_card_row(links: List[Scraper]):
    return dbc.Row(dbc.CardGroup([make_card(link) for link in links]))

def get_page():
    bookmarks = get_bookmarks()
    bookmarks = scrape(bookmarks)
    bookmarks += [None] * (len(bookmarks) % ROW_LEN)
    chunked = []
    for x in range(len(bookmarks) // ROW_LEN):
        row = []
        for y in range(ROW_LEN):
            row.append(bookmarks[(x*ROW_LEN)+y])
        chunked.append(row)
    return dbc.Container([get_card_row(row) for row in chunked], id='home-page')

def layout():
    return get_page()