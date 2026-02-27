from dash import html, dcc
import dash_bootstrap_components as dbc

def get_layout():
    markdown = """
    To monitor the prevalence of Mpox in San Diego, we are measuring virus concentration at the wastewater 
    treatment plants in San Diego. Fragments of Mpox virus DNA are shed in urine and stool and can serve as an 
    early indicator of the caseload in the community. The data shown here is collected by the EXCITE Lab at UCSD in 
    collaboration with San Diego County, and is available on our [Github repository](https://github.com/andersen-lab/MPX_WasteWater_San-Diego). 
    Scatter points indicate raw data, while solid line represent the same data smoothed with a Savitzky-Golay filter. 
    Hover-over text displays raw values for viral load and smoothed values for reported cases. 
    """

    layout = [
        html.Div(
            [
                dcc.Markdown( markdown, link_target='_blank' ),
                html.P(),
                html.Div(
                    [
                        html.Div(
                            [dbc.RadioItems(
                                id="ww-source-radio",
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-primary",
                                labelCheckedClassName="active",
                                options=[
                                    { "label": "Encina", "value": "Encina" },
                                    { "label": "Point Loma", "value": "PointLoma" },
                                    { "label": "South Bay", "value": "SouthBay" }
                                ],
                                value="PointLoma",
                                style={ "width": "50%", "justifyContent": "flex-start" }
                            ),
                                dbc.RadioItems(
                                    id="yaxis-scale-radio",
                                    className="btn-group",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-outline-primary",
                                    labelCheckedClassName="active",
                                    options=[
                                        { "label": "Linear scale", "value": "linear" },
                                        { "label": "Log scale", "value": "log", "disabled" : True },

                                    ],
                                    value="linear",
                                    style={ "width": "50%", "justifyContent": "flex-end" }
                                )]
                        ),
                        dcc.Graph(
                            id="monkeypox-graph",
                            config={"displayModeBar" : False },
                            style={"height" : "30em"}
                        )
                    ]
                )
            ]
        ),
        html.Br(),
        html.Br(),
        html.P( id="commit-date", style={ 'textAlign': 'center' } )
    ]

    return layout
