from dash import html, dcc
import dash_bootstrap_components as dbc

def get_layout():
    layout = [
        html.Div( [dcc.Markdown( id="markdown-stuff", link_target='_blank' ),
                   html.P() ] ),
        html.Div( id="top-table-div", style={"width" : "55em",
                                             "marginLeft" : "auto",
                                             "marginRight" : "auto",
                                             "marginBottom" : "25px"} ),
        html.Div( [
            html.Div( [
                html.Div( [
                    html.H5( "ZIP code", style={ "color" : "#F8F9FA", "margin" : "1%" } ),
                    dcc.Dropdown( id = 'zip-drop',
                                  multi=False,
                                  placeholder="All",
                                  style={"margin" : "1%"}
                                  )
                ],
                    style={ "float" : "left", "width" : "25%" } ),
                html.Div( [
                    html.H5( "Recency", style={ "color" : "#F8F9FA", "margin" : "1%" } ),
                    dcc.Dropdown( id = 'recency-drop',
                                  options=[
                                      { 'label' : "Last week", 'value': 7},
                                      { 'label' : "Last month", 'value' : 30 },
                                      { 'label' : "Last 6 month", 'value' : 183 },
                                      { 'label' : "Last year", 'value' : 365 }
                                  ],
                                  multi=False,
                                  clearable=True,
                                  searchable=False,
                                  placeholder="All",
                                  style={"margin" : "1%"}
                                  )
                ],
                    style={ "float" : "left", "width" : "25%" } ),
                html.Div( [
                    html.H5( "Sequencing Lab", style={ "color" : "#F8F9FA", "margin" : "1%" } ),
                    dcc.Dropdown( id = 'sequencer-drop',
                                  multi=False,
                                  placeholder="All",
                                  style={"margin" : "1%", "fontSize" : "12px" }
                                  )
                ],
                    style={ "float" : "left", "width" : "25%" } ),
                html.Div( [
                    html.H5( "Provider", style={ "color" : "#F8F9FA", "margin" : "1%" } ),
                    dcc.Dropdown( id = 'provider-drop',
                                  multi=False,
                                  clearable=True,
                                  searchable=True,
                                  placeholder="All",
                                  style={"margin" : "1%", "font-size" : "85%" }
                                  )
                ],
                    style={ "float" : "left", "width" : "25%" }
                ),
            ] )
        ],
            style={ "marginLeft" : "auto",
                    "marginRight" : "auto",
                    "backgroundColor" : "#3C5C94",
                    "opacity" : "1"},
            className="pretty_container_rounded row"
        ),
        html.Div( [
            html.Div(
                dcc.Graph(
                    id="cum-graph",
                    config={'displayModeBar': False},
                    style={ "height" : "25em" }
                ),
                className="pretty_container four columns",
                style={'width': '32%', 'display': 'inline-block'}
            ),
            html.Div(
                dcc.Graph(
                    id="daily-graph",
                    config={'displayModeBar': False},
                    style={ "height" : "25em" }
                ),
                className="pretty_container four columns",
                style={'width': '32%', 'display': 'inline-block', }

            ),
            html.Div(
                dcc.Graph(
                    id="fraction-graph",
                    config={'displayModeBar': False},
                    style={ "height" : "25em" }
                ),
                className="pretty_container four columns",
                style={"width": '33%', "display": "inline-block"}
            ),
        ], className="row",
            style={ "marginLeft" : "auto",
                    "marginRight" : "auto",
                    "display": "flex",
                    "flexWrap": "wrap" }
        ),
        html.Div( [
            html.H4( "PANGO Lineages" ),
            html.Div(
                dcc.Dropdown( id = 'lineage-drop',
                              multi=False,
                              placeholder="All lineages"
                              ),
                style={'width': '30%', 'display': 'inline-block'},
                className="three columns" ),
            html.Div(
                dbc.RadioItems(
                    id="lineage-type",
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-outline-primary",
                    labelCheckedClassName="active",
                    options=[
                        { 'label': "Total", 'value': 'sequences' },
                        { 'label': "Fraction", 'value': "fraction" },
                    ],
                    value="sequences",
                ),
                style={ 'width': '49%', 'display': 'inline-block'},
                className="three columns" )
        ],
            className="row"
        ),
        html.Div(
            dcc.Graph(
                id="lineage-graph",
                config={"displayModeBar" : False},
                style={ "height"  : "25em" }
            ),
            className="pretty_container",
            style={ "marginLeft" : "auto",
                    "marginRight" : "auto" }
        ),
        html.Div(
            dcc.Graph(
                id="lineage-time-graph",
                config={"displayModeBar" : False},
                style={"height" : "25em" }
            ),
            className="pretty_container",
            style={ "marginLeft" : "auto",
                    "marginRight" : "auto" }
        ),

        ## Marking the addition of a new area graph
        html.Div(
                    [
                        html.Div(
                            [
                                html.Br(),
                                html.Div(
                                    html.H4( ["Clinical Lineages  ", ] ), 
                                    className="three columns",
                                    style={"width" : "63.3%", "marginLeft" : "0", "marginRight": "2.5%", 'display': 'inline-block'}
                                ),
                                dbc.Tooltip(
                                    uncertainty_alert,
                                    target="tooltip-target",
                                    placement="right",
                                    style={"width" : "500", "maxWidth" : "500"}
                                ),
                            ],
                            className="radio-group",
                            style={"margin" : "0"}
                        ),
                        html.Div(
                            [dbc.RadioItems(
                                id="scale-seqs-radios",
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-primary",
                                labelCheckedClassName="active",
                                options=[
                                    { "label": "Prevalence", "value": "prevalence" },
                                    { "label": "Scale by viral load", "value": "viral" },
                                    { "label": "Scale by cases", "value": "cases" },
                                ],
                                value="prevalence",
                                style={ "width": "50%", "justifyContent": "flex-start" }
                            ),
                                dbc.RadioItems(
                                    id="smooth-radio",
                                    className="btn-group",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-outline-primary",
                                    labelCheckedClassName="active",
                                    options=[
                                        { "label": "Raw data", "value": False },
                                        { "label": "Smoothed", "value": True },

                                    ],
                                    value=True,
                                    style={ "width": "50%", "justifyContent": "flex-end" }
                                )],
                        ),
                        html.Div(
                            dcc.Graph(
                                id="wastewater-seq-graph",
                                config={"displayModeBar" : False},
                            ),
                            style={ "height": "30em", "margin" : "auto" }
                        )
                    ],
                ),
                html.P(),
                html.Div( id="top-table-div", style={ "width"        : "33em",
                                                      "marginLeft"   : "auto",
                                                      "marginRight"  : "auto",
                                                      "marginBottom" : "25px" } ),
            ]
        ),
        html.Br(),
        html.Br(),
        html.P( id="commit-date", style={ 'textAlign': 'center' }

        ),

        html.Div( [
            html.H4( "ZIP Codes" ),
            dcc.Graph(
                id="zip-graph",
                config={"displayModeBar" : False},
                style={ "height"  : "25em" }
            ) ],
            id="zip-div",
            className="pretty_container",
            style={ "marginLeft" : "auto",
                    "marginRight" : "auto" }
        ) 


        
    ]
    return layout