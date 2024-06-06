import argparse
import dash
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State, ALL
from dash_extensions import WebSocket 
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

class GUI():

    def __init__(self, ws_host, ws_port):
        self.app = Dash(
            __name__, 
            external_stylesheets=[dbc.themes.QUARTZ],
            update_title=None,
        )

        self.ws = (ws_host, ws_port)

        self.pillar_figure = go.Figure()
        self.pillar_status_children = None
        self.data = None

        self.update_dat = dict(
            serial_port = {},
            amp = {},
            pitch = {},
            synth = {},
            bpm = {},
            pan = {},
            envelope = {}
        )
        

        self.display_dat = dict(
            touch = {},
        )

        # Store the click states
        self.click_state = {}

        self.app.layout = self.init_layout()
        self.init_callbacks()

    def init_layout(self):
        self.pillar_graph = html.Div([
            dcc.Graph(id="pillar_graph", figure=self.pillar_figure)
        ])

        self.system_status = html.Div([
            html.Div(id='output', style={'display': 'none'}),
            html.Div(id='system-status-dummy-output')
        ])

        self.pillar_status = html.Div(id="pillar-status",  children=[])

        self.html_main_content = html.Div(className='container-fluid', children=[
            html.Div(className='row', children=[
                self.system_status,   
                self.pillar_graph,
                self.pillar_status
            ])
            ], style={
                'padding': '10px 5px',
            })
        

        self.utility_content = html.Div([
            dcc.Interval(id='interval-component', interval=1000/5, n_intervals=0),  
            html.Div(id="websocket-holder", children=WebSocket(id="ws", url=f"ws://{self.ws[0]}:{self.ws[1]}")),
            html.Div(id='dummy-output', style={'display': 'none'}), 
            html.Div(id={"type": f"pillar-status-label", "index": "dummy"}, style={'display':'none'})
        ])

        self.html_header_content = html.Div([
                dbc.Row([
                    dbc.Col(html.Div(
                    html.H1('Forest Dashboard - FON Vol2', className='header-title'),
                    style=dict(padding=5)
                    ), width=6),
                    dbc.Col(dbc.Button("Refresh", id="refresh-button"), width="auto")
                    ], justify="end"
                ),
                self.utility_content,
            ], style={
                'height': '100%',
                'overflow': "hidden",
                'borderBottom': 'thin lightgrey solid',
        })

        return html.Div([
            self.html_header_content,
            self.html_main_content
        ])

    def init_callbacks(self):
        @self.app.callback(
            Output("pillar-status", "children"),
            Input("refresh-button", "n_clicks")
        )
        def refresh_page(n_clicks):
            if self.data:
                return self.generate_pillar_status(self.data)
            return dash.no_update
        
        @self.app.callback(
            [
                Output("output", "children"),
                Output("pillar_graph", "figure"),
                Output({"type": f"pillar-status-label", "index": ALL}, "children") 
            ], 
            [Input("ws", "message")])
        def receive_from_websocket(e):
            if e is None:
                
                return dash.no_update, dash.no_update, [dash.no_update] * len(dash.callback_context.outputs_list[2])  

            data = json.loads(e['data'])
            self.data = data
            self.update_data(data)

            self.pillar_figure = self.generate_pillars_figure(data)

            outputs = dash.callback_context.outputs_list
            status_labels_update = outputs[2]
            labs = self.generate_updated_labels(status_labels_update)

            return f"Response from websocket: {data}", self.pillar_figure, labs 

        @self.app.callback(
            [
                Output("ws", "send"),
                Output("system-status-dummy-output", "children"),
            ],
            [
                Input("pillar_graph", "clickData")
            ],
            [
                State({"type": f"pillar-status-input", "index": ALL}, "value")
            ]
        )
        def update_output(graph_click_data, psi_value):
            ctx = dash.callback_context
            
            ws_out = {}
            if ctx.triggered:
                triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
                print("Triggered ID:", triggered_id)
                if triggered_id == "pillar_graph" and graph_click_data:
                    if 'points' in graph_click_data:
                        data = graph_click_data['points']
                        if len(data) > 0:
                            point = data[0]
                            print("Point:", point)
                            if "curveNumber" in point and "pointNumber" in point:
                                print("Point:", point)
                                #p_id = point['curveNumber']
                                t_id = point['pointNumber']

                                if t_id not in self.click_state:
                                    self.click_state[t_id] = False

                                if not self.click_state[t_id]:
                                    self.click_state[t_id] = True
                                    ws_out["touch"] = ws_out.get("touch", {})
                                ws_out["touch"] = self.click_state
                else:
                    self.click_state = [False] * len(self.data["pillar"]["touch_status"])
                    ws_out["touch"] = self.click_state
                    
                    
            print("WS OUT:", ws_out)

            return [json.dumps(ws_out), dash.no_update]
        
    def generate_pillars_figure(self, data):
        pillars_dict, current_status = data, data["current_state"]
        

        def generate_coords_tubes(num_tubes, radius):
            angles = np.linspace(0, 2*np.pi, num_tubes, endpoint=False)
            x = radius * np.cos(angles)
            y = radius * np.sin(angles)
            points = [[x[i],  y[i]] for i in range(num_tubes)]
            return np.array(points)
        
        fig = make_subplots(rows=1, cols=1, 
                            subplot_titles=[f"Pillar" ])

        
        #for i,  pillar in enumerate(data["pillar"]): #todo: check if this is correct
        tube_coords = generate_coords_tubes(int(data["pillar"]["num_touch_sensors"]), 1)
        current_status_lights = current_status["lights"]
        colours = [f"hsv({l[0]}, 255, {l[1]})" for l in current_status_lights]
        marker_widths = [10 if bool(t) else 2 for t in data["pillar"]["touch_status"]]
        marker_colors = ["DarkSlateGrey" if bool(t) else "white" for t in data["pillar"]["touch_status"]]
        labels = [f"{i},hue:{l[0]}" for i, l in zip(range(data["pillar"]["num_tubes"]), current_status_lights)]
            
        # Update the color for clicked tubes
        print("Click state:", self.click_state)
        for idx, clicked in enumerate(self.click_state):
            if clicked:
                colours[idx] = 'rgba(255,0,0,0.5)'


        trace = go.Scatter(
            x=tube_coords[:, 0], 
            y=tube_coords[:, 1],
            marker=dict(
                color=colours, 
                size=50,
                line=dict(
                    color=marker_colors,
                    width=marker_widths
                )
            ),
            mode="markers+text",
            text=labels,
            textposition="top center")
        
        fig.add_trace(trace, row=1, col=1)
        
        fig.update_layout(showlegend=True)
        fig.update_layout(clickmode='event')
            
        return fig

    def update_data(self, data):

        self.update_dat["serial_port"] = data["pillar"]["serial_status"]["port"]
        self.update_dat["amp"] = data["pillar"]["current_state"]["params"]["amp"]
        self.update_dat["pitch"] = data["pillar"]["current_state"]["params"]["pitch"]
        self.update_dat["synth"] = data["pillar"]["current_state"]["params"]["synth"]
        self.update_dat["bpm"] = data["pillar"]["current_state"]["params"]["bpm"]
        self.update_dat["pan"] = data["pillar"]["current_state"]["params"]["pan"]
        self.update_dat["envelope"] = data["pillar"]["current_state"]["params"]["envelope"]        
        self.display_dat["touch"] = data["pillar"]["touch_status"]
        
        

    def generate_pillar_status(self, data):
        
        output_div = []

        update_dat = {n: d for n, d in self.update_dat.items() }
        display_dat = {n: d for n, d in self.display_dat.items() }
        

        connected = bool(data["pillar"]["serial_status"]["connected"])
        row_div = [
            html.Div(children=f"Pillar status: {'connected' if connected else 'not-connected'}"),
        ]
        for n, val in display_dat.items():
            h = dbc.Col(dbc.Row([
                dbc.Label(f"{n}", width=2),
                dbc.Label(id={"type": f"pillar-status-label", "index": f"{n}"}, width=2), 
            ]))
            row_div.append(h)
        
        for n, val in update_dat.items():
            h = dbc.Row([
                dbc.Label(f"{n}", width=2),
                dbc.Label(id={"type": f"pillar-status-label", "index": f"{n}"}, width=2),
            ])
            row_div.append(h)
        
        output_div.append(dbc.Col(html.Div(row_div), width=5))
            
        return dbc.Row(output_div, justify="evenly")
    
    def generate_updated_labels(self, label_objs):
        status_labels = []
        
        for out_id in label_objs:
            name = out_id['id']['index']
            if name == "dummy":
                status_labels.append(dash.no_update)
                continue
            var = name
            if var in self.update_dat:
                value = self.update_dat[var]
            elif var in self.display_dat:
                value = self.display_dat[var]
            else:
                status_labels.append(dash.no_update)
            status_labels.append(f"{value}")
        return status_labels
        
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

    GUI(args.ws_host, args.ws_port).run(debug=True, host=args.host, port=args.port)
