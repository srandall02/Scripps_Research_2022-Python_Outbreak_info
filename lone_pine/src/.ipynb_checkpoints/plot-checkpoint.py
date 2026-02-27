import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from epiweeks import Week
from scipy.signal import savgol_filter
from scipy.special import betaincinv

from src.variants import VOC, VOI
import datetime

COLOR_DARK = "#495057"
COLOR_LIGHT = "#93aad3"

def _add_date_formatting_minimum( fig ):
    fig.update_layout( template="simple_white",
                       hovermode="x unified",
                       xaxis=dict( hoverformat="%B %d, %Y" ),
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={"r":0,"t":0,"l":0,"b":0},
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)" ) )

def _add_date_formating( fig, minimum, maximum, ylims, ytitle, ytype="linear", skip=1 ):
    min_date = pd.to_datetime( f"{minimum.year}-{minimum.month}-01" )
    maximum += pd.DateOffset( months=1 )
    max_date = pd.to_datetime( f"{maximum.year}-{maximum.month}-01" )

    fig.update_yaxes(
        type=ytype,
        title=f"<b>{ytitle}</b>",
        showgrid=True,
        showline=True,
        ticks="" )
    fig.update_xaxes(
        dtick=f"M{skip}",
        tickformat="%b\n%Y",
        mirror=True,
        showline=False,
        ticks="",
        showgrid=True,
        range=("2020-01-01", max_date )
    )
    fig.update_xaxes( showline=True, mirror=False )

    if ytype == "log":
        fig.update_yaxes( dtick=1 )
    if ylims:
        fig.update_yaxes( range=ylims )
    _add_date_formatting_minimum( fig )

def get_date_limits( series ):
    # Max
    year = series.max().year
    month = series.max().month + 1
    if month == 13:
        month = 1
        year += 1
    day = 1
    max_lim = pd.to_datetime( f"{year}-{month}-{day}" )

    # min
    year = series.min().year
    month = series.min().month
    day = 1
    min_lim = pd.to_datetime( f"{year}-{month}-{day}" )
    return [min_lim, max_lim]

def plot_daily_cases_seqs( df ):
    #df.to_csv( "/Users/natem/Downloads/temp_presentation/daily_cases.csv" )
    fig = go.Figure()
    fig.add_trace( go.Scattergl( x=df["date"], y=df["new_cases"],
                                 mode='markers',
                                 name='Daily Cases',
                                 marker={ "color" : COLOR_DARK } ) )
    fig.add_trace(go.Scattergl(x=df["date"], y=df["new_sequences"],
                               mode='markers',
                               name='Daily Sequences',
                               marker={ "color" : COLOR_LIGHT} ) )

    min_lim = np.floor( np.log10( 0.75 ) )
    max_lim = np.ceil( np.log10( df["new_cases"].max() ) )
    _add_date_formating( fig, minimum=pd.to_datetime( "2020-01-01" ), maximum=df["date"].max(), ytype="log", ylims=[min_lim, max_lim], ytitle="Number of cases", skip=6 )

    return fig

def plot_cummulative_cases_seqs( df ):
    #df.to_csv( "/Users/natem/Downloads/presentation/cum_cases.csv" )
    fig = go.Figure()
    fig.add_trace( go.Scattergl( x=df["date"], y=df["cases"],
                               mode='lines',
                               name='Reported',
                               hovertemplate='%{y:,.0f}',
                               line={ "color" : COLOR_DARK, "width" : 4 } ) )
    fig.add_trace(go.Scattergl(x=df["date"], y=df["sequences"],
                               mode='lines',
                               name='Sequenced',
                               hovertemplate='%{y:,.0f}',
                               line={ "color" : COLOR_LIGHT, "width" : 4 } ) )

    min_lim = np.floor( np.log10( df.loc[df["sequences"] > 0,"sequences"].min() ) )
    max_lim = np.ceil( np.log10( df["cases"].max() ) )
    _add_date_formating( fig, minimum=pd.to_datetime( "2020-01-01" ), maximum=df["date"].max(), ytype="log",
                         ylims=[min_lim, max_lim], ytitle="Cummulative cases", skip=6 )

    return fig

