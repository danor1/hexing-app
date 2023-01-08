import pandas as pd
import geopandas as gpd
import json
import plotly.express as px
import math
import dash
from dash import dcc, html, Input, Output, callback_context, dash_table
from .layout import html_layout


area_codes_df = pd.read_csv('./data/miscData/area_code_names.csv', index_col=0)
area_codes_dict = area_codes_df.set_index('area_code').to_dict()['area_name']
area_codes_inverted_dict = {v: k for k, v in area_codes_dict.items()}
area_codes = list(area_codes_dict.keys())
area_code_names = list(area_codes_dict.values())

all_hexes_df = gpd.read_file('./data/geoData/all_hexes.csv', GEOM_POSSIBLE_NAMES="geometry", KEEP_GEOM_COLUMNS="NO")
all_sites_df = gpd.read_file('./data/geoData/all_sites.csv', GEOM_POSSIBLE_NAMES="geometry", KEEP_GEOM_COLUMNS="NO")


def get_saved_hexing(postcode_initial):
    return all_hexes_df[all_hexes_df['hex_identifier'].str.contains(postcode_initial)]['geometry']


def get_this_postcode_sites(postcode_initial):
    site_data = all_sites_df[all_sites_df[f"hex_id_{postcode_initial.split('_')[1]}"].str.contains(postcode_initial)]

    site_data.crs = "EPSG:4326"

    # filter and add columns
    pts_geo_df = site_data.copy()
    pts_geo_df['name'] = site_data['name']
    pts_geo_df['chain'] = 'SMB'
    pts_geo_df['brand_stack'] = 'no stack'

    enterprise = pd.read_csv('./data/miscData/enterprise_detailed.csv', index_col=0)
    strategic = pd.read_csv('./data/miscData/strategic_detailed.csv', index_col=0)
    multisite = pd.read_csv('./data/miscData/multisite_detailed.csv')

    pts_geo_df.loc[pts_geo_df['name'].isin(multisite['Name']), 'chain'] = 'Multi-Site'

    for i, r in enterprise.iterrows():
        if isinstance(r.Exclude_entries, str):
            pts_geo_df.loc[(pts_geo_df['name'].str.lower().str.contains(r.Search_name, na=False, regex=False)) & (
                ~(pts_geo_df['name'].isin(r.Exclude_entries.split("' '")))), 'chain'] = 'Enterprise'
        else:
            pts_geo_df.loc[(pts_geo_df['name'].str.lower().str.contains(r.Search_name, na=False,
                                                                        regex=False)), 'chain'] = 'Enterprise'

    for i, r in strategic.iterrows():
        if isinstance(r.Exclude_entries, str):
            pts_geo_df.loc[(pts_geo_df['name'].str.lower().str.contains(r.Search_name, na=False, regex=False)) & (
                ~(pts_geo_df['name'].isin(r.Exclude_entries.split("' '")))), 'chain'] = 'Strategic'
        else:
            pts_geo_df.loc[(pts_geo_df['name'].str.lower().str.contains(r.Search_name, na=False,
                                                                        regex=False)), 'chain'] = 'Strategic'

    pts_geo_df.loc[pts_geo_df['social'] == 'peckwater', 'chain'] = 'Peckwater'

    pts_geo_df['brand_stack'] = pts_geo_df.apply(
        lambda r: r['foods'] if r['social'] == 'peckwater' else r['brand_stack'], axis=1)

    pts_geo_df['available_stacks_sort'] = pts_geo_df['available_stacks'].apply(lambda x: len(x.split(';')))
    chain_d = {'SMB': 0, 'Peckwater': 4, 'Multi-Site': 1, 'Enterprise': 2, 'Strategic': 3}
    pts_geo_df['chain_sort'] = pts_geo_df['chain'].apply(lambda x: chain_d[x])
    pts_geo_df.sort_values(inplace=True,
                           by=['available_stacks_sort', 'chain_sort', 'revenue_per_listing_prediction_site',
                               'hygiene_rating'], ascending=False)
    pts_geo_df.drop(['available_stacks_sort', 'chain_sort'], axis=1, inplace=True)

    return pts_geo_df


