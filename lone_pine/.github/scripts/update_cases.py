import os
from urllib.error import HTTPError
import pandas as pd
import datetime
from tableauscraper import TableauScraper as TS

def append_wastewater( sd ):
    zip_loc = "https://raw.githubusercontent.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego/master/Zipcodes.csv"
    zips = pd.read_csv( zip_loc, usecols=["Zip_code", "Wastewater_treatment_plant"], dtype={"Zip_code" : str, "Wastewater_treatment_plant" : str } )
    zips.columns = ["ziptext", "catchment_new"]
    zips["catchment_new"] = zips["catchment_new"].str.replace( " " , "" )
    zips = zips.set_index( "ziptext" )
    return_df = sd.merge( zips, left_on="ziptext", right_index=True, how="left" )
    return_df.loc[return_df["catchment"].isna(),"catchment"] = return_df.loc[return_df["catchment"].isna(),"catchment_new"]
    return_df = return_df.drop( columns=["catchment_new"] )
    return_df["catchment"] = return_df["catchment"].fillna( "Other" )

    assert return_df.shape[0] == sd.shape[0], f"Merge was unsuccessful. {sd.shape[0]} rows in original vs. {return_df.shape[0]} rows in merge output."
    return return_df

def download_sd_cases():
    """
    Returns
    -------
    pandas.DataFrame
        DataFrame detailing the daily number of cases in San Diego.
    """
    def _append_population( dataframe ):
        pop_loc = os.path.abspath("../../resources/zip_pop.csv")
        pop = pd.read_csv( pop_loc, usecols=["Zip", "Total Population"], thousands=",", dtype={"Zip" : str, "Total Population" : int } )
        dataframe = dataframe.merge( pop, left_on="ziptext", right_on="Zip", how="left" )
        dataframe = dataframe.drop( columns=["Zip"] )
        dataframe["population"] = dataframe["Total Population"]
        dataframe = dataframe.drop( columns=["Total Population"] )

        return dataframe

    def _add_missing_cases( entry, start ):
        entry = entry.set_index( "updatedate" ).reindex( pd.date_range( start, entry["updatedate"].max() ) ).rename_axis( "updatedate" ).reset_index()
        indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=7)
        entry["new_cases"] = entry.rolling( window=indexer, min_periods=1 )["new_cases"].apply( lambda x: x.max() / 7 )
        entry["new_cases"] = entry["new_cases"].fillna(0)
        return entry

    # First, we load current dataset of cases
    sd = pd.read_csv(os.path.abspath("../../resources/cases.csv"), parse_dates=["updatedate"] )
    sd = sd.loc[~sd["ziptext"].isna()]
    sd = sd.loc[sd["ziptext"]!="None"]
    sd["ziptext"] = sd["ziptext"].astype(int).astype(str)

    # Next we load the diff, which is an offset which helps reconcile differences between dataset. Not perfect and we
    # still see a big leap when we switched.
    diff = pd.read_csv(os.path.abspath("../../resources/cases-zip-diff.csv"), index_col="zipcode", dtype={"zipcode" : str, "diff" : float})
    diff = diff["diff"]

    # We load the latest cummulative cases from the Tableau dashbaord
    url = "https://public.tableau.com/views/COVID-19Geography/GeoZip"
    ts = TS()
    ts.loads( url )
    workbook = ts.getWorkbook()
    updatedate = pd.to_datetime( workbook.worksheets[0].data["DAY(End Date)-alias"] ).values[0]
    if updatedate <= sd["updatedate"].max():
        print( "No update to San Diego's cases." )
        return sd

    temp = workbook.worksheets[1].data
    temp = temp[["ZIP-value", "SUM(population (Zip))-alias", "SUM(zipcount (Zip))-alias", "DAY(End Date)-value"]].copy()
    temp.columns = ["ziptext", "population", "case_count", "updatedate"]
    temp["ziptext"] = temp["ziptext"].astype(int).astype(str)
    temp["case_count"] = temp["case_count"].replace({"%null%": 0})
    temp["updatedate"] = pd.to_datetime(temp["updatedate"])
    temp["diff"] = temp["ziptext"].map(diff)
    temp["case_count"] += temp["diff"]
    temp = temp.drop(columns=["diff"])
    temp.to_csv( "new_cases.csv" )

    # Combine lastest commulative cases and prior SD cases
    sd = pd.concat([sd, temp], ignore_index=True)
    sd["new_cases"] = sd.groupby("ziptext")["case_count"].diff()
    sd["new_cases"] = sd["new_cases"].fillna(0)
    sd.loc[sd["new_cases"] < 0, "new_cases"] = 0

    # Fill in new_cases by interpolating difference in cummulative cases.
    date = sd["updatedate"].unique()[-2]

    sdprob = sd.loc[sd["updatedate"]>date]
    sdprob = sdprob.groupby( "ziptext" ).apply( _add_missing_cases, start=date + pd.Timedelta( days=1 ) )
    sdprob = sdprob.drop( columns="ziptext" ).reset_index()
    sdprob = sdprob.drop( columns="level_1" )

    sd = sd.loc[sd["updatedate"]<=date]
    sd = pd.concat( [sd,sdprob] )
    sd["case_count"] = sd.groupby("ziptext")["new_cases"].cumsum()

    sd = _append_population( sd )

    sd["days_past"] = ( datetime.datetime.today() - sd["updatedate"] ).dt.days

    sd["case_count"] = sd.groupby( "ziptext" )["new_cases"].cumsum()

    # Add the catchment area
    sd = append_wastewater( sd )
    return sd

def download_bc_cases():
    """
    Returns
    -------
    pandas.DataFrame
        DateFrame detailing the daily number of cases in Baja California, Mexico
    """
    today = datetime.datetime.today()
    date_range = 10
    attempts = 0
    while attempts < date_range:
        print( f"Attemping to load BC data from {today.strftime( '%Y-%m-%d')}" )
        date_url = int( today.strftime( "%Y%m%d" ) )
        bc_url = f"https://datos.covid-19.conacyt.mx/Downloads/Files/Casos_Diarios_Estado_Nacional_Confirmados_{date_url}.csv"

        try:
            bc = pd.read_csv( bc_url, index_col="nombre" )
            break
        except HTTPError:
            today = today - datetime.timedelta( days=1 )
    else:
        raise RuntimeError( f"Unable to find a valid download link. Last url tried was {bc_url}" )

    bc = bc.drop( columns=["cve_ent", "poblacion"] )
    bc = bc.T
    bc = bc["BAJA CALIFORNIA"].reset_index()
    bc["index"] = pd.to_datetime( bc["index"], format="%d-%m-%Y" ).dt.tz_localize( None )
    bc["index"] = bc["index"].dt.normalize()
    bc.columns = ["updatedate", "new_cases"]
    bc = bc.sort_values( "updatedate" )

    # Generate the additional columns
    bc["case_count"] = bc["new_cases"].cumsum()
    bc["ziptext"] = "None"
    bc["population"] = 3648100
    bc["days_past"] = ( today - bc["updatedate"] ).dt.days

    bc = bc.loc[bc["case_count"] > 0]

    return bc

def download_cases():
    """ Downloads the cases per San Diego ZIP code. Appends population.
    Returns
    -------
    pandas.DataFrame
        DataFrame detailing the cummulative cases in each ZIP code.
    """
    sd = download_sd_cases()
    bc = download_bc_cases()
    c = pd.concat( [sd,bc] )

    return c

if __name__ == "__main__":
    cases = download_cases()
    cases.to_csv( os.path.abspath("../../resources/cases.csv"), index=False )
