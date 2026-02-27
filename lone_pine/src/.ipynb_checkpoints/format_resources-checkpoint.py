from typing import List
import os
import numpy as np
import pandas as pd
from dash import html
from epiweeks import Week

from src.variants import VOC, VOI
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
from numpy import exp, log
import geopandas as gpd

def load_sequences( window=None ):
    sequences = pd.read_csv( os.path.abspath("./resources/sequences.csv") )

    # Convert to dates correctly.
    sequences["collection_date"] = pd.to_datetime( sequences["collection_date"] ).dt.tz_localize( None )
    sequences["collection_date"] = sequences["collection_date"].dt.normalize()
    sequences["epiweek"] = pd.to_datetime( sequences["epiweek"] ).dt.tz_localize( None )
    sequences["epiweek"] = sequences["epiweek"].dt.normalize()

    sequences["zipcode"] = sequences["zipcode"].apply( lambda x: str(x).split( ":" )[0] )
    sequences["zipcode"] = sequences["zipcode"].replace(r'^\s*$', np.nan, regex=True)
    sequences["zipcode"] = sequences["zipcode"].apply( lambda x: f"{float( x ):.0f}" )

    if window is not None:
        sequences = sequences.loc[sequences["days_past"] <= window].copy()

    return sequences


def load_cases( window = None ):
    cases = pd.read_csv( os.path.abspath("./resources/new_cases.csv" ))

    # Convert to dates correctly.
    cases["updatedate"] = pd.to_datetime( cases["updatedate"] ).dt.tz_localize( None )
    cases["updatedate"] = cases["updatedate"].dt.normalize()

    if window is not None:
        cases = cases.loc[cases["days_past"] <= window].copy()
    return cases


def load_growth_rates():
    return pd.read_csv( os.path.abspath("./resources/growth_rates.csv" ))


def load_ww_growth_rates():
    return pd.read_csv( "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/rel_growth_rates.csv" )

def format_cases_total( cases_df ):
    return_df = cases_df.sort_values( "updatedate", ascending=False ).groupby( "ziptext" ).first()
    return_df = return_df.reset_index()
    return return_df.drop( columns=["days_past"] )

def get_seqs_per_case( time_series, seq_md, zip_f=None ):
    """ Combines timeseries of cases and sequences.
    Parameters
    ----------
    time_series
    seq_md
    zip_f

    Returns
    -------
    """
    if zip_f:
        if type( zip_f ) != list:
            zip_f = [zip_f]
        time_series = time_series.loc[time_series["ziptext"].isin(zip_f)]
    cases = time_series.pivot_table( index="updatedate", values="case_count", aggfunc="sum" )
    cases["case_count"] = np.maximum.accumulate( cases["case_count"] )
    cases = cases.reset_index()

    cases.columns = ["date", "cases"]

    cases = cases.merge( get_seqs( seq_md, zip_f=zip_f ), on="date", how="outer", sort=True )

    cases["new_sequences"] = cases["new_sequences"].fillna( 0.0 )
    cases["sequences"] = cases["new_sequences"].cumsum()
    cases["cases"] = np.maximum.accumulate( cases["cases"].fillna(0) )
    cases["new_cases"] = cases["cases"].diff()
    cases["new_cases"] = cases["new_cases"].fillna( 0.0 )
    cases.loc[cases["new_cases"] < 0,"new_cases"] = 0

    return cases

def get_seqs( seq_md, groupby="collection_date", zip_f=None ):
    """ Pivots the output of download_search().
    Parameters
    ----------
    seq_md : pandas.DataFrame
        output of download_search(); list of sequences attached to ZIP code and collection date.
    groupby : str
        column of seq_md to count.
    zip_f : bool
        indicates whether to filter sequences to a single zipcode.

    Returns
    -------
    pandas.DatFrame
    """
    if zip_f:
        seqs = seq_md.loc[seq_md["zipcode"].isin( zip_f )]
    else:
        seqs = seq_md

    seqs = seqs.groupby( groupby )["ID"].agg( "count" ).reset_index()
    if groupby == "collection_date":
        seqs.columns = ["date", "new_sequences"]
    elif groupby == "zipcode":
        seqs.columns = ["zip", "sequences"]

    return seqs

