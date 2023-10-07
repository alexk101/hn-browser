from pathlib import Path
from dash import (
    Input, 
    Output,
    State,
    html, 
    dcc,
    ctx,
    callback
)
import dash_bootstrap_components as dbc
from sqlalchemy import update
import dash
from typing import List, Dict
from datetime import datetime
from .internal.web.scraper import (
    MultiScraper, 
    BingImgSearch, 
    update_posts,
    validate_all
)
from .css import *
from .internal.web import interfaces as inter
from .internal.web.schema import Post
from alive_progress import alive_bar
import numpy as np
import trio

DEFAULT_BOOKMARKS = Path(__file__).resolve().parent.parent / "bookmarks.txt"
BASE_ROUTE = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_LINK = "https://www.hckrnws.com/stories/{id}"
ROW_LEN = 6

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

    links = dbc.ButtonGroup(
        inner_links, 
        className='card-footer',
        style={'padding': 0}
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                link.title, 
                className="card-title",
                style=OVERFLOW_TEXT
            ),
            dbc.CardImg(
                src=link.img, 
                # top=True, 
                className="img-fluid rounded-start",
                style=IMG_STYLE
            ),
            dbc.CardBody(
                [
                    dbc.Stack(
                        [
                            html.Div(f"Added: {link.date_added.strftime('%d %b, %Y')}"),
                            html.Div(f"Created: {link.time.strftime('%d %b, %Y')}"),
                        ]
                    )
                ],
                style={
                    'padding': '0.5rem'
                }
            ),
            links
        ],
    )


def get_card_row(links: List[Post]):
    cards = []
    for card in links:
        if card is not None:
            cards += [make_card(card)]
    return dbc.Row(dbc.CardGroup(cards))


@callback(
    Output('home-page', 'children'),
    Input("page-num", "active_page"),
    Input('rel-img', 'n_clicks'), 
    prevent_initial_call=True
)
def reload_imgs(page: int, n_click: int):
    context = ctx.triggered_id
    print(context)
    if context == 'rel-img':
        missing_imgs = inter.DBMi.session.query(Post).filter(Post.img.is_(None)).all()
        bing = BingImgSearch()

        temp = {}
        for post in missing_imgs:
            if post.img is None:
                temp[post.title] = post
                bing.add_query(post.title)

        imgs = dict(zip(bing.titles, bing.get_urls()))

        for title, img in imgs.items():
            temp[title].img = img
        posts = list(temp.values())
        update_posts(posts)
    print('triggered')
    return get_page(page)


@callback(
    Output('dummy', 'children'),
    Input('chk-img', 'n_clicks'), 
    prevent_initial_call=True
)
def check_images(n_click: int):
    all_posts = inter.DBMi.session.query(Post).filter(Post.img.is_not(None)).all()

    valid = trio.run(validate_all, [x.img for x in all_posts])
    valid = np.asarray(valid)

    print(f'valid: {valid.sum()}')
    print(f'invalid: {(valid==False).sum()}')

    evict = []
    for post, validity in zip(all_posts, valid):
        if not validity:
            evict.append(post.id)

    stmnt = update(Post).where(Post.id.in_(evict)).values(img=None)
    inter.DBMi.session.execute(stmnt)
    inter.DBMi.session.commit()
    return None


def get_page(page: int):
    # Update Database with new bookmarks
    scraper = MultiScraper(get_bookmarks())
    scraper.save()

    n_item = ROW_LEN * 3
    total_items = inter.DBMi.session.query(Post).count()
    # Query DB
    bookmarks: List[Post] = inter.DBMi.session.query(Post).limit(n_item).offset((page-1)*n_item).all()

    nav = dbc.Navbar(
        [
            dbc.NavbarBrand('HN Browser', style={'margin-left':'1rem'}),
            dbc.Container(
                [
                    dbc.NavLink("Dashboard", active=True, href="/dash", style=NAV_ITEM),
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem("Reload Images", id='rel-img'),
                            dbc.DropdownMenuItem("Check Images", id='chk-img')
                        ],
                        label="Options",
                        nav=True,
                        style=NAV_ITEM
                    )
                ],
                fluid = True,
                style={
                    'justify-content': 'flex-end',
                    'padding': 0
                },
                # horizontal='end'
            )
        ],
        color="dark",
        dark=True,
    )

    # Construct Bookmarks
    padded_bookmarks = bookmarks + [None] * (len(bookmarks) % ROW_LEN)
    chunked = []
    for x in range(len(padded_bookmarks) // ROW_LEN):
        row = []
        for y in range(ROW_LEN):
            row.append(padded_bookmarks[(x * ROW_LEN) + y])
        chunked.append(row)

    pagination = dbc.Pagination(
        id='page-num', 
        max_value=np.ceil(total_items/n_item),
        first_last=True,
        previous_next=True,
        fully_expanded=False,
        style={'justify-content':'center'},
        active_page=page
    )

    contents = []
    contents.append(html.Div(id='dummy', style={'display':'none'}))
    contents.append(nav)
    contents += [get_card_row(row) for row in chunked]
    contents.append(pagination)

    return dbc.Container(contents, id="home-page")


def layout():
    return get_page(1)