def plot_cummulative_sampling_fraction( df ):
    df["epiweek"] = df["date"].apply( lambda x: Week.fromdate(x).startdate() )
    plot_df = df.groupby( "epiweek" ).agg( new_cases = ("new_cases", "sum"), new_sequences = ("new_sequences", "sum" ) )
    plot_df = plot_df.loc[plot_df["new_sequences"]>0]
    plot_df["fraction"] = plot_df["new_sequences"] / plot_df["new_cases"]
    plot_df = plot_df.reset_index()

    #plot_df.to_csv( "/Users/natem/Downloads/presentation/sampling_fraction.csv" )

    fig = go.Figure()
    fig.add_trace( go.Scattergl( x=plot_df["epiweek"], y=plot_df["fraction"],
                                 mode='lines',
                                 name='Fraction',
                                 line={ "color" : COLOR_DARK, "width" : 4 } ) )

    _add_date_formating( fig, minimum=pd.to_datetime( "2020-01-01" ), maximum=plot_df["epiweek"].max(), ytype="log",
                         ylims=[], ytitle="Cases sequenced (%)", skip=6 )
    fig.update_layout(  yaxis_tickformat='.1%' )
    fig.update_yaxes( dtick="D2" )

    return fig

def add_missing_to_color_scale( scale, color="white" ):
    return_list = [[0, color],
                   [0.01, color]]
    len_scale = len( scale ) - 1
    for i, col in enumerate( scale ):
        if i == 0:
            return_list.append( [0.01, col] )
        else:
            return_list.append( [( 1 / len_scale ) * i, col] )
    return return_list

def plot_lineages_time( df, lineage=None, scaleby="fraction" ):
    plot_df = df.pivot_table( index="epiweek", columns="lineage", values="ID", aggfunc="count" )
    plot_df = plot_df.fillna( 0 )

    yaxis_label = "Sequences"

    if scaleby == "fraction":
        plot_df = plot_df.apply( lambda x: x / x.sum(), axis=1 )
        yaxis_label += " (%)"

    max_lim = np.round( plot_df.sum( axis=1 ).max() * 1.05 )

    fig = go.Figure()
    if lineage is not None:
        focus_df = plot_df[lineage]
        plot_df = plot_df.drop( columns=lineage )
        plot_df = plot_df.sum( axis=1 )
        plot_df = pd.concat( [focus_df, plot_df], axis=1 )
        plot_df.columns = [lineage, "all"]
        fig.add_trace( go.Bar( x=plot_df.index, y=plot_df[lineage], name=lineage, marker_color=COLOR_LIGHT ) )
    else:
        plot_df = plot_df.sum(axis=1).reset_index()
        plot_df.columns = ["epiweek", "all"]
        plot_df = plot_df.set_index( "epiweek" )

    fig.add_trace( go.Bar( x=plot_df.index, y=plot_df["all"], name="All", marker_color=COLOR_DARK ) )
    fig.update_layout(barmode='stack' )
    _add_date_formating( fig, minimum=pd.to_datetime( "2020-01-01" ), maximum=plot_df.index.max(), ylims=[0, max_lim], ytitle=yaxis_label )

    if scaleby == "fraction":
        fig.update_layout( yaxis_tickformat='.1%',
                           legend=dict( bgcolor="white" ) )

    return fig

def plot_voc( df, scaleby="fraction", focus="VOC" ):
    plot_df = df.pivot_table( index="epiweek", columns="lineage", values="state", aggfunc="count", fill_value=0 ).T
    plot_df["VOC"] = plot_df.index.map( VOC )
    plot_df.loc[plot_df["VOC"].isna(),"VOC"] = "Other"

    if focus != "VOC":
        other_df = plot_df.loc[~plot_df["VOC"].str.startswith( focus )]
        other_df = other_df.drop( columns="VOC" ).sum()
        other_df.name = "Other"

        focus_df = plot_df.loc[plot_df["VOC"].str.startswith( focus )]
        focus_df = focus_df.drop( columns="VOC" ).T
        focus_df = focus_df.reindex( columns=focus_df.sum().sort_values( ascending=False ).index )
        focus_top = focus_df.iloc[:,:5]
        focus_bottom = focus_df.iloc[:,5:].sum( axis=1)
        focus_bottom.name = "Other"
        focus_df = pd.concat( [focus_top, focus_bottom], axis=1 )
        focus_df = focus_df.rename(columns={"Other" : f"Other {focus} lineages"} )

        plot_df = pd.concat( [focus_df,other_df], axis=1 )

    else:
        plot_df = plot_df.groupby( "VOC" ).agg( "sum" ).T

        order = plot_df.sum().sort_values( ascending=False ).index.to_list()
        order.remove( "Other" )
        order.append( "Other" )

        plot_df = plot_df.reindex( columns=order )

    yaxis_label = "Sequences"
    if scaleby == "fraction":
        plot_df = plot_df.apply( lambda x: x / x.sum(), axis=1 )
        yaxis_label += " (%)"

    max_lim = np.round( plot_df.sum( axis=1 ).max() * 1.05 )

    fig = go.Figure()
    for i, j in enumerate( plot_df ):
        if j == "Other":
            color = COLOR_DARK
        else:
            color = px.colors.colorbrewer.Dark2[i]
        fig.add_trace( go.Bar( x=plot_df.index, y=plot_df[j], name=j, marker_color=color ) )

    fig.update_layout( barmode='stack' )

    _add_date_formating( fig, minimum=pd.to_datetime( "2020-01-01" ), maximum=plot_df.index.max(), ylims=[0, max_lim], ytitle=yaxis_label )
    fig.update_layout( legend=dict( bgcolor="rgba(256,256,256,256)" ) )
    if scaleby == "fraction":
        fig.update_layout( yaxis_tickformat='.1%',
                           legend=dict( bgcolor="white" ) )
    return fig

