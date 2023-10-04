from dash import Dash, html
import dash_bootstrap_components as dbc
import dash
import logging
import argparse
from util import LogLevel, EnumAction

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
        type=LogLevel, 
        help=f'set logging level {list(e.name for e in LogLevel)}', 
        action=EnumAction,
        dest='log',
        metavar=''
    )

    args = parser.parse_args()
    logging.basicConfig(level=args.log.value)

    run()
