import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import openpyxl

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Function to load and process the Excel data
def load_data(file_path):
    df = pd.read_excel(file_path, engine='openpyxl', sheet_name='python')
    df['Datetime'] = pd.to_datetime(df['Datetime'], format='%d/%m/%Y %H:%M')
    df['Date'] = df['Datetime'].dt.date
    return df

# Sample data loading
# Replace 'data.xlsx' with your actual Excel file path or use an upload component
data = load_data('20240924 Physio log.xlsx')
available_dates = data['Date'].unique()

# App layout
app.layout = dbc.Container(
    [
        dcc.Store(id='store-date', data=0),  # This store will keep track of the current date index
        dcc.Store(id='store-data', data=data.to_dict()),  # Store the entire dataset in memory
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
    ],
    fluid=True,
)

# Callback to update the graph and current date
@app.callback(
    [
        Output('current-date', 'children'),
        Output('daily-graph', 'figure'),
        Output('overall-graph', 'figure'),
    ],
    [
        Input('prev-day', 'n_clicks'),
        Input('next-day', 'n_clicks')
    ],
    [
        State('store-date', 'data'),
        State('store-data', 'data')
    ]
)
def update_graph(prev_clicks, next_clicks, current_date_index, stored_data):
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

    # Plot Swelling data (bottom graph)
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Datetime'],
        y=daily_data['Swelling'],
        mode='markers',
        name='Swelling (dimensionless)',
        marker=dict(
            symbol='diamond',
            size=10,
            color='red',
            line=dict(color='black', width=2)
        )
    ), row=2, col=1)

    # Add vertical lines for events, and tooltips for event details
    for _, row in daily_data.iterrows():
        if row['Events'] == 'Rest':
            color = 'green'
        elif row['Events'] == 'Move':
            color = 'orange'
        elif row['Events'] == 'Exercise':
            color = 'red'
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
            line=dict(color=color, width=2, dash='dash')
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
            title='Time'
        ),
        xaxis2 = dict(
            range=[day_start, day_end],  # Set x-axis from midnight to midnight for top two plots
            title='Time'
        ),
        yaxis=dict(
            title='Angle (degrees)',
            range=[0, 100]  # Fixed range for Angle axis (top graph)
        ),
        yaxis2=dict(
            title='Swelling (dimensionless)',
            range=[0, 20],  # Fixed range for Swelling axis (middle graph)
        ),
        height=800,  # Adjust height for three plots
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20)
    )

    fig_daily.update_layout(
        title=f'Data for {current_date}',
        xaxis=dict(  # Show the full range of time
            title='Time',
        ),
        yaxis=dict(  # Third graph's y-axis range for all angle data
            title='All Angle Data',
            range=[0, 100]
        ),
        height=800,  # Adjust height for three plots
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=20)
    )

    # Update the current date displayed in the header
    return str(current_date), fig_daily, fig_overall

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)