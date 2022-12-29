from dash import Dash, html
import dash_bootstrap_components as dbc
import dash

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    use_pages=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# The app.layout components contains what is displayed by the web app
app.layout = html.Div([dash.page_container])

def run() -> None:
    """A function which starts the web app."""
    app.run_server(debug=True)
    # app.run_server()


if __name__ == "__main__":
    run()