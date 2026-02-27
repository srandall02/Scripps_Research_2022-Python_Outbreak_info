import os
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.dates as mdates
from subprocess import run
import json
from pango_aliasor.aliasor import Aliasor
import re
from scipy.special import expit, logit
import pickle

SEQS_LOCATION = os.path.abspath("../../resources/sequences.csv")
VOC_LOCATION = os.path.abspath("../../resources/voc.txt")

aliasor = Aliasor()

def load_cdc_variants():
    # This link provides API access to the data found in this chart: https://covid.cdc.gov/covid-data-tracker/#variant-proportions
    # However, I haven't confirmed this doesn't change over time.
    init_url = "https://data.cdc.gov/resource/jr58-6ysp.json"
    request = run( f"curl -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36' {init_url}", shell=True, capture_output=True, text=True )
    response = json.loads( request.stdout )

    variants = ["XBB.1.5", "XBB", "DQ.1"]
    for entry in response:
        if (entry["variant"] in variants) or (entry["variant"] == "Other"):
            continue
        variants.append( entry["variant"] )
    return variants

def load_sequences():
    seqs = pd.read_csv( SEQS_LOCATION, usecols=["ID", "collection_date", "epiweek", "lineage", "state"],
                       parse_dates=["collection_date", "epiweek"] )
    seqs = seqs.loc[seqs["state"] == "San Diego"]
    return seqs

def collapse_lineage( entry : str, accepted_lineages: set[str] ):
    if entry in accepted_lineages or "." not in entry:
        return entry
    elif re.match( "[A-Z]{2}.\\+$", entry ):
        return aliasor.partial_compress( aliasor.uncompress( entry ), accepted_aliases=["BA"] )
    return ".".join( entry.split( "." )[:-1] )


def calculate_CIs( entry, name, model ):
    return_df = entry.copy()
    se = model.cov_params().loc[name,name].to_numpy()
    se = np.sqrt( [xx@se@xx for xx in [[i, 1] for i in return_df.index]] )
    return_df["upper"] = expit( logit( return_df["prevalence"] ) + 1.96 * se )
    return_df["lower"] = expit( logit( return_df["prevalence"] ) - 1.96 * se )
    return return_df


def format_model_results( model_results, weeks : list ):
    results = pd.DataFrame( model_results.predict( [[i, 1] for i in weeks] ), index=weeks,
                            columns=model_results.model._ynames_map.values() )
    results = results.drop( columns=["Other"] )
    results = results.melt( var_name="variant", value_name="prevalence", ignore_index=False )
    results = results.groupby( "variant" ).apply( lambda x: calculate_CIs( x, x.name, model_results ) )
    return results


def model_sequence_counts( df : pd.DataFrame, weeks : list ):
    mdata = df.copy()
    mdata["const"] = 1
    X = mdata[["epiweek", "const"]]
    Y = mdata["collapsed_linege"]

    model = sm.MNLogit( Y, X, missing="drop" )
    res = model.fit_regularized( maxiter=1000 )

    results = format_model_results( res, weeks )

    return results, res


def calculate_growth_rate( results ):
    coeff = results.params.T
    coeff[["lower", "upper"]] = results._results.conf_int()[:, :1].reshape( -1, 2 )
    coeff.index = list( results.model._ynames_map.values() )[1:]
    coeff = coeff.drop( columns=["const"] )
    coeff = coeff.rename( columns={"epiweek" : "growth_rate" })
    return coeff

def dump_model_names( model, collapsed_names ):
    with open( os.path.abspath("../../resources/clinical.model"), "wb" ) as model_file:
        pickle.dump( model, model_file )
    with open( os.path.abspath("../../resources/collapsed_names.csv"), "w" ) as cn:
        cn.write( "lineage,collapsed_lineage\n" )
        [cn.write( f"{k},{v}\n" ) for k, v in collapsed_names.items()]

def smooth_sequence_counts( df : pd.DataFrame, weeks : list, forced_lineages : list[str], rounds : int = 10, min_sequences : int = 50 ):
    last_seqs = df.loc[df["epiweek"].isin( weeks )].copy()

    previous_round = "lineage"
    for i in range( rounds ):
        counts = last_seqs[previous_round].value_counts()
        accepted = set( list( counts.loc[counts > min_sequences].index ) + forced_lineages )
        last_seqs[f"round_{i}"] = last_seqs[previous_round].apply( lambda x: collapse_lineage( x, accepted ) )

        previous_round = f"round_{i}"
        counts = last_seqs[previous_round].value_counts()
        print(
            f"Round {i} allowed {len( set( list( counts.loc[counts > min_sequences].index ) + forced_lineages ) )} lineages from {len( accepted )}" )
    else:
        last_seqs["collapsed_linege"] = last_seqs[previous_round]
        last_seqs = last_seqs.drop( columns=[i for i in last_seqs.columns if i.startswith( "round" )] )
        accepted = set( list( counts.loc[counts > min_sequences].index ) + forced_lineages )
        last_seqs.loc[~last_seqs["collapsed_linege"].isin( accepted ), "collapsed_linege"] = "Other"

    last_seqs["epiweek"] = mdates.date2num( last_seqs["epiweek"] )

    last_weeks = list( last_seqs["epiweek"].sort_values().unique() )
    prediction_weeks = [max( last_weeks )+7*i for i in range(1,4)]
    last_week_prediction = last_weeks + prediction_weeks

    collapsed_names = last_seqs.groupby( "lineage" ).first()["collapsed_linege"].to_dict()
    cat = last_seqs["collapsed_linege"].unique()
    cat = np.append( ["Other"], cat[cat != "Other"] )
    last_seqs["collapsed_linege"] = last_seqs["collapsed_linege"].astype( 'category' ).cat.set_categories( new_categories=cat )

    smoothed, model = model_sequence_counts( last_seqs, last_week_prediction )

    dump_model_names( model, collapsed_names )

    smoothed.index = mdates.num2date( smoothed.index )
    smoothed.index = smoothed.index.tz_localize(None)
    growth_rates = calculate_growth_rate( model )

    return smoothed, growth_rates, collapsed_names