def plot_delta( df, scaleby="fraction" ):
    plot_df = df.pivot_table( index="epiweek", columns="lineage", values="state", aggfunc="count", fill_value=0 ).T
    plot_df["VOC"] = plot_df.index.map( VOC )
    plot_df.loc[plot_df["VOC"].isna(),"VOC"] = "Other"

    other_df = plot_df.loc[~plot_df["VOC"].str.startswith( "Delta" )]
    other_df = other_df.drop( columns="VOC" ).sum()
    other_df.name = "Other"

    delta_df = plot_df.loc[plot_df["VOC"].str.startswith( "Delta" )]
    delta_df = delta_df.drop( columns="VOC" ).T
    delta_df = delta_df.reindex( columns=delta_df.sum().sort_values( ascending=False ).index )
    delta_top = delta_df.iloc[:,:5]
    delta_bottom = delta_df.iloc[:,5:].sum( axis=1)
    delta_bottom.name = "Other"
    delta_df = pd.concat( [delta_top, delta_bottom], axis=1 )
    delta_df = delta_df.rename(columns={"Other" : "Other Delta lineages"} )

    plot_df = pd.concat( [delta_df,other_df], axis=1 )

    yaxis_label = "Sequences"
    if scaleby == "fraction":
        plot_df = plot_df.apply( lambda x: x / x.sum(), axis=1 )
        yaxis_label += " (%)"

    max_lim = np.round( plot_df.sum( axis=1 ).max() * 1.05 )

    fig = go.Figure()
    for i, j in enumerate( plot_df ):
        if j == "Other":
            color = COLOR_DARK
        else:
            color = px.colors.colorbrewer.Dark2[i]
        fig.add_trace( go.Bar( x=plot_df.index, y=plot_df[j], name=j, marker_color=color ) )

    fig.update_layout( barmode='stack' )

    _add_date_formating( fig, minimum=pd.to_datetime("2020-01-01"), maximum=plot_df.index.max(), ylims=[0, max_lim], ytitle=yaxis_label )
    fig.update_layout( legend=dict( bgcolor="rgba(256,256,256,256)" ) )
    return fig


def plot_lineages( df ):

    plot_df = df["lineage"].value_counts().reset_index()

    colors = list()
    for i in plot_df["index"]:
        if i in sorted( VOI.keys() ):
            colors.append( "#4977CE" )
        elif i in sorted( VOC.keys() ):
            colors.append( "#925c37" )
        else:
            colors.append( COLOR_DARK )

    fig = go.Figure()
    fig.add_trace( go.Bar( x=plot_df["index"], y=plot_df["lineage"], marker_color=colors ) )
    fig.update_yaxes( showgrid=True, title="<b>Number of sequences</b>" )
    fig.update_xaxes( title="<b>PANGO lineage</b>" )

    if len( plot_df ) > 50:
        fig.update_xaxes( range=[-0.5, 50.5] )
    else:
        fig.update_xaxes( range=[-0.5, len( plot_df ) - 0.5] )

    fig.update_layout( template="simple_white",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={"r":0,"t":0,"l":0,"b":0},
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)" ) )
    return fig

