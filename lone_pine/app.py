# -*- coding: utf-8 -*-
from dash import html, dcc
import dash_bootstrap_components as dbc
import src.format_resources as format_data
import dash
from src.callbacks import register_callbacks

external_stylesheets = [dbc.themes.ZEPHYR, dbc.icons.BOOTSTRAP]
app = dash.Dash( __name__, external_stylesheets=external_stylesheets )
server = app.server
app.config.suppress_callback_exceptions = True
app.scripts.config.serve_locally = False
app.scripts.append_script( {
    "external_url" : "https://www.googletagmanager.com/gtag/js?id=G-35P4705MP1"
})
app.scripts.append_script( {
    "external_url" : "https://raw.githubusercontent.com/watronfire/lone_pine/master/assets/gtag.js"
})

sequences = format_data.load_sequences()
cases_whole = format_data.load_cases()
growth_rates = format_data.load_growth_rates()
ww_growth_rates = format_data.load_ww_growth_rates()

register_callbacks( app, sequences, cases_whole, growth_rates, ww_growth_rates )

app.layout = html.Div( children=[
    dcc.Location(id='url', refresh=False),
    html.Div( [html.P( "Loading..." )],
        id="page-contents"
    ),
    html.Div( id="hidden-div", children=[], hidden=True )
],
    style={ "marginLeft" : "auto",
            "marginRight" : "auto",
            "maxWidth" : "77em" }
)

if __name__ == '__main__':
    app.run_server( debug=False, port=8051 )