def build_selected(psc, screen_size):
    # read in saved hex dataframe
    hex_df = get_saved_hexing(psc)

    # read in this postcode's sites
    points_geo_df = get_this_postcode_sites(psc)

    # create circles
    points_geo_crs_change_df = points_geo_df.to_crs(4326)

    try:
        first_pw_lat = \
            points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].geometry.values[
                0].coords.xy[1][0]
    except:
        first_pw_lat = 0

    points_geo_crs_change_df = points_geo_df.to_crs(3857)
    p = math.pi / 180
    scale_factor = 1 / math.cos(p * first_pw_lat)
    buffer_radius_meters = 1.5 * 1000 * 1.60934 * scale_factor
    circles = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters)  # fairly certain this is 2414m
    circles1 = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters - 200)
    circles2 = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters - 100)
    circles3 = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters)
    circles4 = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters + 100)
    circles5 = points_geo_crs_change_df.loc[points_geo_crs_change_df['brand_stack'] != 'no stack'].buffer(
        buffer_radius_meters + 200)
    circles1 = circles1.to_crs("EPSG:4326")
    circles2 = circles2.to_crs("EPSG:4326")
    circles3 = circles3.to_crs("EPSG:4326")
    circles4 = circles4.to_crs("EPSG:4326")
    circles5 = circles5.to_crs("EPSG:4326")

    points_geo_df['size'] = points_geo_df['chain'].apply(lambda x: 6 if x == 'Peckwater' else 1)

    # set parameters for screen resizing
    w = -1
    h = -1
    if screen_size == 'laptop':
        w = 800
        h = 500
    elif screen_size == 'monitor':
        w = 1400
        h = 900

    # begin plotting
    fig = px.scatter_mapbox(points_geo_df,
                            lat=points_geo_df.geometry.y,
                            lon=points_geo_df.geometry.x,
                            hover_name=points_geo_df['name'],
                            color='chain',
                            category_orders={'chain': ['SMB', 'Multi-Site', 'Enterprise', 'Strategic', 'Peckwater']},
                            color_discrete_sequence=['blue', 'red', 'yellow', 'green', 'orange'],
                            hover_data=['hygiene_rating', 'foods', 'brand_stack', 'available_stacks',
                                        'revenue_per_listing_prediction_site'],
                            custom_data=['name', 'address', 'postcode', 'city', 'phone', 'social', 'foods',
                                         'overall_rating', 'overall_rating_count',
                                         'revenue_per_listing_prediction_site', 'hygiene_rating', 'link_DE',
                                         'rating_DE', 'rating_count_DE', 'link_UE', 'rating_UE', 'rating_count_UE',
                                         'link_JE', 'rating_JE', 'rating_count_JE', 'link_GP', 'rating_GP',
                                         'rating_count_GP', 'postcode_DE_market_share', 'postcode_UE_market_share',
                                         'postcode_JE_market_share', 'chain', 'brand_stack', 'available_stacks',
                                         'hex_id_40', 'hex_id_30', 'hex_id_20', 'hex_id_10'],
                            zoom=9,
                            mapbox_style="carto-darkmatter",
                            width=w,
                            height=h
                            )

    fig.update_traces(
        marker_size=7,
    )

    fig.update_layout(
        mapbox={
            "layers": [
                {
                    "source": json.loads(hex_df.geometry.to_json()),
                    "below": "traces",
                    "type": "line",

                    "color": "purple",
                    "line": {"width": 1.5},
                },
                {
                    "source": json.loads(
                        circles1.loc[points_geo_df['brand_stack'].str.contains('Chicken 1;', na=False)].to_json()),
                    "below": "traces",
                    "type": "line",
                    "color": "red",
                    "line": {"width": 1.5},
                },
                {
                    "source": json.loads(
                        circles2.loc[points_geo_df['brand_stack'].str.contains('Mexican 1;', na=False)].to_json()),
                    "below": "traces",
                    "type": "line",
                    "color": "green",
                    "line": {"width": 1.5},
                },
                {
                    "source": json.loads(
                        circles3.loc[points_geo_df['brand_stack'].str.contains('Chicken 2;', na=False)].to_json()),
                    "below": "traces",
                    "type": "line",
                    "color": "yellow",
                    "line": {"width": 1.5},
                },
                {
                    "source": json.loads(
                        circles4.loc[points_geo_df['brand_stack'].str.contains('KTSU;', na=False)].to_json()),
                    "below": "traces",
                    "type": "line",
                    "color": "pink",
                    "line": {"width": 1.5},
                },
                {
                    "source": json.loads(
                        circles5.loc[points_geo_df['brand_stack'].str.contains('SAQ;', na=False)].to_json()),
                    "below": "traces",
                    "type": "line",
                    "color": "blue",
                    "line": {"width": 1.5},
                }
            ],
        },
        clickmode='event+select',
        margin=dict(t=0, b=0, l=0, r=0)
    )

    return fig


