from pathlib import Path

from dash import dcc, html
import dash_bootstrap_components as dbc
import dash
from typing import List, Dict, Any
from datetime import datetime
from .internal.web.scraper import MultiScraper
from sqlalchemy import text
from .css import *
from .internal.web import interfaces as inter
from .internal.web.schema import python_hn_post
from alive_progress import alive_bar

DEFAULT_BOOKMARKS = Path(__file__).resolve().parent.parent / 'bookmarks.txt'
BASE_ROUTE = 'https://hacker-news.firebaseio.com/v0/item/{id}.json'
HN_LINK = 'https://www.hckrnws.com/stories/{id}'
ROW_LEN = 5

dash.register_page(__name__, path="/")

def get_bookmarks(path: Path=DEFAULT_BOOKMARKS) -> Dict[datetime,str]:
    with open(path) as fp:
        bookmarks = ''.join(fp.readlines())
    bookmarks = bookmarks.split('-')
    output = {}

    conn = inter.DBMi.engine.connect()
    query = 'SELECT 1 FROM hn_bookmarks WHERE id = {id};'

    print(f'Querying cached bookmarks...')
    with alive_bar(len(bookmarks)) as bar:
        for x in range(len(bookmarks)):
            parsed = bookmarks[x].split('q')
            result = list(conn.execute(text(query.format(id=parsed[0]))))[0][0]
            # Check if bookmark is not already in DB
            if not result:
                output[datetime.fromtimestamp(float(parsed[1])/1e3)] = BASE_ROUTE.format(id=parsed[0])
            bar()

    conn.close()
    return output


def get_image():
    pass


def make_card(link: Dict[str,Any]): 
    # Ellipses for long descriptions
    description: str = link['text']
    temp = description.split(' ')
    if (len(temp) > 100):
        description = ' '.join(temp[:50]) + '...'
    # print(f"Card title: {link['title']}")

    return dbc.Card(
        [
            # dbc.CardImg(src=link.preview.absolute_image, top=True),
            dbc.CardBody(
                [                    
                    html.H4(link['title'], className="card-title"),
                    html.Hr(),
                    html.P(description, className="card-text"),
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                "Show HN", 
                                href=HN_LINK.format(id=link['id']),
                                target="_blank"
                            ), 
                            dbc.Button(
                                "Show Post", 
                                href=link['url'],
                                target="_blank"
                            )
                        ]
                    ),
                    html.Hr(),
                    html.H6(f"Date Added: {link['date_added'].strftime('%d %B, %Y')}"),
                    html.H6(f"Date Created: {link['time'].strftime('%d %B, %Y')}"),
                ]
            ),
        ],
    )


def get_card_row(links: List[Dict[str,Any]]):
    return dbc.Row(dbc.CardGroup([make_card(link) for link in links]))


def get_page():
    # Update Datebase with new bookmarks
    MultiScraper(get_bookmarks())

    # Query DB
    conn = inter.DBMi.engine.connect()
    bookmarks: List[Dict[str,Any]] = [dict(zip(python_hn_post, bookmark)) for bookmark in conn.execute(inter.DBMi.hn.select())]
    conn.close()

    # Construct Bookmarks
    bookmarks += [python_hn_post.copy()] * (len(bookmarks) % ROW_LEN)
    chunked = []
    for x in range(len(bookmarks) // ROW_LEN):
        row = []
        for y in range(ROW_LEN):
            row.append(bookmarks[(x*ROW_LEN)+y])
        chunked.append(row)
    return dbc.Container([get_card_row(row) for row in chunked], id='home-page')


def layout():    
    return get_page()