def plot_zips( df, colorby="sequences" ):
    fig = go.Figure()
    fig.add_trace( go.Bar( x=df["ziptext"], y=df[colorby], marker_color=COLOR_DARK ) )

    if colorby == "fraction":
        title="Cases sequenced (%)"
        fig.update_layout( yaxis_tickformat='.1%' )
    else:
        title="Number of sequences"

    max_lim = df[colorby].max() * 1.05
    if colorby == 'sequences':
        max_lim = np.round( max_lim )
    fig.update_yaxes( showgrid=True, title=f"<b>{title}</b>", range=[0,max_lim] )
    fig.update_xaxes( title="<b>ZIP code</b>", type="category", categoryorder="total descending" )
    if (df['sequences']>0).sum() > 65:
        fig.update_xaxes( range=[-0.5, 65.5] )
    else:
        fig.update_xaxes( range=[-0.5, (df['sequences']>0).sum() - 0.5] )
    fig.update_layout( template="simple_white",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={"r":0,"t":0,"l":0,"b":0},
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)" ) )
    return fig


def binom_conf_interval(k, n, confidence_level=0.95 ):
    alpha = 1.0 - confidence_level
    k = np.asarray( k ).astype( int )
    n = np.asarray( n ).astype( int )
    lowerbound = betaincinv( k + 0.5, n - k + 0.5, 0.5 * alpha )
    upperbound = betaincinv( k + 0.5, n - k + 0.5, 1.0 - 0.5 * alpha )
    if lowerbound.ndim == 0:
        if k == 0:
            lowerbound = 0.0
        elif k == n:
            upperbound = 1.0
    else:
        lowerbound[k == 0] = 0
        upperbound[k == n] = 1

    return pd.Series( [lowerbound, upperbound] )

