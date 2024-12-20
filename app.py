import dash
import dash_bootstrap_components as dbc
import gdown
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, State
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

# https://mpfl-tto-surgery-rehab.onrender.com/

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

def download_excel_from_gdrive(gdrive_url):
    file_id = gdrive_url.split('/d/')[1].split('/')[0]
    download_url = f'https://drive.google.com/uc?id={file_id}&export=download'

    output_file = 'data_from_gdrive.xlsx'
    gdown.download(download_url, output_file, quiet=False)

    excel_data = pd.ExcelFile(output_file)
    df = pd.concat([excel_data.parse(sheet_name) for sheet_name in excel_data.sheet_names], ignore_index=True)
    df['Datetime'] = pd.to_datetime(df['Datetime'], format='%d/%m/%Y %H:%M', errors='coerce')

    has_invalid_entries = df['Datetime'].isna().any()
    if has_invalid_entries:
        df = df.dropna(subset=['Datetime'])

    df['Date'] = df['Datetime'].dt.date
    return df, has_invalid_entries

default_gdrive_url = 'https://docs.google.com/spreadsheets/d/1bUDv4iCsTPddnd0yYFgj6xg_mzgpvdta/edit?usp=sharing&ouid=111732102481483761509&rtpof=true&sd=true'
data, has_invalid_entries = download_excel_from_gdrive(default_gdrive_url)
available_dates = data['Date'].unique()

app.layout = dbc.Container(
    [
        dcc.Store(id='store-date', data=len(available_dates) - 1),
        dcc.Store(id='store-dates', data=available_dates),
        dcc.Store(id='store-data', data=data.to_dict()),
        dcc.Store(id='default-url', data=default_gdrive_url),
        dcc.Store(id='invalid_data_entries'),

        dbc.Row(
            [
                dbc.Col(dbc.Button('<<', id='first-day', color='primary', className='mr-2'), width='auto'),
                dbc.Col(dbc.Button('<', id='prev-day', color='primary', className='mr-2'), width='auto'),
                dbc.Col(html.H3(id='current-date', className='text-center'), width='auto'),
                dbc.Col(dbc.Button('>', id='next-day', color='primary', className='ml-2'), width='auto'),
                dbc.Col(dbc.Button('>>', id='last-day', color='primary', className='ml-2'), width='auto'),
            ],
            className='justify-content-center mb-3'
        ),

        html.Div(
            [
                dbc.InputGroup(
                [
                    dbc.Input(id="google-sheet-url", placeholder="Enter Google Sheet URL (allow view access)", value=default_gdrive_url),
                    dbc.Button("Graph data", id="upload-button", n_clicks=0),
                    dbc.Button("?", id="upload-help-button", n_clicks=0),
                ]
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Upload help")),
                    dbc.ModalBody([
                        html.Div("Data comes from the Google Sheet at the default populated URL."),
                        html.Br(),
                        html.Div("To use this tool yourself, make your own copy of the default Google Sheet (must be .xlsx) and fill in your own data."),
                        html.Br(),
                        html.Div("Make your file viewable for anyone with the link, and replace the default link with your own link."),
                    ]),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Close", id="upload-help-close", className="ms-auto", n_clicks=0
                        )
                    ),
                ],
                id="upload-help-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Warning: wrong formatting in Excel")),
                    dbc.ModalBody(html.Div(id="wrong-input-format-content")),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Close", id="wrong-input-format-close", className="ms-auto", n_clicks=0
                        )
                    ),
                ],
                id="wrong-input-format-modal",
                is_open=False,
            ),
            ], style={'position': 'absolute', 'top': '0px', 'right': '15px', 'width': '25%'},
        ),

        dcc.Graph(id='daily-graph'),
        dcc.Graph(id='overall-graph'),
    ],
    fluid=True,
)

@app.callback(
[
    Output('wrong-input-format-modal', 'is_open'),
    Output('wrong-input-format-content', 'children'),
],
[
    Input('invalid_data_entries', 'data'),
    Input('wrong-input-format-close', 'n_clicks'),
],
[
    State('wrong-input-format-modal', 'is_open'),
])
def toggle_wrong_input_warning(has_invalid_entries, n_clicks, is_open):
    content = html.Div([html.P("Warning: Some entries have an invalid date-time format. Expected '%d/%m/%Y %H:%M', but received something different."),
                        html.Br(),
                        html.P("All invalid data points have been left out of the graphs shown.")])
    if has_invalid_entries or n_clicks:
        return not is_open, content
    return dash.no_update


@app.callback(
    [
        Output('store-data', 'data'),
        Output('store-dates', 'data'),
        Output('invalid_data_entries', 'data'),
    ],
    [
        Input('upload-button', 'n_clicks')
    ],
    [
        State('default-url', 'data'),
        State('google-sheet-url', 'value')
    ]
)
def load_data(n_clicks, default_gdrive_url, user_provided_url):
    gdrive_url = user_provided_url if user_provided_url else default_gdrive_url

    data, invalid_entries = download_excel_from_gdrive(gdrive_url)
    available_dates = data['Date'].unique()

    if data is not None:
        return data.to_dict(), available_dates, invalid_entries

    return dash.no_update


