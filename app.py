import dash
import dash_bootstrap_components as dbc
import gdown
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, State
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

# https://docs.google.com/spreadsheets/d/1aosvnSmsJQOGKC1ovB38PTfes1ZzHu73/edit?usp=sharing&ouid=111732102481483761509&rtpof=true&sd=true

# todo:
#   https://render.com/pricing
#   https://github.com/thusharabandara/dash-app-render-deployment
#   https://www.pythonanywhere.com/pricing/


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def download_excel_from_gdrive(gdrive_url):
    file_id = gdrive_url.split('/d/')[1].split('/')[0]
    download_url = f'https://drive.google.com/uc?id={file_id}&export=download'

    output_file = 'data_from_gdrive.xlsx'
    gdown.download(download_url, output_file, quiet=False)

    df = pd.read_excel(output_file)
    df['Datetime'] = pd.to_datetime(df['Datetime'], format='%d/%m/%Y %H:%M')
    df['Date'] = df['Datetime'].dt.date
    return df

default_gdrive_url = 'https://docs.google.com/spreadsheets/d/1bUDv4iCsTPddnd0yYFgj6xg_mzgpvdta/edit?usp=sharing&ouid=111732102481483761509&rtpof=true&sd=true'
data = download_excel_from_gdrive(default_gdrive_url)  # todo: remove code duplication
available_dates = data['Date'].unique()

# App layout
app.layout = dbc.Container(
    [
        dcc.Store(id='store-date', data=len(available_dates) - 1),  # This store will keep track of the current date index
        dcc.Store(id='store-dates', data=available_dates),  # This store will keep track of the unique dates
        dcc.Store(id='store-data', data=data.to_dict()),  # Store the entire dataset in memory

        html.Div(
            html.P([
                "Data comes from " ,
                html.A("this Google doc", href=default_gdrive_url, target="_blank"),
                ". To use this tool yourself, make your own Google Sheet using the same format. "
                "Upload your file on the right."
            ]),
            style={'position': 'absolute', 'top': '0px', 'left': '15px', 'width': '35%'},
        ),

        html.Div(
            dbc.InputGroup(
                [
                    dbc.Input(id="google-sheet-url", placeholder="Enter Google Sheet URL (allow view access)"),
                    dbc.Button("Upload data", id="upload-button", n_clicks=0),
                ]
            ), style={'position': 'absolute', 'top': '0px', 'right': '15px', 'width': '35%'},
        ),

        dbc.Row(
            [
                dbc.Col(dbc.Button('<', id='prev-day', color='primary', className='mr-2'), width='auto'),
                dbc.Col(html.H3(id='current-date', className='text-center'), width='auto'),
                dbc.Col(dbc.Button('>', id='next-day', color='primary', className='ml-2'), width='auto'),
            ],
            className='justify-content-center mb-4'
        ),
        dcc.Graph(id='daily-graph'),
        dcc.Graph(id='overall-graph'),
        html.Div(id='dummy', style={'display': 'none'})
    ],
    fluid=True,
)

@app.callback(
    [
        Output('store-data', 'data'),
        Output('store-dates', 'data')
    ],
    [
        # Input('dummy', 'children'),
        Input('upload-button', 'n_clicks')
    ],
    [
    State('google-sheet-url', 'value')
    ]
)
def load_data(n_clicks, user_provided_url):
    gdrive_url = 'https://docs.google.com/spreadsheets/d/1bUDv4iCsTPddnd0yYFgj6xg_mzgpvdta/edit?usp=sharing&ouid=111732102481483761509&rtpof=true&sd=true'
    default_gdrive_url = gdrive_url
    gdrive_url = user_provided_url if user_provided_url else default_gdrive_url

    data = download_excel_from_gdrive(gdrive_url)
    available_dates = data['Date'].unique()

    if data is not None:
        return data.to_dict(), available_dates

    return dash.no_update