def calculate_last_weeks( df : pd.DataFrame ):
    last_weeks = df["epiweek"].value_counts().sort_index()
    last_weeks = last_weeks[last_weeks > 100]
    last_weeks = last_weeks[-8:].index
    return last_weeks


def load_vocs():
    with open( VOC_LOCATION, "r" ) as i:
        vocs = { k: v for k, v in map( lambda x: x.strip().split( ",", 1 ), i ) }
    return vocs


def generate_table(
        rates_df : pd.DataFrame,
        seqs_df : pd.DataFrame,
        prevalence_df : pd.DataFrame,
        weeks, vocs: dict[str],
        forced_lineages : list[str]
):
    table = rates_df.reset_index()
    table["growth_rate_str"] = table.apply( lambda x: f"{x['lower']:.1%} to {x['upper']:.1%}", axis=1 )
    table = table.drop( columns=["upper", "lower"] )
    table.columns = ["lineage", "growth_rate", "growth_rate_str"]

    table["variant"] = table["lineage"].map( vocs )

    total_counts = seqs_df["collapsed_lineage"].value_counts()
    total_counts.name = "total_count"
    table = table.merge( total_counts, left_on="lineage", right_index=True, how="left" )

    recent_counts = seqs_df.loc[seqs_df["epiweek"].isin( weeks ), "collapsed_lineage"].value_counts()
    recent_counts.name = "recent_counts"
    table = table.merge( recent_counts, left_on="lineage", right_index=True, how="left" )
    table = table.dropna( subset=["recent_counts"] )

    last_prop = prevalence_df.loc[prevalence_df.index.isin( weeks )].groupby( "variant" ).last()

    table = table.merge( last_prop["prevalence"], left_on="lineage", right_index=True, how="left" )
    table = table.rename( columns={"prevalence" : "est_proportion"} )
    table["first_date"] = min( weeks ).strftime( "%Y-%m-%d" )
    table["last_date"] = max( weeks ).strftime( "%Y-%m-%d" )


    today = prevalence_df.index.max().strftime( "%Y-%m-%d" )
    nowcast = prevalence_df.groupby( "variant" ).last()
    nowcast["prevalence_str"] = nowcast.apply( lambda x: f"{x['lower']:.1%} to {x['upper']:.1%}", axis=1 )
    nowcast = nowcast[["prevalence", "prevalence_str"]]
    nowcast.columns = ["now_proportion", "now_proportion_str"]
    table = table.merge( nowcast, left_on="lineage", right_index=True, how="left" )

    table["today"] = today

    table = table.reindex(
        columns=["lineage", "variant", "total_count", "recent_counts", "est_proportion", "now_proportion", "now_proportion_str", "growth_rate", "growth_rate_str", "first_date",
                 "last_date", "today"] )
    #table_filtered = table.loc[table["recent_counts"] > 5]
    table_filtered = table.copy()

    fastest_growers = table_filtered.sort_values( "growth_rate", ascending=False ).head( 5 )["lineage"].to_list()
    fastest_growers.extend( forced_lineages )
    table_filtered = table_filtered.loc[table_filtered["lineage"].isin( fastest_growers )]
    return table_filtered, table


def add_collapsed_lineages( seqs: pd.DataFrame, names: dict[str] ):
    seqs["collapsed_lineage"] = seqs["lineage"].replace( names )
    return seqs

def calculate_growth_rates():
    cdc_lineages = load_cdc_variants()
    seqs = load_sequences()
    last_weeks = calculate_last_weeks( seqs )
    smooth_seqs, rates, names = smooth_sequence_counts( seqs, last_weeks, forced_lineages=cdc_lineages )
    rates = rates.sort_values( "growth_rate", ascending=False )

    seqs = add_collapsed_lineages( seqs, names )

    voc_names = load_vocs()
    return generate_table( rates_df=rates, seqs_df=seqs, prevalence_df=smooth_seqs, weeks=last_weeks, vocs=voc_names, forced_lineages=cdc_lineages )


if __name__ == "__main__":
    growth_rates_filtered, all = calculate_growth_rates()
    growth_rates_filtered.to_csv( os.path.abspath("../../resources/growth_rates.csv") , index=False )
    all.to_csv( os.path.abspath("../../resources/growth_rates_all.csv"), index=False )