def plot_sgtf( sgtf_data ):
    plot_df = sgtf_data[0]
    plot_df["week"] = plot_df["Date"].apply( lambda x: Week.fromdate( x ).startdate() )
    plot_df = plot_df.groupby( "week" )[["sgtf_all", "sgtf_likely", "sgtf_unlikely", "total_positive"]].agg( sum )
    plot_df["percent"] = plot_df["sgtf_all"] / plot_df["total_positive"]
    plot_df[["lower", "upper"]] = plot_df.apply( lambda x: binom_conf_interval( x["sgtf_all"], x["total_positive"] ), axis=1 )
    plot_df = plot_df.reset_index()

    max_lim = np.round( plot_df["total_positive"].max() * 1.05 )

    fig = make_subplots( specs=[[{"secondary_y" : True}]] )
    fig.add_trace( go.Bar( x=plot_df["week"], y=plot_df["sgtf_likely"], name="SGTF <=30 Ct", marker_color="#E69F00" ), secondary_y=False )
    fig.add_trace( go.Bar( x=plot_df["week"], y=plot_df["sgtf_unlikely"], name="SGTF >30 Ct", marker_color="#009E73" ), secondary_y=False )
    fig.add_trace( go.Bar( x=plot_df["week"], y=plot_df["total_positive"] - plot_df["sgtf_likely"] - plot_df["sgtf_unlikely"], name="Total positive", marker_color="#56B4E9" ), secondary_y=False )
    fig.add_trace( go.Scattergl( x=plot_df["week"], y=plot_df["percent"],
                                 mode='lines',
                                 name='SGTF (%)',
                                 showlegend=False,
                                 line={ "color" : "#000000", "width" : 2, "dash" : "dash"} ), secondary_y=True )
    fig.add_trace( go.Scatter( x=plot_df["week"], y=plot_df["lower"],
                               mode='lines',
                               fillcolor="#E4E4E4",
                               showlegend=False,
                               hoverinfo='skip',
                               line={"color" : "#E4E4E4", "width" : 0 } ), secondary_y=True )
    fig.add_trace( go.Scatter( x=plot_df["week"], y=plot_df["upper"],
                               mode='lines',
                               fill="tonextx",
                               fillcolor="rgba(0,0,0,0.1)",
                               showlegend=False,
                               hoverinfo='skip',
                               line={"color" : "#E4E4E4", "width" : 0 } ), secondary_y=True )
    fig.update_layout( barmode='stack' )
    fig.update_yaxes( showgrid=True, title=f"<b>Tests</b>", range=[0,max_lim], secondary_y=False )
    fig.update_yaxes( showgrid=False, title=f"<b>SGTF (%)</b>", secondary_y=True, range=[-0.01,1.01] )

    fig.update_xaxes( dtick="M2", tickformat="%b\n%Y", mirror=True, showline=False, ticks="", showgrid=True )
    fig.update_yaxes( mirror=True, secondary_y=False, showline=False, ticks="" )
    fig.update_yaxes( tickformat='.0%', secondary_y=True, showline=False, ticks="" )
    fig.update_layout( template="simple_white",
                       hovermode="closest",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       xaxis=dict( hoverformat="%b %d, %Y" ),
                       margin={"r":0,"t":40,"l":0,"b":0},
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(255,255,255,0.8)" ) )

    return fig


def plot_sgtf_estiamte( sgtf_data ):
    plot_df = sgtf_data[1]
    plot_df.loc[plot_df["date"]<"2024-01-01"]
    shade = "#E4E4E4"
    fig = go.Figure()
    fig.add_trace( go.Scattergl( x=sgtf_data[0]["Date"], y=sgtf_data[0]["percent_filter"],
                                 mode='markers',
                                 name='SGTF (%)',
                                 showlegend=False,
                                 hoverinfo='skip',
                                 marker={ "color" : "#56B4E9", "size" : 12 } ) )
    fig.add_trace( go.Scattergl( x=plot_df["date"], y=plot_df["fit_y"],
                                 mode='lines',
                                 name='SGTF (%)',
                                 showlegend=False,
                                 line={ "color" : "#000000", "width" : 2} ) )
    fig.add_trace( go.Scatter( x=plot_df["date"], y=plot_df["fit_lower"],
                               mode='lines',
                               fillcolor=shade,
                               showlegend=False,
                               hoverinfo='skip',
                               line={"color" : shade, "width" : 0} ) )
    fig.add_trace( go.Scatter( x=plot_df["date"], y=plot_df["fit_upper"],
                               mode='lines',
                               fill="tonextx",
                               fillcolor="rgba(0,0,0,0.1)",
                               showlegend=False,
                               hoverinfo='skip',
                               line={"color" : shade, "width" : 0} ) )

    fig.update_xaxes( dtick="M2", tickformat="%b\n%Y", mirror=True, showline=False, ticks="", tickangle=0, showgrid=True )
    fig.update_yaxes( mirror=True, tickformat='.0%', showline=False, ticks="" )
    fig.update_yaxes( showgrid=True, title=f"<b>SGTF (%)</b>", range=[-0.01,1.01] )
    fig.update_layout( template="simple_white",
                       hovermode="closest",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       xaxis=dict( hoverformat="%b %d, %Y" ),
                       margin={"r":0,"t":40,"l":0,"b":0},
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(255,255,255,0.8)" ) )
    today = datetime.datetime.today()
    max_date = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    # max_date = pd.to_datetime( "2023-08-01" )
    fig.update_xaxes( range=["2021-11-25", "2025-01-01"] ) # if you want automatic, use max_date.strftime( "%Y-%m-%d")

    esti = sgtf_data[2]

    # Use these when SGTF is increasing.
    double_str =  f"Doubling time (days): {esti['doubling_time'][0]:.1f} ({esti['doubling_time'][2]:.1f}–{esti['doubling_time'][1]:.1f})<br>"
    growth_str =  f"Daily growth rate: {esti['growth_rate'][0]:.1%} ({esti['growth_rate'][1]:.1%}–{esti['growth_rate'][2]:.1%})<br>"
    transmission_str =  f"Transmission increase: {esti['transmission_increase'][0]:.0%} ({esti['transmission_increase'][1]:.0%}–{esti['transmission_increase'][2]:.0%})<br>"

    # Use these when SGTF is decreasing.
    #double_str = f"Halving time (days): {esti['doubling_time'][0]:.1f} ({esti['doubling_time'][2]:.1f}–{esti['doubling_time'][1]:.1f})<br>"
    #growth_str = f"Daily decline rate: {esti['growth_rate'][0]:.1%} ({esti['growth_rate'][1]:.1%}–{esti['growth_rate'][2]:.1%})<br>"
    #transmission_str = f"Transmission decrease: {esti['transmission_increase'][0]:.0%} ({esti['transmission_increase'][1]:.0%}–{esti['transmission_increase'][2]:.0%})<br>"

    for col, name in [("date50", "50%"), ("date99", "99%")]:
        date_str = f"{name}: {esti[col][0].strftime( '%b %d' )}<br>({esti[col][1].strftime( '%b %d' )}–{esti[col][2].strftime( '%b %d' )})"
        midpoint =  pd.to_datetime( sgtf_data[2][col]["estimate"] ).timestamp() * 1000
        fig.add_vline( midpoint, line_color="#ff6a6a", line_dash="dash", opacity=1, line_width=2 )
        align = "right" if name == "50%" else "center"
        fig.add_annotation( x=midpoint, y=1.10, yref="paper", text=date_str, showarrow=False, font={"color" : "#ff6a6a"}, align=align, xanchor=align )


    y_scale = 0.75
    x_place = "2021-12-10"
    bgcolor = "rgba(255,255,255,0.8)"
    fig.add_annotation( x=x_place, y=0.2 + y_scale, text=double_str, showarrow=False, xanchor="left", bgcolor=bgcolor )
    fig.add_annotation( x=x_place, y=0.15 + y_scale, text=growth_str, showarrow=False, xanchor="left", bgcolor=bgcolor )
    fig.add_annotation( x=x_place, y=0.1 + y_scale, text=transmission_str, showarrow=False, xanchor="left", bgcolor=bgcolor )

    return fig

def plot_catchment_areas( sd_map ):
    fig = px.choropleth( sd_map, geojson=sd_map.geometry, locations=sd_map.index, color="Wastewater_treatment_plant",
                         labels={ "ZIP": "Zip code", "Wastewater_treatment_plant": "Catchment area" },
                         hover_data=["Wastewater_treatment_plant"],
                         category_orders={ "Encina": 0, "Point Loma": 1, "South Bay": 2, "Other": 3 },
                         color_discrete_map={ "Encina": "#009E73", "Point Loma": "#56B4E9", "South Bay": "#D55E00",
                                              "Other": "#dddddd" },
                         projection="mercator", basemap_visible=False, fitbounds="geojson", scope=None )
    fig.update_geos( bgcolor="#ffffff" )
    fig.update_layout( template="simple_white",
                       autosize=True,
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={ "r": 0, "t": 0, "l": 0, "b": 0 },
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)",
                                    itemsizing='constant' ) )
    return fig

