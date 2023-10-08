import argparse
import dash
from dash import Dash, html, dcc, ClientsideFunction
from dash.dependencies import Input, Output, State
from dash_extensions import WebSocket 
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import colorsys
import json

class GUI():

    def __init__(self):

        self.app = Dash(
            __name__, 
            external_stylesheets=[dbc.themes.QUARTZ],
            update_title=None
        )

        self.pillar_figure = go.Figure()

        self.init_layout()
        self.init_callbacks()


    def init_layout(self):
        ###############
        ## Layouts ##
        ###############

        self.pillar_graph = html.Div([
            dcc.Graph(id="pillar_graph", figure=self.pillar_figure)
        ])

        self.system_status = html.Div([
            html.Div(id='output', style={'display': 'none'}),
            dbc.Row([
                dbc.Label("Current Beats Per Minute", width=2),
                dbc.Label(id="bpm-output", width=1),
                dbc.Col(dbc.Input(id="bpm-input", type="number", placeholder="Enter BPM"), width=4),
                dbc.Col(dbc.Button("Update", id="bpm-button", color="primary"), width=2),
            ]),
    
            dbc.Row([
                dbc.Label("Mapping ID", width=2),
                dbc.Label(id="mapping-output", width=1),
                dbc.Col(dbc.Input(id="mapping-input", type="number", placeholder="Enter Mapping ID"),width=4),
                dbc.Col(dbc.Button("Update", id="mapping-button", color="primary"),width=2),
            ]),
            html.Div(id='system-status-dummy-output')
        ])

        self.html_main_content = html.Div(className='container-fluid', children=[
            html.Div(className='row', children=[
                self.pillar_graph,
                self.system_status   
            ])
            ], style={
                'padding': '10px 5px',
            })
        

        self.utility_content = html.Div([
            dcc.Interval(id='interval-component', interval=1000/5, n_intervals=0),  # Trigger every 200ms
            WebSocket(id="ws", url="ws://127.0.0.1:8765"),
            html.Div(id='dummy-output', style={'display': 'none'})  # Hidden dummy output component
        ])

        self.html_header_content = html.Div([
                html.Div(
                    html.H1('RaveForest Dashboard'),
                    style=dict(padding=5)
                ),
                self.utility_content,
            ], style={
                'height': '100%',
                'overflow': "hidden",
                'borderBottom': 'thin lightgrey solid',
        })

        self.app.layout = html.Div([
            self.html_header_content,
            self.html_main_content
        ])


    def init_callbacks(self):
        ###############
        ## CALLBACKS ##
        ###############

        # self.app.clientside_callback(
        #     ClientsideFunction(
        #         namespace="clientside",
        #         function_name='read_message'
        #     ), 
        #     Output("output", "children"), 
        #     Input("ws", "message"))

        @self.app.callback(
            [
                Output("output", "children"),
                Output("pillar_graph", "figure"),
                Output("bpm-output", "children"),
                Output("mapping-output", "children"),
            ], 
            [Input("ws", "message")])
        def receive_from_websocket(e):
            if e is None:
                return [dash.no_update for _ in range(4)]    

            data = json.loads(e['data'])
            print(data)
            self.pillar_figure = self.generate_pillars_figure(data['pillars'], data["current_state"])
            return [
                f"Response from websocket: {data}", 
                self.pillar_figure,
                data["bpm"],
                data["mapping_id"]
            ]

        @self.app.callback(
            [
                Output("ws", "send"),
                Output("system-status-dummy-output", "children"),
            ],
            Input("bpm-button", "n_clicks"),
            Input("mapping-button", "n_clicks"),
            Input("bpm-input", "value"),
            Input("mapping-input", "value"),
        )
        def update_output(bpm_n_clicks, mapping_n_clicks, bpm_value, mapping_value):
            ctx = dash.callback_context
            msg = dash.no_update
            ws_out = {}
            if ctx.triggered:
                triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
                
                if triggered_id == "bpm-button" and bpm_value is not None:
                    msg=f"Updating Current BPM: {bpm_value}"
                    ws_out["bpm"] = bpm_value
                elif triggered_id == "mapping-button" and mapping_value is not None:
                    msg=f"Updating Mapping ID: {mapping_value}"
                    ws_out["mapping_id"] = mapping_value

            return [
                json.dumps(ws_out),
                msg
            ]

    def generate_pillars_figure(self, pillars_dict, current_status):
        num_pillars = len(pillars_dict)

        def generate_coords_tubes(num_tubes, radius):

            # Calculate the angles at which the points should be placed
            angles = np.linspace(0, 2*np.pi, num_tubes, endpoint=False)
            
            # Calculate the x and y coordinates of the points on the circle
            x = radius * np.cos(angles)
            y = radius * np.sin(angles)
            
            points = [[x[i], y[i]] for i in range(num_tubes)]

            return np.array(points + [[0, 0]])
        
        dist_between_centers = np.array([0, 100])
        
        fig = make_subplots(rows=1, cols=num_pillars, 
                            subplot_titles=[f"Pillar {p_id}" for p_id in pillars_dict])

        for i, (p_id, pillar) in enumerate(pillars_dict.items()):
            tube_coords = generate_coords_tubes(int(pillar["num_tubes"]), 1)
            current_status_lights = current_status[str(i)]["lights"]
            colours = [f"hsv({l[0]}, {l[1]}, 100)" for l in current_status_lights]
            trace = go.Scatter(
                x=tube_coords[:, 0], 
                y=tube_coords[:, 1],
                marker=dict(
                    color=colours, 
                    size=50
                ),
                mode="markers")
            
            fig.add_trace(trace, row=1, col=i+1)
        
        fig.update_layout(showlegend=False)
            
        return fig


    def run(self, **kwargs):
        self.app.run(**kwargs)
        
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--host", default="127.0.0.1", help="The host to connect to.")
    parser.add_argument("--port", default="8080", type=int, help="The port to use.")
    parser.add_argument("--debug", default=False, action="store_true", help="Whether to run the Dash GUI")

    parser.add_argument("--ws-host", default="localhost", help="The internal websocket URI")
    parser.add_argument("--ws-port", default="8765", help="The internal websocket URI")

    args = parser.parse_args()

    GUI().run(debug=True, host=args.host, port=args.port)


