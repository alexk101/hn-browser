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

def plot_url_stats():
    """
    Plots the domain stats of the urls in the database.
    For each domain, the number of posts and the number of children are plotted.
    """
    # Get all posts with URLs
    posts = inter.DBMi.session.query(Post).filter(Post.url.isnot(None)).all()
    
    # Extract domains and count frequencies
    from urllib.parse import urlparse
    domain_stats = {}
    for post in posts:
        try:
            domain = urlparse(post.url).netloc
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'posts': 0,
                    'children': 0
                }
            domain_stats[domain]['posts'] += 1
            domain_stats[domain]['children'] += post.descendants
        except:
            continue
            
    # Convert to lists for plotting
    domains = list(domain_stats.keys())
    post_counts = [stats['posts'] for stats in domain_stats.values()]
    child_counts = [stats['children'] for stats in domain_stats.values()]

    # Create bar plot
    import plotly.graph_objects as go
    fig = go.Figure(data=[
        go.Bar(name='Posts', x=domains, y=post_counts),
        go.Bar(name='Comments', x=domains, y=child_counts)
    ])
    
    fig.update_layout(
        title='Domain Statistics',
        xaxis_title='Domain',
        yaxis_title='Count',
        barmode='group',
        height=400
    )

    return dcc.Graph(figure=fig)

def get_page():
    """
    Get the dashboard page
    """
    contents = []
    missing_imgs = inter.DBMi.session.query(Post).filter(Post.img.is_(None)).count()

    
    notif = html.Span(
        [
            dbc.Badge(
                f"Missing Images: {missing_imgs}", 
                color="info", 
                className="me-1"
            ),
            dbc.Row(
                [
                    dbc.Col(plot_url_stats())
                ]
            )
        ]
    )

    contents.append(notif)
    return dbc.Container(contents, id="dashboard")


def layout():
    return get_page()