# Callback to update the graph and current date
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
        Input('store-data', 'data')
    ],
    [
        State('store-date', 'data')
    ]
)
def update_graph(prev_clicks, next_clicks, stored_data, current_date_index):
    df = pd.DataFrame(stored_data)
    available_dates = df['Date'].unique()

    # Determine the direction of the change based on button clicks
    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'] == 'prev-day.n_clicks' and current_date_index > 0:
        current_date_index -= 1
    elif ctx.triggered[0]['prop_id'] == 'next-day.n_clicks' and current_date_index < len(available_dates) - 1:
        current_date_index += 1

    # Filter data for the current selected day
    current_date = available_dates[current_date_index]
    daily_data = df[df['Date'] == current_date]

    # Calculate the time range for the day (midnight to midnight)
    day_start = pd.to_datetime(current_date + ' 00:00:00')
    day_end = pd.to_datetime(current_date + ' 23:59:59')

    # Create a figure with three subplots, vertically stacked
    fig_daily = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,  # Adjust the space between plots
        subplot_titles=('Angle (degrees)', 'Swelling (dimensionless)')
    )

    fig_overall = make_subplots(
        rows=1, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.1,  # Adjust the space between plots
    )

    # Plot Angle data (top graph)
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Angle [deg]'],
        mode='markers',
        name='Angle (degrees)',
        marker=dict(
            symbol='circle',
            size=10,
            color='blue',
            line=dict(color='darkblue', width=2)
        )
    ), row=1, col=1)

    # Plot Circ low [cm] data
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ low [cm]'],
        mode='markers',
        name='Circ low [cm]',
        marker=dict(
            symbol='square',
            size=8,
            color='pink',
            # line=dict(color='darkblue', width=2)
        )
    ), row=2, col=1)

    # Plot Circ med [cm] data
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ med [cm]'],
        mode='markers',
        name='Circ med [cm]',
        marker=dict(
            symbol='diamond',
            size=8,
            color='red',
            # line=dict(color='darkgreen', width=2)
        )
    ), row=2, col=1)

    # Plot Circ high [cm] data
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Circ high [cm]'],
        mode='markers',
        name='Circ high [cm]',
        marker=dict(
            symbol='triangle-up',
            size=8,
            color='darkred',
            # line=dict(color='darkorange', width=2)
        )
    ), row=2, col=1)

    # Add vertical lines for events, and tooltips for event details
    for _, row in daily_data.iterrows():
        # Determine the color and line style based on the event type
        if row['Events'] == 'L':
            color = 'green'
            line_width = 1  # Green line with default width
            dash_style = None  # Green lines dashed
        elif row['Events'] == 'M':
            color = 'yellow'
            line_width = 1  # Yellow line thin
            dash_style = None  # Yellow line not dashed (solid)
        elif row['Events'] == 'H':
            color = 'red'
            line_width = 1  # Red line thicker
            dash_style = None  # Red lines dashed
        else:
            continue

        # Add vertical lines to both subplots
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

        # Add invisible scatter points for hover text (tooltips)
        fig_daily.add_trace(go.Scatter(
            x=[row['Datetime']],
            y=[1],  # Place the tooltip at the top of the graph
            mode='markers',
            marker=dict(size=1, color=color, opacity=0),  # Invisible marker
            hoverinfo='text',
            hovertext=row['Event details'],  # Tooltip text from the "Event details" column
            showlegend=False  # Hide from legend
        ), row=1, col=1)  # Tooltip added to the top graph

        fig_daily.add_trace(go.Scatter(
            x=[row['Datetime']],
            y=[1],  # Place the tooltip at the top of the bottom graph
            mode='markers',
            marker=dict(size=1, color=color, opacity=0),  # Invisible marker
            hoverinfo='text',
            hovertext=row['Event details'],  # Tooltip text from the "Event details" column
            showlegend=False  # Hide from legend
        ), row=2, col=1)  # Tooltip added to the bottom graph

        # Plot all Angle data on the third graph (constant, for all data points)
    fig_overall.add_trace(go.Scatter(
        x=df['Datetime'],
        y=df['Angle [deg]'],
        mode='markers',
        name='All Angle Data',
        line=dict(color='blue'),
        marker=dict(symbol='circle', size=6, color='blue', line=dict(color='darkblue', width=1))
    ), row=1, col=1)

    # Customize layout to include fixed axis ranges, no event lines on the third graph, and shared time range
    fig_daily.update_layout(
        title=f'Data for {current_date}',
        xaxis1=dict(
            range=[day_start, day_end],  # Set x-axis from midnight to midnight for top two plots
        ),
        xaxis2 = dict(
            range=[day_start, day_end],  # Set x-axis from midnight to midnight for top two plots
        ),
        yaxis=dict(
            title='Angle (degrees)',
            range=[10, 90],  # Fixed range for Angle axis (top graph)
            nticks = 9
    ),
        yaxis2=dict(
            title='Swelling (dimensionless)',
            range=[35, 45],  # Fixed range for Swelling axis (middle graph)
        ),
        height=400,  # Adjust height for three plots
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20)
    )

    fig_overall.update_layout(
        title=f'Overall',
        yaxis=dict(  # Third graph's y-axis range for all angle data
            title='Angle (degrees)',
            range=[10, 90],
            nticks=9
        ),
        height=230,  # Adjust height for three plots
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20)
    )

    # Update the current date displayed in the header
    return current_date_index, str(current_date), fig_daily, fig_overall

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)