def format_zip_summary( cases, seqs ):
    """ Merges cummulate cases and sequences for each ZIP code.
    Parameters
    ----------
    cases : pandas.DataFrame
        output of format_cases_total( load_cases() ) containing the cummulative cases for each zip code.
    seqs : pandas.DataFrame
        output of download_search() or load_sequences() containing a lkist of sequences with ZIP code information.
    Returns
    -------
    pandas.DataFrame :
        DataFrame linking ZIP code to case counts, sequences, and fraction of cases sequenced. Use format_shapefile() if
        want GeoDataFrames.
    """
    cumulative_seqs = get_seqs( seqs, groupby="zipcode" )

    cumulative_seqs = cumulative_seqs.merge( cases[["ziptext", "case_count"]], left_on="zip", right_on="ziptext", how="right" )
    cumulative_seqs["sequences"] = cumulative_seqs["sequences"].fillna( 0.0 )
    cumulative_seqs["fraction"] = cumulative_seqs["sequences"] / cumulative_seqs["case_count"]
    cumulative_seqs.loc[cumulative_seqs["fraction"].isna(),"fraction"] = 0
    cumulative_seqs = cumulative_seqs.drop( columns=["zip"] )

    return cumulative_seqs

def get_lineage_values( seqs ):
    values = seqs["lineage"].dropna()
    values = values.sort_values().unique()

    return_dict = [{"label" : "All variants of concern", "value" : "all-voc" },
                   {"label" : "All Delta lineages", "value" : "all-delta" },
                   {"label" : "All Omicron lineages", "value" : "all-omicron" },
                   {"label" : " - Variants of concern" , "value" : "None", "disabled" : True}]
    for i in sorted( VOC.keys() ):
        if i in values:
            return_dict.append( { "label" : i, "value" : i } )

    return_dict.append( {"label" : " - Variants of interest" , "value" : "None", "disabled" : True} )
    for i in sorted( VOI.keys() ):
        if i in values:
            return_dict.append( { "label" : i, "value" : i } )

    return_dict.append( {"label" : " - PANGO lineages" , "value" : "None", "disabled" : True} )
    for i in values:
        if ( i not in VOC ) & ( i not in VOI ):
            return_dict.append( { "label" : i, "value" : i } )

    return return_dict

def get_summary_table( seqs ):
    sg = {"textAlign" : "center" }
    sd2 = {"marginLeft" : "50px" }
    table = [html.Tr( [html.Th( "Type", style={"marginLeft" : "20px" } ), html.Th( "Total", style=sg ), html.Th( "Last Month", style=sg )] ),
             html.Tr( [html.Td( html.B( "Sequences", style={"marginLeft" : "10px" } ) ), html.Td( len( seqs ), style=sg ), html.Td( len( seqs.loc[seqs['days_past'] < 30] ), style=sg )] ),
             html.Tr(html.Td( "", colSpan=3 ) ),
             html.Tr( html.Td( html.B( "Variants of concern", style={"marginLeft" : "10px" } ), colSpan=3))]

    vocs = seqs.copy()
    vocs["VOC"] = vocs["lineage"].map( VOC )
    vocs = vocs.loc[~vocs["VOC"].isna()]

    for i in vocs["VOC"].sort_values().unique():
        table.append( html.Tr( [html.Td( html.I( i, style={"marginLeft" : "20px" } ) ), html.Td( len( vocs.loc[vocs['VOC']==i] ), style=sg ), html.Td( len( vocs.loc[(vocs['VOC']==i)&(seqs['days_past']<30)] ), style=sg )] ) )

    # Brief hack to get Omicron in table
    #table.append( html.Tr(
    #    [html.Td( html.I( "Omicron-like", style={ "marginLeft": "20px" } ) ), html.Td( 0, style=sg ),
    #     html.Td( 0, style=sg )] ) )

    return table