def init_dashboard(server):
    """ Create the Dash app instance """
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix="/dashapp/",
        external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'],
    )

    dash_app.layout = html.Div([
        html.Div([
            dcc.Dropdown(
                ['UK'],
                'UK',
                id='dropdown',
                style={'display': 'inline-block', 'width': '24vw', 'background-color': 'rgba(0, 255, 0, 0.5)'}
            ),
            dcc.Dropdown(
                area_code_names,
                'Manchester',
                id='dropdown1',
                style={'display': 'inline-block', 'width': '24vw', 'background-color': 'rgba(0, 255, 0, 0.5)'}
            ),
            dcc.Dropdown(
                ['10', '20', '30', '40'],
                '20',
                id='dropdown2',
                style={'display': 'inline-block', 'width': '24vw', 'background-color': 'rgba(0, 255, 0, 0.5)'}
            ),
            dcc.Dropdown(
                ['laptop', 'monitor'],
                'laptop',
                id='dropdown3',
                style={'display': 'inline-block', 'width': '24vw', 'background-color': 'rgba(0, 255, 0, 0.5)'}
            )
        ], style={'background-color': 'rgba(0, 255, 0, 0.5)'}),

        html.Div([
            html.Div([
                dcc.Graph(
                    id='map-datapoint'
                )
            ], style={'display': 'inline-block'}),

            html.Div([
                dcc.Markdown("""
                    **Select Data**

                    Select a data point
                    """),
                html.Pre(id='click-datapoint'),
                html.A([html.Span('Social')], id='url_id', href="click-url", target="_blank"),

            ], style={'display': 'inline-block', 'float': 'right', 'padding': '5px', 'border': '2px solid blue'}),
        ]),
        dash_table.DataTable(id='clicked_button', export_format='xlsx', sort_action="native",
                             style_cell={
                                 'textAlign': 'left', 'height': 40
                             },
                             style_header={
                                 'backgroundColor': 'rgb(30, 30, 30)',
                                 'color': 'white', 'fontWeight': 'bold',
                                 'font': 18
                             },
                             style_data={
                                 'backgroundColor': 'rgb(50, 50, 50)',
                                 'color': 'white',
                                 'font': 16
                             },
                             columns=[
                                 {'name': 'sellable_stacks', 'id': 'available_stacks'},
                                 {'name': 'chain', 'id': 'chain'},
                                 {'name': 'FSA', 'id': 'hygiene_rating'},
                                 {'name': 'overall_rating', 'id': 'overall_rating'},
                                 {'name': 'overall_rating_count', 'id': 'overall_rating_count'},
                                 {'name': 'revenue_per_listing_prediction_site',
                                  'id': 'revenue_per_listing_prediction_site'},
                                 {'name': 'name', 'id': 'name'},
                                 {'name': 'address', 'id': 'address'},
                                 {'name': 'postcode', 'id': 'postcode'},
                                 {'name': 'city', 'id': 'city'},
                                 {'name': 'phone', 'id': 'phone'},
                                 {'name': 'social', 'id': 'social'},
                                 {'name': 'foods', 'id': 'foods'},
                                 {'name': 'link_DE', 'id': 'link_DE'},
                                 {'name': 'rating_DE', 'id': 'rating_DE'},
                                 {'name': 'rating_count_DE', 'id': 'rating_count_DE'},
                                 {'name': 'link_UE', 'id': 'link_UE'},
                                 {'name': 'rating_UE', 'id': 'rating_UE'},
                                 {'name': 'rating_count_UE', 'id': 'rating_count_UE'},
                                 {'name': 'link_JE', 'id': 'link_JE'},
                                 {'name': 'rating_JE', 'id': 'rating_JE'},
                                 {'name': 'rating_count_JE', 'id': 'rating_count_JE'},
                                 {'name': 'link_GP', 'id': 'link_GP'},
                                 {'name': 'rating_GP', 'id': 'rating_GP'},
                                 {'name': 'rating_count_GP', 'id': 'rating_count_GP'},
                                 {'name': 'postcode_DE_market_share', 'id': 'postcode_DE_market_share'},
                                 {'name': 'postcode_UE_market_share', 'id': 'postcode_UE_market_share'},
                                 {'name': 'postcode_UE_market_share', 'id': 'postcode_UE_market_share'},
                                 {'name': 'brand_stack', 'id': 'brand_stack'}])

    ])

    # Initialize callbacks after our app is loaded. Pass dash_app as a parameter
    init_callbacks(dash_app)

    return dash_app.server