def plot_wastewater( ww, seqs, cases, scale="linear", source="PointLoma", seq_indicator=True ):
    fig = make_subplots( specs=[[{"secondary_y" : True}]] )

    seqs_filter = seqs.loc[seqs["source"]==source]
    seq_min = seqs_filter.index.min()
    seq_max = seqs_filter.index.max()

    # subset wastewater data
    subset_ww = ww.loc[ww["source"]==source]
    date_range = get_date_limits( subset_ww["date"] )
    if source != "PointLoma":
        date_range[0] = "2022-01-01"

    cases = cases.loc[cases.index > ww["date"].min() ]

    #fig.add_trace( go.Scattergl( x=cases.index, y=cases["reported_cases"],
    #                             name="Reported cases",
    #                             mode="markers",
    #                             hoverinfo="skip",
    #                             visible=False,
    #                             showlegend=True,
    #                             marker={"color" : "#D55E00", "size" : 8 } ), secondary_y=True )
    fig.add_trace( go.Scattergl( x=cases.dropna().index, y=cases.dropna()["reported_cases_rolling"]*100000,
                                 name="Reported cases per 100,000",
                                 mode="lines",
                                 hovertemplate="%{y:,.0f}",
                                 showlegend=True,
                                 line={"color" : "#D55E00", "width" : 3 } ), secondary_y=True )
    fig.add_trace( go.Scattergl( x=subset_ww["date"], y=subset_ww["gene_copies"],
                                 name="Viral load in wastewater",
                                 mode="markers",
                                 hovertemplate="%{y:,.0f}",
                                 marker={"color" : "#56B4E9", "size" : 8 } ), secondary_y=False )
    fig.add_trace( go.Scattergl( x=subset_ww["date"], y=subset_ww["gene_copies_rolling"],
                                 showlegend=False,
                                 name="Viral load in wastewater",
                                 mode="lines",
                                 hoverinfo="skip",
                                 line={"color" : "#56B4E9", "width" : 3 } ), secondary_y=False )
    if seq_indicator:
        fig.add_vrect( x0=seq_min, x1=seq_max, fillcolor="#e9eef6", opacity=0.5, annotation_text="*Sequence data available", annotation_borderpad=10, annotation_position="top left", layer="below" )



    fig.update_yaxes( showgrid=True, title=f"<b>Mean viral gene copies / Liter</b>", tickfont=dict(color="#56B4E9"), title_font=dict(color="#56B4E9"), secondary_y=False, showline=False, ticks="", type=scale )
    fig.update_yaxes( showgrid=False, title=f"<b>Reported cases / 100,000</b>", tickfont=dict(color="#D55E00"), title_font=dict(color="#D55E00"), secondary_y=True, showline=False, ticks="", type=scale )
    fig.update_xaxes( dtick="M1", tickformat="%b\n%Y", mirror=True, showline=False, ticks="", range=date_range )

    if scale == "linear":
        ww_range = [-subset_ww["gene_copies"].max()*0.05, subset_ww["gene_copies"].max()*1.05]
        cases_range = [-cases["reported_cases_rolling"].max()*100000*0.05, cases["reported_cases_rolling"].max()*100000*1.05]
        fig.update_yaxes( secondary_y=False, range=ww_range )
        fig.update_yaxes( secondary_y=True, range=cases_range)

    fig.update_layout( template="simple_white",
                       hovermode="x unified",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={"r":0,"t":0,"l":0,"b":0},
                       xaxis=dict( hoverformat="%B %d, %Y" ),
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)",
                                    itemsizing='constant') )

    return fig

