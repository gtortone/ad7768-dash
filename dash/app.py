#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_daq as daq
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from celery import chord

from sched.tasks import *
from sched.tasks import queue
from time import sleep
from lib.ad7768 import DataFormat, Filter, DecRate, ClockDiv, ModDiv, ChannelGroup

def purgeAllTasks(queue):
    tid = []
    # cancel queued tasks
    queue.control.purge()
    # cancel running tasks
    active_tasks = queue.control.inspect().active()
    for worker in active_tasks.keys():
        for task in active_tasks[worker]:
            tid.append(task["id"])
    queue.control.revoke(tid, terminate=True)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

#
# globals
#

length = (128, 1024, 4096, 8192, 16384, 32768, 65536)
linestyle = dict(width = 1.2)

#
# layout
#

app.layout = html.Div( 
    [

        html.Div([

            dcc.Interval(id="page_scheduler", n_intervals=0, interval=5000),

            # banner - start

            html.Div([
                html.H3("AD7768-4 Dashboard"),
            ], style={'display': 'flex', 'justify-content': 'center'}),

            # banner - end

            html.Div([

                # left frame - start

                html.Div([

                    html.Div([

                        html.Label('channel'),
                        dcc.Dropdown(
                            id = "channel",
                            options = [{'label': i, 'value': i} for i in range(0,4)],
                            value = 0
                        ),
                    
                        html.Label('waveform length'),
                        dcc.Dropdown(
                            id = "waveform_length",
                            options = [{'label': i, 'value': i} for i in length],
                            value = length[0]
                        ),

                    ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '10px 10px', 'margin': "5px 5px 5px 5px", 'border': '1px solid #1C6EA4'}),

                    html.Div([

                        html.Label('filter'),
                        dcc.Dropdown(
                            id = "filter",
                            options = [
                                {'label': 'Wideband', 'value': Filter.WIDEBAND},
                                {'label': 'Sinc5', 'value': Filter.SINC5},
                            ],
                            value = Filter.WIDEBAND
                        ),

                        html.Label('decimation'),
                        dcc.Dropdown(
                            id = "decimation",
                            options = [
                                {'label': 'x32', 'value': DecRate.x32},
                                {'label': 'x64', 'value': DecRate.x64},
                                {'label': 'x128', 'value': DecRate.x128},
                                {'label': 'x256', 'value': DecRate.x256},
                                {'label': 'x512', 'value': DecRate.x512},
                                {'label': 'x1024', 'value': DecRate.x1024},
                            ],
                            value = DecRate.x32
                        ),
                    ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '10px 10px', 'margin': "5px 5px 5px 5px", 'border': '1px solid #1C6EA4'}),

                    html.Div([

                        html.Label('modulator freq.'),
                        dcc.Dropdown(
                            id = "adcclockdiv",
                            options = [
                                {'label': 'fMCLK/4', 'value': ClockDiv.div4},
                                {'label': 'fMCLK/8', 'value': ClockDiv.div8},
                                {'label': 'fMCLK/32', 'value': ClockDiv.div32},
                            ],
                            value = ClockDiv.div32
                        ),

                        html.Label('chopping freq.'),
                        dcc.Dropdown(
                            id = "fmoddiv",
                            options = [
                                {'label': 'fMOD/8', 'value': ModDiv.div8},
                                {'label': 'fMOD/32', 'value': ModDiv.div32},
                            ],
                            value = ModDiv.div32
                        ),

                    ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '10px 10px', 'margin': "5px 5px 5px 5px", 'border': '1px solid #1C6EA4'}),

                    html.Div([

                        html.Div([
                            html.Button(
                                "Submit",
                                id='submit-button'
                            ),
                        ], style={'margin': "5px 5px 5px 5px"}),

                        html.Div([
                            html.Button(
                                "STOP",
                                id='stop-button'
                            ),
                        ], style={'margin': "5px 5px 5px 5px"}),

                    ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '10px', 'margin': "5px 5px 5px 5px", 'border': '1px solid #1C6EA4', 'text-align': 'center'}),

                    html.Div([
                        html.Label('Status'),
                        dcc.Loading(id="loading", type='dot', children=[html.Div("IDLE", id="wait-spinner", style={'font-size': '25px'})])
                    ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '10px 10px', 'margin': "5px 5px 5px 5px", 'border': '1px solid #1C6EA4', 'text-align': 'center'}),

                ], style={'width': '15%', 'display': 'flex', 'flexDirection': 'column'}),

                # left frame - end

                # center frame - start

                html.Div([

                    html.Div([

                        dcc.RadioItems(
                            id="plot-type",
                            options=[
                                {'label': 'Time Domain', 'value': DataFormat.VOLTAGE},
                                {'label': 'FFT', 'value': DataFormat.FFT},
                            ],
                            value=DataFormat.VOLTAGE,   
                            labelStyle={'display': 'inline-block'}
                        ),
                    ], style={'display': 'flex', 'justify-content': 'center'}),

                    html.Div([
                        dcc.Graph(
                            id='plot',
                            figure={
                                'layout': {
                                    'title': 'Data Visualization'
                                }
                            }
                        ),
                    ]),

                    html.Div([
                        html.Label(id='info-params'),
                    ]),

                ], style={'width': '100%', 'display': 'flex', 'flexDirection': 'column', 'borderBottom': 'thin lightgrey solid', 'backgroundColor': 'rgb(250, 250, 250)', 'padding': '10px 5px'})

                # center frame - end
            
            ], style={'width': '85%', 'display': 'flex'}),
        
        ], style={'width': '100%', 'display': 'flex', 'flexDirection': 'column'}),
    
    ], style={'display': 'flex', 'border': '1px solid #1C6EA4'})