def init_callbacks(dash_app):
    @dash_app.callback(
        Output('clicked_button', 'data'),
        Input('map-datapoint', 'clickData'),
        Input('dropdown1', 'value'),
        Input('dropdown2', 'value'))
    def display_table(click_data, psc_value1, psc_value2):
        changed_id = [p['prop_id'] for p in callback_context.triggered][0]
        if 'map-datapoint' in changed_id:
            a = json.dumps(click_data, indent=2)
            if a != 'null':
                a1 = eval(a)['points'][0]['customdata']
                h_i = a1[-int(psc_value2[0])]
            p_g_df = get_this_postcode_sites(area_codes_inverted_dict[psc_value1] + '_' + psc_value2)
            default_table = p_g_df[p_g_df[f'hex_id_{psc_value2}'] == h_i]
            return default_table[['name', 'address', 'postcode', 'city', 'phone', 'social', 'foods', 'overall_rating',
                                  'overall_rating_count', 'revenue_per_listing_prediction_site', 'hygiene_rating',
                                  'link_DE', 'rating_DE', 'rating_count_DE', 'link_UE', 'rating_UE', 'rating_count_UE',
                                  'link_JE', 'rating_JE', 'rating_count_JE', 'link_GP', 'rating_GP', 'rating_count_GP',
                                  'postcode_DE_market_share', 'postcode_UE_market_share', 'postcode_JE_market_share',
                                  'chain', 'brand_stack', 'available_stacks']].to_dict('records')
        return get_this_postcode_sites(area_codes_inverted_dict[psc_value1] + '_' + psc_value2)

    @dash_app.callback(
        Output('map-datapoint', 'figure'),
        Input('dropdown1', 'value'),
        Input('dropdown2', 'value'),
        Input('dropdown3', 'value'))
    def choose_postcode(mrtk_place, area_code, screen_sizing):
        return build_selected(area_codes_inverted_dict[mrtk_place] + '_' + area_code, screen_sizing)

    @dash_app.callback(
        Output('click-datapoint', 'children'),
        Output('url_id', 'href'),
        Input('map-datapoint', 'clickData'))
    def display_click_data(click_data):
        a = json.dumps(click_data, indent=2)

        if a != 'null':
            
            a1 = eval(a)['points'][0]['customdata']
            a2 = 'Name:    ' + a1[0] + '\n\n'

            listing_count_factor = 9
            je_available_str = '(JE available)'
            if a1[17] == '':
                listing_count_factor = 6
                je_available_str = '(JE not available)'
            a2 = a2 + 'Weekly predicted revenue of site: £' + (str(round(float(a1[9]) * listing_count_factor, 2))) + je_available_str + '\n\n'

            a2 = a2 + 'Rating:  ' + a1[7] + '\n\n'

            foods_line = a1[6].split(',')
            a2 = a2 + 'Foods:   '
            for ind, line in enumerate(foods_line):
                if ind != 0:
                    a2 = a2 + '         '
                a2 = a2 + line + '\n'

            a2 = a2 + 'Stack:   ' + a1[-6] + '\n\n'
            a2 = a2 + 'Sellable Stacks:   ' + a1[-5] + '\n\n'

            address_line = a1[1].split(", ")
            a2 = a2 + 'Address: '
            for ind, line in enumerate(address_line):
                if ind != 0:
                    a2 = a2 + '         '
                a2 = a2 + line + '\n'

            a2 = a2 + 'Phone:   ' + a1[4] + '\n\n'

            social_line = a1[5].split(",")
            a2 = a2 + 'Social:  '
            for ind, line in enumerate(social_line):
                if ind != 0:
                    a2 = a2 + '         '
                a2 = a2 + line + '\n'

            if a[5] != '':
                return [a2, a1[5]]
            else:
                return [a2, "https://www.youtube.com/watch?v=iik25wqIuFo"]
        return [a, "https://www.youtube.com/watch?v=iik25wqIuFo"]