@app.callback(
    [
        Output('store-date', 'data'),
        Output('current-date', 'children'),
        Output('daily-graph', 'figure'),
        Output('overall-graph', 'figure'),
    ],
    [
        Input('prev-day', 'n_clicks'),
        Input('next-day', 'n_clicks'),
        Input('first-day', 'n_clicks'),
        Input('last-day', 'n_clicks'),
        Input('store-data', 'data')
    ],
    [
        State('store-date', 'data')
    ]
)
def update_graph(prev_clicks, next_clicks, first_clicks, last_clicks, stored_data, current_date_index):
    df = pd.DataFrame(stored_data)
    available_dates = df['Date'].unique()

    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'] == 'prev-day.n_clicks' and current_date_index > 0:
        current_date_index -= 1
    elif ctx.triggered[0]['prop_id'] == 'next-day.n_clicks' and current_date_index < len(available_dates) - 1:
        current_date_index += 1
    elif ctx.triggered[0]['prop_id'] == 'first-day.n_clicks' and current_date_index > 0:
        current_date_index = 0
    elif ctx.triggered[0]['prop_id'] == 'last-day.n_clicks' and current_date_index < len(available_dates) - 1:
        current_date_index = len(available_dates)-1

    current_date = available_dates[current_date_index]
    daily_data = df[df['Date'] == current_date]

    day_start = pd.to_datetime(current_date + ' 00:00:00')
    day_end = pd.to_datetime(current_date + ' 23:59:59')

    fig_daily = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('Angle', 'Swelling (circumference of knee, measured at three locations)')
    )

    fig_overall = make_subplots(
        rows=1, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.1,
    )

    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Angle [deg]'],
        mode='markers',
        name='Angle',
        marker=dict(
            symbol='circle',
            size=10,
            color='blue',
            line=dict(color='darkblue', width=2)
        )
    ), row=1, col=1)

    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ low [cm]'],
        mode='markers',
        name='Circ low',
        marker=dict(
            symbol='square',
            size=8,
            color='pink',
        )
    ), row=2, col=1)

    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ med [cm]'],
        mode='markers',
        name='Circ med',
        marker=dict(
            symbol='diamond',
            size=8,
            color='red',
        )
    ), row=2, col=1)

    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ high [cm]'],
        mode='markers',
        name='Circ high',
        marker=dict(
            symbol='triangle-up',
            size=8,
            color='darkred',
        )
    ), row=2, col=1)

    for _, row in daily_data.iterrows():
        if row['Events'] == 'L':
            color = 'green'
            line_width = 1
            dash_style = None
        elif row['Events'] == 'M':
            color = 'yellow'
            line_width = 1
            dash_style = None
        elif row['Events'] == 'H':
            color = 'red'
            line_width = 1
            dash_style = None
        else:
            continue

        fig_daily.add_shape(
            type='line',
            x0=row['Datetime'],
            x1=row['Datetime'],
            y0=0,
            y1=1,
            xref='x',
            yref='paper',
            line=dict(
                color=color,
                width=line_width,
                dash=dash_style)
        )

        fig_daily.add_trace(go.Scatter(
            x=[row['Datetime']],
            y=[1],
            mode='markers',
            marker=dict(size=1, color=color, opacity=0),
            hoverinfo='text',
            hovertext=row['Event details'],
            showlegend=False
        ), row=1, col=1)

        fig_daily.add_trace(go.Scatter(
            x=[row['Datetime']],
            y=[1],
            mode='markers',
            marker=dict(size=1, color=color, opacity=0),
            hoverinfo='text',
            hovertext=row['Event details'],
            showlegend=False
        ), row=2, col=1)

    fig_overall.add_trace(go.Scatter(
        x=df['Datetime'],
        y=df['Angle [deg]'],
        mode='markers',
        name='All Angle Data',
        marker=dict(symbol='circle', size=6, color='skyblue', line=dict(color='#0d6efd', width=1))
    ), row=1, col=1)

    fig_overall.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Angle [deg]'],
        mode='markers',
        name='Today\'s Angle Data',
        marker=dict(symbol='circle', size=6, color='blue', line=dict(color='darkblue', width=1))
    ), row=1, col=1)

    fig_daily.update_layout(
        title=f'Data for {current_date}',
        xaxis1=dict(
            range=[day_start, day_end],
            nticks=24,
        ),
        xaxis2 = dict(
            title='Time of day',
            range=[day_start, day_end],
            nticks=24,
            tickformat='%H'
        ),
        yaxis=dict(
            title='Angle [deg]',
            range=[0, 150],
            nticks = 8
    ),
        yaxis2=dict(
            title='Swelling [cm]',
            range=[35, 45],
        ),
        height=400,
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20)
    )

    fig_overall.update_layout(
        title=f'Overall',
        yaxis=dict(
            title='Angle [deg]',
            range=[0, 150],
            nticks=8
        ),
        height=250,
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20),
        showlegend=False
    )

    fig_overall.add_hline(y=90, line_width=1, line_color="grey")

    return current_date_index, str(current_date), fig_daily, fig_overall

@app.callback(
    Output("upload-help-modal", "is_open"),
    [
        Input("upload-help-button", "n_clicks"),
        Input("upload-help-close", "n_clicks")
    ],
    State("upload-help-modal", "is_open"),
)
def toggle_upload_help_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

if __name__ == '__main__':
    app.run_server(debug=True)
