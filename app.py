from dash import Dash, html
import dash_bootstrap_components as dbc
import dash
import logging
import argparse
from util import LogLevel, EnumAction
from pages.internal.web.schema import CACHE
import os

def run() -> None:
    """A function which starts the web app."""

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        suppress_callback_exceptions=True,
        use_pages=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )

    # The app.layout components contains what is displayed by the web app
    app.layout = html.Div([dash.page_container])
    app.run_server(debug=True)
    # app.run_server()


if __name__ == "__main__":

    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--log',
        default=LogLevel.Info,
        type=LogLevel, 
        help=f'set logging level {list(e.name for e in LogLevel)}', 
        action=EnumAction,
        dest='log',
        metavar=''
    )
    parser.add_argument(
        '-r', '--refresh',
        default=False,
        action='store_true',
        help='refresh the database by deleting the cache',
    )

    args = parser.parse_args()

    if args.refresh:
        os.remove(CACHE[10:])

    logging.basicConfig(level=args.log.value)

    run()
