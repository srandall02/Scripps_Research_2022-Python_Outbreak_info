from dash import html, dcc
import src.plot as dashplot

def get_layout( sgtf_data ):
    markdown = """
    To gain insight into the spread of the Omicron variant in our community, we are working with a large number of 
    partners to track S-gene target failures (SGTFs). SGTFs are a feature of the TaqPath PCR assay that fails to detect
    the spike gene of certain variants of interest due to a deletion in these viruses' spike gene. Some Omicron 
    sequences, particularly BA.1, have this deletion while most Delta sequences and some Omicron sequences, particularly 
    BA.2, do not. Using this data, we estimate the prevalence of Omicron by fitting a logisitic growth mixture model to 
    this data. The data shown here is collected by our collaboring partners in San Diego and can be found on our 
    [GitHub repository](https://github.com/andersen-lab/SARS-CoV-2_SGTF_San-Diego). More information on Omicron and 
    other estimates of its prevalence in San Diego and elsewhere can be found at [Outbreak.info](https://outbreak.info/).
    """

    #commit_date = get_last_commit_date()
    #commit_date = "December 23 @ 3:47 PM PST"

    layout = [
        html.Div(
            [
                dcc.Markdown( markdown, link_target='_blank' ),
                html.Div( [
                    #html.H4( "S Gene Target Failure" ),
                    html.Div(
                        dcc.Graph(
                            figure=dashplot.plot_sgtf( sgtf_data ),
                            id="sgtf-graph",
                            config={"displayModeBar" : False},
                            style={"height" : "30em"}
                        ),
                        style={ 'width': '49%', 'display': 'inline-block' },
                        className="six columns",
                    ),
                    html.Div(
                        dcc.Graph(
                            figure=dashplot.plot_sgtf_estiamte( sgtf_data ),
                            id="sgtf-estimate",
                            config={"displayModeBar" : False},
                            style={ "height" : "30em",
                                    "marginLeft" : "20px" }
                        ),
                        style={ 'width': '49%', 'display': 'inline-block' },
                        className="six columns",
                    )
                ],
                    id="sgtf-div",
                    className="pretty_container",
                    style={ "marginLeft" : "auto",
                            "marginRight" : "auto" }
                ),
            ],
            className="row" ),
        html.Br(),
        html.Br(),
        html.P( id="commit-date", style={ 'textAlign': 'center' })
    ]

    return layout