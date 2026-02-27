from dash import html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dash_table.Format import Format, Scheme

def get_table( growth_rates ):
    growth_rates['Lineage'] = [dfl if dfl!='Recombinants' else 'Other recombinants' for dfl in growth_rates['Lineage']]
    columns = [
        {'id': "Lineage", 'name': "Lineage"},
        {"id": "Estimated Advantage", 'name': 'Growth Advantage'},
        {'id': "Bootstrap 95% interval", 'name': "Bootstrap 95% CI"}
    ]
    

    table = html.Div( [
        dash_table.DataTable(
            data=growth_rates.to_dict('records'),
            columns=columns,
            tooltip_header={
                "Estimated Advantage" : "Estimated growth advantage of a particular lineage relative to circulating lineages, with serial interval of 3.1 days"
            },
            tooltip_delay=0,
            tooltip_duration=None,
            css=[
                { 'selector': '.dash-table-tooltip',
                  'rule': 'font-family: sans-serif; text-align: center; font-size: 12px' },
                { 'selector': '.dash-tooltip',
                  'rule': 'border: 0' },

            ],
            style_as_list_view=True,
            style_header={
                'backgroundColor': '#3C5C94',
                'color': '#F8F9FA',
                'fontWeight': 'bold',
                'fontFamily': 'sans-serif',
            },
            style_cell = {
                'fontFamily': 'sans-serif',
                'border': '0',
                'padding-right': '10px',
                'padding-left': '10px'
            },
            style_table={
                'borderRadius': '5px',
                "overflow" : "hidden",
                'fontSize': "11px",
            },
            style_header_conditional=[
                {
                    'if': { 'column_id': 'Estimated Advantage' },
                    'textAlign': 'center'
                },
                {
                    'if': { 'column_id': 'Lineage' },
                    'textAlign': 'left'
                }
            ],
            style_data_conditional=[
                # {
                #     'if': { 'filter_query': '{growth_rate} > 10.', 'column_id': 'Estimated Advantage' },
                #     'color': 'rgb(200, 0, 0)',
                #     'fontWeight': 'bold'
                # },
                # {
                #     'if': { 'filter_query': '{growth_rate} < -10.', 'column_id': 'Estimated Advantage'},
                #     'color': 'rgb(0, 0, 200)',
                #     'fontWeight': 'bold'
                # },
                {
                    'if': {'row_index': 'odd' },
                    'backgroundColor': '#e9eef6', # was #f0f0f0
                },
                {
                    'if': {'column_id': 'Estimated Advantage'},
                    'textAlign': 'center'
                },
                {
                    'if': { 'column_id': 'Lineage' },
                    'textAlign': 'left',
                    'fontStyle': 'italic'
                }
            ]
        ) ]
    )

    return table