def get_provider_sequencer_values( seqs, value ):
    labels = [{"label" : f"{i} ({j})", "value": i }for i, j in seqs[value].sort_values().value_counts().iteritems()]
    labels = sorted( labels, key=lambda x: x["label"] )
    return labels


def load_sgtf_data():
    """ Loads S-gene target failure data from file and fits a logistic growth mixture model. Data comes from clinical
    sequencing in San Diego. Logisitic growth mixture model is a summation of three logisitic growth models. Further
    versions might include a fourth model. Logisitic growth models are parameterized using logisitic growth rate and
    sigmoid midpoint.

    Returns
    -------
    tests : pandas.DataFrame
        Raw SGTF data, in terms of number of tests conducted with S-gene dropout.
    fits : pandas.DataFrame
        Estimated prevelence of SGTF using Logistic growth mixture model.
    estimates : pandas.DataFrame
        Estimates and confidence intervals for the growth rate, doubling time, and transmission advantage of the last component of the mixture model.

    """

    def lgm( ndays, x0, r ):
        return 1 / ( 1 + ( ( ( 1 / x0 ) - 1 ) * exp( -1 * r * ndays ) ) )

    def lgm_mixture( ndays, x0_1, r_1, x0_2, r_2, x0_3, r_3, x0_4, r_4, x0_5, r_5 ):
        return (lgm( ndays, x0_1, r_1 )
                - lgm( ndays, x0_2, r_2 )
                + lgm( ndays, x0_3, r_3 )
                - lgm( ndays, x0_4, r_4 )
                + lgm( ndays - 50, x0_5, r_5 ) )    # you didn't see anything.

    tests = pd.read_csv( "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_SGTF_San-Diego/main/SGTF_San_Diego_new.csv", parse_dates=["Date"] )
    tests = tests.dropna( how='all', axis=1 )
    tests.columns = ["Date", "sgtf_all", "sgtf_likely", "sgtf_unlikely", "no_sgtf", "total_positive", "percent_low", "percen_all"]
    tests = tests.loc[~tests["Date"].isna()]
    tests["percent"] = (tests["sgtf_all"] / tests["total_positive"]).fillna(0)
    tests["percent_filter"] = savgol_filter( tests["percent"], window_length=7, polyorder=2 )
    tests["ndays"] = tests["Date"].apply(lambda x: x.toordinal())
    tests["ndays"] = tests["ndays"] - min( tests["ndays"] ) + 1

    fit, covar = curve_fit(
        f=lgm_mixture,
        xdata=tests["ndays"],
        ydata=tests["percent_filter"],
        p0=[0.01, 0.1, 0.003, 0.1, 2e-7, 0.1, 1e-9, 0.1, 1e-11, 0.05],
        bounds=([0] * 10, [np.inf] * 10)
    )
    sigma_ab = np.sqrt( np.diagonal( covar ) )

    days_sim = 1500

    fit_df = pd.DataFrame( {"date" : pd.date_range( tests["Date"].min(), periods=days_sim ) } )
    fit_df["ndays"] = fit_df.index
    fit_df["fit_y"] = [lgm_mixture(i, *fit) for i in range( days_sim )]

    sigma_addition = sigma_ab
    # should be -1 when we want to include the term. I won't for now because the CI is so large.
    sigma_addition[4] *= -1
    sigma_addition[5] *= -1
    sigma_addition[8] *= -0.5   # sneaky little hack to get CIs
    sigma_addition[9] *= -1

    fit_df["fit_lower"] = [lgm_mixture( i, *(fit + sigma_addition) ) for i in range( days_sim )]
    fit_df["fit_upper"] = [lgm_mixture( i, *(fit - sigma_addition) ) for i in range( days_sim )]

    min_date = "2023-07-01"

    above_99 = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_y"] > 0.99),"date"].min()
    above_99_lower = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_lower"] > 0.99),"date"].min()
    above_99_upper = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_upper"] > 0.99),"date"].min()

    above_50 = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_y"] > 0.50),"date"].min()
    above_50_lower = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_lower"] > 0.50),"date"].min()
    above_50_upper = fit_df.loc[(fit_df["date"] > min_date)&(fit_df["fit_upper"] > 0.50),"date"].min()

    growth_rate = fit[9]
    serial_interval = 5.5

    estimates = pd.DataFrame( {
        "estimate" : [above_99, above_50, growth_rate],
        "lower" : [above_99_lower, above_50_lower, growth_rate + sigma_ab[5]],
        "upper" : [above_99_upper, above_50_upper, growth_rate - sigma_ab[5]] }, index=["date99", "date50", "growth_rate"] )
    estimates = estimates.T
    estimates["doubling_time"] = log(2) / estimates["growth_rate"]
    estimates["transmission_increase"] = serial_interval * estimates["growth_rate"]

    return tests, fit_df, estimates

