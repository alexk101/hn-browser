from pathlib import Path
from dash import Input, Output, html, dcc, callback, dash_table
import dash_bootstrap_components as dbc
import dash
from typing import List, Dict
from datetime import datetime
from .internal.web.scraper import MultiScraper
from .css import *
from .internal.web import interfaces as inter
from .internal.web.schema import Post
import plotly.graph_objects as go


dash.register_page(__name__, path="/dash")


# @callback(
#     Output('home-page', 'children'), 
#     Input('rel-img', 'n_clicks')
# )
# def temp():
#     pass

def plot_url_stats(min_count: int = 0, show_column: str = "posts"):
    """
    Plots the domain stats of the urls in the database.
    
    Args:
        min_count (int): Minimum number of posts to include in plot
        show_column (str): Which column to display ('posts' or 'comments')
    """
    # Get all posts with URLs
    posts = inter.DBMi.session.query(Post).filter(Post.url.isnot(None)).all()
    
    # Extract domains and count frequencies
    from urllib.parse import urlparse
    domain_stats = {}
    for post in posts:
        try:
            domain = urlparse(post.url).netloc.split('.')[-2]
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'posts': 0,
                    'children': 0
                }
            domain_stats[domain]['posts'] += 1
            domain_stats[domain]['children'] += post.descendants
        except:
            continue
    
    # Filter based on minimum count
    domain_stats = {k:v for k,v in domain_stats.items() if v['posts'] >= min_count}
            
    # Convert to lists for plotting
    domains = list(domain_stats.keys())
    values = [stats['posts'] if show_column == "posts" else stats['children'] 
             for stats in domain_stats.values()]

    # Create bar plot
    fig = go.Figure(data=[
        go.Bar(
            name='Posts' if show_column == "posts" else 'Comments', 
            x=domains, 
            y=values
        )
    ])
    
    fig.update_layout(
        title='Domain Statistics',
        xaxis_title='Domain',
        yaxis_title='Count',
        height=400
    )

    return dcc.Graph(figure=fig)

def plot_date_histogram(bin_size: int = 7):
    """
    Creates a histogram of post addition dates
    
    Args:
        bin_size (int): Size of bins in days
    """
    posts = inter.DBMi.session.query(Post).all()
    dates = [post.date_added.date() for post in posts]
    
    fig = go.Figure(data=[
        go.Histogram(
            x=dates,
            xbins=dict(
                size=bin_size * 24 * 60 * 60 * 1000  # Convert days to milliseconds
            ),
            name='Posts'
        )
    ])
    
    fig.update_layout(
        title='Post Addition Timeline',
        xaxis_title='Date',
        yaxis_title='Number of Posts',
        height=400,
        bargap=0.1
    )
    
    return dcc.Graph(figure=fig)

def get_page():
    """
    Get the dashboard page
    """
    contents = []
    missing_imgs = inter.DBMi.session.query(Post).filter(Post.img.is_(None)).count()
    missing_imgs_perc = missing_imgs/inter.DBMi.session.query(Post).count()*100
    
    # Get posts missing HTML
    missing_html_posts = inter.DBMi.session.query(Post).filter(Post.html.is_(None)).all()
    missing_html = len(missing_html_posts)
    missing_html_perc = missing_html/inter.DBMi.session.query(Post).count()*100

    # Prepare data for DataTable
    table_data = [
        {'title': post.title, 'url': post.url} 
        for post in missing_html_posts if post.url is not None
    ]

    notif = html.Span([
        dbc.Badge(
            f"Missing Images: {missing_imgs} | {missing_imgs_perc:.1f}%", 
            color="info", 
            className="me-1"
        ),
        dbc.Badge(
            f"Missing HTML: {missing_html} | {missing_html_perc:.1f}%", 
            color="info", 
            className="me-1"
        ),
        dbc.Row([
            dbc.Col([
                html.H4("Post Timeline", className="mt-4"),
                dbc.Label("Bin Size (days):"),
                dbc.Input(
                    type="number",
                    min=1,
                    step=1,
                    value=7,
                    id="histogram-bin-size"
                ),
                html.Div(id="date-histogram-plot")
            ])
        ]),
        dbc.Row(
            [
                dbc.Col([
                    dbc.Label("Minimum Posts Filter:"),
                    dbc.Input(
                        type="number",
                        min=0,
                        step=1,
                        value=3,
                        id="min-posts-filter"
                    ),
                    dbc.RadioItems(
                        options=[
                            {"label": "Show Posts", "value": "posts"},
                            {"label": "Show Comments", "value": "comments"},
                        ],
                        value="posts",
                        id="column-selector",
                        inline=True,
                        style={"marginTop": "10px", "marginBottom": "10px"}
                    ),
                    html.Div(id="url-stats-plot")
                ])
            ]
        ),
        dbc.Row(
            [
                dbc.Col([
                    html.H4("Posts Missing HTML", className="mt-4"),
                    dash_table.DataTable(
                        data=table_data,
                        columns=[
                            {'name': 'Title', 'id': 'title'},
                            {'name': 'URL', 'id': 'url'}
                        ],
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'textAlign': 'left',
                            'minWidth': '180px', 
                            'maxWidth': '400px',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        page_size=10,
                    )
                ])
            ]
        )
    ])

    contents.append(notif)
    return dbc.Container(contents, id="dashboard")

@callback(
    Output("url-stats-plot", "children"),
    Input("min-posts-filter", "value"),
    Input("column-selector", "value")
)
def update_plot(min_count, show_column):
    if min_count is None:
        min_count = 0
    return plot_url_stats(min_count, show_column)

@callback(
    Output("date-histogram-plot", "children"),
    Input("histogram-bin-size", "value")
)
def update_histogram(bin_size):
    if bin_size is None or bin_size < 1:
        bin_size = 7
    return plot_date_histogram(bin_size)

def layout():
    return get_page()