def plot_monkeypox_concentration( mx_gene: pd.DataFrame, mx_cases: pd.DataFrame, scale: str = "linear", source: str = "PointLoma" ):
    subset_ww = mx_gene.loc[mx_gene["source"] == source]
    date_range = get_date_limits( subset_ww["date"] )

    fig = make_subplots( specs=[[{"secondary_y" : True}]] )

    # Concentration plot
    fig.add_trace( go.Scattergl( x=mx_cases["date"], y=mx_cases["cases_rolling"],
                                 name="Reported cases",
                                 mode="lines",
                                 hovertemplate="%{y:,.0f}",
                                 showlegend=True,
                                 legendgroup="b",
                                 line={"color" : "#D55E00", "width" : 3 } ), secondary_y=True )
    fig.add_trace( go.Scattergl( x=subset_ww["date"], y=subset_ww["copies"],
                                 name="Viral load in wastewater",
                                 showlegend=False,
                                 mode="markers",
                                 hovertemplate="%{y:f}",
                                 marker={ "color": "#56B4E9", "size": 10 } ), secondary_y=False )
    fig.add_trace( go.Scattergl( x=subset_ww["date"], y=subset_ww["copies_rolling"],
                                 showlegend=True,
                                 legendgroup="b",
                                 name="Viral load in wastewater",
                                 mode="lines",
                                 hoverinfo="skip",
                                 line={ "color": "#56B4E9", "width": 3 } ), secondary_y=False)
    fig.add_trace( go.Scattergl( x=subset_ww.loc[subset_ww["copies"]==0, "date"], y=subset_ww.loc[subset_ww["copies"]==0, "copies"],
                               name="Below detection limit",
                               mode='markers',
                               hoverinfo="skip",
                               legendgroup="b",
                               marker=dict( size=6, color="white", line=dict( width=0.5, color="#56B4E9" ) ) ) )

    fig.update_yaxes( showgrid=True, title=f"<b>MPX copies / PMMoV copies</b>", tickfont=dict( color="#3C5C94" ), tickformat="f",
                      title_font=dict( color="#3C5C94" ), secondary_y=False, showline=False, ticks="", type=scale, )
    fig.update_yaxes( showgrid=False, title=f"<b>Reported cases</b>", tickfont=dict( color="#D55E00" ),
                      title_font=dict( color="#D55E00" ), secondary_y=True, showline=False, ticks="", type=scale, range=(-0.9,13) )
    fig.update_xaxes( dtick="1209600000", tickformat="%b\n%d", mirror=True, showline=False, ticks="", range=date_range)

    fig.update_layout( template="simple_white",
                       hovermode="x unified",
                       plot_bgcolor="#ffffff",
                       paper_bgcolor="#ffffff",
                       margin={ "r": 0, "t": 0, "l": 0, "b": 0 },
                       xaxis=dict( hoverformat="%B %d, %Y" ),
                       legend=dict( yanchor="top",
                                    y=0.99,
                                    xanchor="left",
                                    x=0.01,
                                    bgcolor="rgba(0,0,0,0)",
                                    itemsizing='constant' ) )

    return fig

##### The code that creates/returns the wastewater_area plot; replicate this in a new function beneath this
## From wastewater page copy code from line 92 on into main page -- this is the code for the area plot
## Add (copy/paste the callback code
## In callbacks copy code starting from 290 for the wastewater plot
## Use load_seqs (line  from format_resources to get your data, perhaps make code similar to what is seen in load_wastewater_data (line 307)
## We need to conect the selections with Zipcode data instead of locations in wastewater.