def load_ww_individual( loc: str, source: str, date_col: str, value_col: str, columns: List[str], window_length: int ) -> pd.DataFrame:
    """ Loads wastewater qPCR data from file
    Parameters
    ----------
    loc : str
        Location of file
    source : str
        Name of the catchment area the file refers to. Will be encoded in the returned dataframe.
    date_col : str
        Name of column in file that contains the date.
    value_col : str
        Name of column in file that contains the qPCR measurements.
    columns : list[str]
        Values to replace column names in file. Bit of a hack...
    window_length : int
        Length of window to use for Savitzky-Golay filter.

    Returns
    -------
    pd.DataFrame
        DataFrame containing a time series of qPCR measurements for a given catchment area.
    """
    temp = pd.read_csv( loc, parse_dates=[date_col] )
    temp["source"] = source
    temp.columns = columns
    temp.loc[~temp[value_col].isna(), f"{value_col}_rolling"] = savgol_filter(
        temp[value_col].dropna(), window_length=window_length, polyorder=2 )

    return temp

def load_wastewater_data():
    def round_to_odd( value ):
        return np.ceil( np.floor( value ) / 2 ) * 2 - 1

    def load_seq_individul( loc, source ):
        temp = pd.read_csv( loc, parse_dates=["Date"], index_col="Date" )
        temp["source"] = source
        return temp

    titer_template = "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/{}_sewage_qPCR.csv"
    seqs_template = "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/{}_sewage_seqs.csv"
    locations = ["PointLoma", "Encina", "SouthBay"]

    qpcr_columns = ["date", "gene_copies", "source"]
    return_df = pd.concat( [load_ww_individual( loc=titer_template.format( loc ), source=loc, date_col="Sample_Date", value_col="gene_copies", columns=qpcr_columns, window_length=11 ) for loc in locations] )
    seqs = pd.concat( [load_seq_individul( seqs_template.format( loc ), loc ) for loc in locations] )

    return return_df, seqs

def load_catchment_areas():
    zip_loc = "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/Zipcodes.csv"
    zips = pd.read_csv( zip_loc, usecols=["Zip_code", "Wastewater_treatment_plant"] )

    sd = gpd.read_file( os.path.abspath("./resources/zips.geojson" ))

    sd = sd.merge( zips, left_on=["ZIP"], right_on=["Zip_code"], how="outer" )
    sd = sd.loc[~sd["geometry"].isna()]
    sd["geometry"] = sd.simplify( 0.002 )
    sd["Wastewater_treatment_plant"] = sd["Wastewater_treatment_plant"].fillna( "Other" )
    sd["ZIP"] = sd["ZIP"].apply( lambda x: f"{x:.0f}" )
    sd = sd.set_index( "ZIP" )
    return sd

def convert_rbg_to_tuple( rgb ):
    rgb = rgb.lstrip( "#" )
    return tuple( int( rgb[i :i + 2], 16 ) for i in (0, 2, 4) )

