from pathlib import Path
from dash import Input, Output, html, dcc, callback
import dash_bootstrap_components as dbc
import dash
from typing import List, Dict
from datetime import datetime
from .internal.web.scraper import MultiScraper
from .css import *
from .internal.web import interfaces as inter
from .internal.web.schema import Post


dash.register_page(__name__, path="/dash")


# @callback(
#     Output('home-page', 'children'), 
#     Input('rel-img', 'n_clicks')
# )
# def temp():
#     pass


def get_page():
    contents = []
    missing_imgs = inter.DBMi.session.query(Post).filter(Post.img.is_(None)).count()

    notif = html.Span(
        [
            dbc.Badge(
                f"Missing Images: {missing_imgs}", 
                color="info", 
                className="me-1"
            ),
        ]
    )

    contents.append(notif)
    return dbc.Container(contents, id="dashboard")


def layout():
    return get_page()