def plot_wastewater_seqs( ww_data, seqs, cases, config, norm_type, source="PointLoma", smooth=True ) -> go.Figure:
    def hex_to_rgb( hex_color: str ) -> tuple:
        hex_color = hex_color.lstrip( "#" )
        if len( hex_color ) == 3:
            hex_color = hex_color * 2
        return int( hex_color[0:2], 16 ), int( hex_color[2:4], 16 ), int( hex_color[4:6], 16 )

    filtered_seqs = seqs.loc[seqs["source"]==source]

    plot_df = []
    for i in config.keys() :
        if i != "Other" :
            try:
                temp_sum = filtered_seqs[config[i]["members"]].sum( axis=1 )
            except KeyError:
                print( 'help"')
                exit()
            temp_sum.name = i
            plot_df.append( temp_sum )
    plot_df = pd.concat( plot_df, axis=1 )
    plot_df["Other"] = 100 - plot_df.sum( axis=1 )
    plot_df["Other"] = plot_df["Other"].clip( lower=0 )


    if smooth:
        plot_df = plot_df.apply( savgol_filter, window_length=21, polyorder=1 )
        #plot_df = plot_df.apply( lambda x: x.rolling( 14, min_periods=1, win_type="triang" ).mean() )
        plot_df = plot_df.clip( lower=0 )
        plot_df = plot_df.apply( lambda x:( x / x.sum()) * 100, axis=1  )

    norm=None
    ht = "%{y:.0f}"

    if norm_type == "viral":
        norm = "gene_copies_rolling"
        yaxis_label = "<b>Variant copies / Liter</b>"
        ticksuffix = ""
        yrange = None
    elif norm_type == "cases":
        ww_data = ww_data.merge( cases, left_on="date", right_index=True, how="left" )
        ww_data["reported_cases_rolling"] = ww_data["reported_cases_rolling"] * ww_data["population"]
        norm="reported_cases_rolling"
        yaxis_label = "<b>Estimated cases<b>"
        ticksuffix = ""
        yrange = None
    elif norm_type == "prevalence":
        ht = "%{y:.0f}%"
        yaxis_label = "<b>Variant prevalence</b>"
        ticksuffix = "%"
        yrange = [0,100]

    if norm is not None:
        ww_data = ww_data.loc[ww_data["source"]==source]
        plot_df = plot_df.merge( ww_data[["date", norm]], left_index=True, right_on="date", how="left" )
        plot_df = plot_df.rename( columns={ "date" : "Date" } )
        plot_df = plot_df.dropna()
        plot_df = plot_df.set_index( "Date" )
        plot_df = plot_df.loc[:, plot_df.columns != norm].apply( lambda x : (x / 100) * plot_df[norm] )

    fig = go.Figure()

    fill_pattern = go.scatter.Fillpattern( bgcolor=config["Recombinants"]["color"], fgcolor="white", shape="/", solidity=0.5 )

    fig.add_trace(
        go.Scatter(
            x=plot_df.index, y=[0]*plot_df.shape[0],
            hoverinfo="skip",
            showlegend=False,
            fillcolor="black",
            line=dict( width=1, color="black" ),
            stackgroup='one'
        )
    )
    for i in reversed( list( config.keys() ) ):
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df[i],
                name=config[i]["name"],
                hovertemplate=ht,
                hoverinfo='x+y',
                mode='lines',
                fillcolor=f"rgba{(*hex_to_rgb(config[i]['color']), 0.65)}",
                line=dict( width=0.5, color=config[i]["color"] ),
                fillpattern=fill_pattern if i == "Recombinants" else None,
                stackgroup='one'
            )
        )
    fig.add_trace(
        go.Scatter(
            x=plot_df.index, y=[0]*plot_df.shape[0],
            hoverinfo="skip",
            showlegend=False,
            fillcolor="black",
            line=dict( width=1, color="black" ),
            stackgroup='one'
        )
    )
    fig.update_yaxes( showgrid=True, title=yaxis_label, range=yrange, tickformat='.0f',
                      ticksuffix=ticksuffix, showline=True, ticks="", mirror=True, linewidth=2 ) # Twice as wide because fake lineages adds with the x-axis
    fig.update_xaxes( dtick="M1", tickformat="%b\n%Y", mirror=True, showline=True, ticks="", showgrid=False, linewidth=1 )
    _add_date_formatting_minimum( fig )
    fig.update_layout( legend=dict( bgcolor="white" ) )
    fig.update_traces( mode="lines" )
    return fig