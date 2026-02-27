from dash import html, dcc

def get_layout():
    layout = [
        html.Div(
            [
                dcc.Graph(
                    id="indiv-wastewater-graph",
                    config={ "displayModeBar" : False },
                    style={ "height" : "30em" }
                )
            ]
        )
    ]
    return layout