#
# callbacks
#

@app.callback(  Output('stop-button', 'children'),
                [Input('stop-button', 'n_clicks')])
def stop_acquisition(value):
    purgeAllTasks(queue)
    raise PreventUpdate

@app.callback(  [Output('plot', 'figure'), 
                Output('wait-spinner', 'children'),
                Output('info-params', 'children')], 
                [Input('submit-button', 'n_clicks'),
                Input('plot-type', 'value')], 
                [State('waveform_length', 'value'),
                State('channel', 'value'),
                State('adcclockdiv', 'value'),
                State('fmoddiv', 'value'),
                State('filter', 'value'),
                State('decimation', 'value')])
def update_plot(value, plotType, length, channel, adcclockdiv, fmoddiv, filter, decrate):
    ctx = dash.callback_context
    name = ctx.triggered[0]['prop_id'].split('.')[0]
    if value is None:
        # dash initialization
        purgeAllTasks(queue)
        raise PreventUpdate
    else:
        data_for_graph = []
        if name == "submit-button":
            if(filter == Filter.SINC5):
                group = ChannelGroup.A
            else:
                group = ChannelGroup.B
            ch = chord((setLength.s(length), selectChannel.s(channel), setFilter.s(filter, decrate), setMasterClockDiv.s(adcclockdiv), setModulatorDiv.s(group,fmoddiv)))
            result = ch(getWaveform.s(fmt=plotType))
        elif name == "plot-type":
            result = fetchWaveform.delay(fmt=plotType)
        while result.ready() is False:
            sleep(0.5)
        wf = result.get()
        data_for_graph.append(dict(x = wf["x"], y = wf["y"], line = linestyle))

        return {'data': data_for_graph}, 'IDLE', \
            f"Plot generated with: channel = {channel}, length = {length}, filter = {wf['filtername']}, \
                decimation = {wf['decname']}, ADC clock freq. = {wf['adcclockfreq']}, \
                clock error =  {wf['clock_error']}, chip_error = {wf['chip_error']}"

#@app.callback(  Output('measuring', 'value'),
#                [Input('submit-button', 'n_clicks'), 
#                Input('plot', 'figure')])
#def update_indicator(value, plot):
#    if value is not None:
#        ctx = dash.callback_context
#        name = ctx.triggered[0]['prop_id'].split('.')[0]
#        return (name == 'submit-button')
#    raise PreventUpdate

#
# main
#

if __name__ == '__main__':
    app.run_server(debug = True, host='0.0.0.0')