def convert_tuple_to_rgb( r, g, b ):
    return '#%02x%02x%02x' % (int(r), int(g), int(b))

def lighten_field( value, alpha, gamma=2.2 ):
    return pow( pow(255, gamma) * (1 - alpha) + pow( value, gamma ) * alpha, 1 / gamma)
def lighten_color( r, g, b, alpha, gamma=2.2 ):
    return lighten_field(r, alpha, gamma ), lighten_field( g, alpha, gamma ), lighten_field( b, alpha, gamma )
def load_ww_plot_config( delta=0.15 ):
    """ Loads the configuration file for the wastewater seqs plots. Essentially, the file specifies the name and color of
    lineages to be included.
    Returns
    -------
    dict
        Description of the name, lineage members, and color of each trace to be included in the plot.
    """
    import yaml
    from urllib import request

    try:
        config_url = request.urlopen( "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/plot_config.yml" )
        plot_config = yaml.load( config_url, Loader=yaml.FullLoader )
    except:
        print( "Unable to connect to remote config. Defaulting to local, potentially out-of-date copy." )
        with open( os.path.abspath("./resources/ww_seqs.yml"), "r" ) as f :
            plot_config = yaml.load( f, Loader=yaml.FullLoader )

    children_dict = dict()

    # Test the config is reasonable complete.
    assert "Other" in plot_config, "YAML is not complete. Does not contain 'Other' entry."
    for key in reversed( list( plot_config.keys() ) ):
        for value in ["name", "members"]:
            assert value in plot_config[key], f"YAML entry {key} is not complete. Does not contain '{value}' entry."
        if "color" not in plot_config[key]:
            assert "parent" in plot_config[key], f"YAML entry {key} is incomplete. Must specify either a 'color' or 'parent' entry."
            if plot_config[key]["parent"] in children_dict:
                children_dict[plot_config[key]["parent"]] += 1
            else:
                children_dict[plot_config[key]["parent"]] = 1
            child_idx = children_dict[plot_config[key]["parent"]]
            parent_color = plot_config[plot_config[key]["parent"]]["color"]
            parent_color = convert_rbg_to_tuple( parent_color )
            plot_config[key]["color"] = convert_tuple_to_rgb( *lighten_color( *parent_color, alpha=1.0-(delta*child_idx) ) )

    return plot_config

def load_monkeypox_data():
    titer_template = "https://raw.githubusercontent.com/andersen-lab/MPX_WasteWater_San-Diego/master/MPX_{}_qpcr.csv"
    locations = ["PointLoma", "Encina", "SouthBay"]
    data = pd.concat( [load_ww_individual( loc=titer_template.format( loc ), source=loc, date_col="date", value_col="copies", columns=["date", "source", "copies"], window_length=11 if loc=="PointLoma" else 3 ) for loc in locations] )
    data.loc[data["copies_rolling"] < 0, "copies_rolling"] = 0

    cases = pd.read_csv( "https://raw.githubusercontent.com/andersen-lab/MPX_WasteWater_San-Diego/master/MPX_cases.csv", parse_dates=["date"] )
    cases["cases"] = cases["cases"].diff().fillna(0)
    cases.loc[cases["cases"]<0,"cases"] = 0
    cases["week"] = cases["date"].apply( lambda x: Week.fromdate( x ).startdate() )
    cases = cases.groupby( "week" )["cases"].agg( "sum" )
    cases = cases.reindex( pd.date_range( cases.index.min(), cases.index.max() ) ).rename_axis( "date" ).reset_index()
    indexer = pd.api.indexers.FixedForwardWindowIndexer( window_size=7 )
    cases["cases"] = cases["cases"].fillna(0)
    cases["cases"] = cases.rolling( window=indexer, min_periods=1 )["cases"].apply( lambda x: x.max() / 7 )
    cases["cases_rolling"] = savgol_filter( cases["cases"], window_length=11, polyorder=2 )
    cases.loc[cases["cases_rolling"]<0,"cases_rolling"] = 0

    return data, cases
