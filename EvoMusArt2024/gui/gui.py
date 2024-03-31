import argparse
import dash
from dash import Dash, html, dcc, ClientsideFunction, callback_context
from dash.dependencies import Input, Output, State, ALL
from dash_extensions import WebSocket 
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import colorsys
import json

class GUI():

    def __init__(self, ws_host, ws_port):

        self.app = Dash(
            __name__, 
            external_stylesheets=[dbc.themes.QUARTZ],
            update_title=None,
            # prevent_initial_callbacks=True,
        )

        self.ws = (ws_host, ws_port)

        self.pillar_figure = go.Figure()
        print("Pillar figure", self.pillar_figure)

        self.pillar_status_children = None
        self.data = None

        self.update_dat = dict( # ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]
            serial_port={},
            amp = {},
            pitch = {},
            synth = {},
            bpm = {},
            pan = {},
            envelope = {}
        )

        self.display_dat = dict(
            touch = {},
            #params = {}
        )

        self.app.layout = self.init_layout()
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
            html.Div(id='system-status-dummy-output')
        ])

        self.pillar_status = html.Div(id="pillar-status",  children=[]) # Fill in dynamically

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
            dcc.Interval(id='interval-component', interval=1000/5, n_intervals=0),  # Trigger every 200ms
            html.Div(id="websocket-holder", children=WebSocket(id="ws", url=f"ws://{self.ws[0]}:{self.ws[1]}")),
            html.Div(id='dummy-output', style={'display': 'none'}),  # Hidden dummy output component
            html.Div(id={"type": f"pillar-status-label", "index": "dummy"}, style={'display':'none'})
        ])

        self.html_header_content = html.Div([
                dbc.Row([
                    dbc.Col(html.Div(
                    html.H1('Alien-Forest Dashboard'),
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
            Output("pillar-status", "children"),
            Input("refresh-button", "n_clicks")
        )
        def refresh_page(n_clicks):
            print("I am refreshing the page")
            if self.data:
                print("Get data and go to generate pillars")
                return self.generate_pillar_status(self.data)
            return dash.no_update
        
        @self.app.callback(
            [
                Output("output", "children"),
                Output("pillar_graph", "figure"),
                Output({"type": f"pillar-status-label", "index": ALL}, "children") 
            ], 
            Input("ws", "message"),
            prevent_initial_call=False)
        def receive_from_websocket(e): 
            if e is None:
                print("e is none")
                #return [dash.no_update for _ in range(2)] + [ [dash.no_update] for _ in dash.callback_context.outputs_list[2] ] 
                #return dash.no_update, dash.no_update, [dash.no_update] * len(dash.callback_context.outputs_list[2])  
                raise PreventUpdate

            data = json.loads(e['data']) # This is the data from the websocket?
            self.data = data
            # print(f"Received data: {data}")

            self.update_data(data)
            #print(len(data), data.keys())

            self.pillar_figure = self.generate_pillars_figure(data)

            outputs = dash.callback_context.outputs_list
        
            status_labels_update = outputs[2]
            #print("Status labels update", status_labels_update)
            labs = self.generate_updated_labels(status_labels_update)

            return f"Response from websocket: {data}", self.pillar_figure, labs # data update the children of output, self.pillar_figure update the figure of pillar_graph, labs update the children of pillar-status-label

        @self.app.callback(
            [
                Output("ws", "send"),
                Output("system-status-dummy-output", "children"),
            ],
                Input("pillar_graph", "clickData"),
                State({"type": f"pillar-status-input", "index": ALL}, "value") # pillar-status-input 
        )
        def update_output(graph_click_data, psi_values):
            ws_out = {}
            msg = "No updates"  # Default message when there are no updates

            ctx = callback_context
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]  # Extract the component ID that triggered the callback

            if triggered_id == "pillar_graph" and graph_click_data:
                # Handle clicks on the graph
                print("Graph clicked")
                if 'points' in graph_click_data:
                    data = graph_click_data['points']
                    if len(data) > 0:
                        point = data[0]
                        if "curveNumber" in point and "pointNumber" in point:
                            p_id = point['curveNumber']
                            t_id = point['pointNumber']
                            # Touch status of tubes in a pillar
                            out = [False for _ in range(int(self.data["pillars"][str(p_id)]["num_tubes"]))]
                            out[t_id] = True
                            ws_out["touch"] = {str(p_id): out}
                            msg = f"Updated pillar {p_id}, tube {t_id}"
                            
                        else:
                            out = [False for _ in range(int(self.data["pillars"][str(p_id)]["num_tubes"]))]
                            ws_out["touch"] = {str(p_id): out}
                            msg = f"Tubes stop been touched"
            elif "{" in triggered_id:  # Handle dynamic triggers
                try:
                    # Assuming triggered_id is a stringified JSON that includes "index" key
                    prop_dict = json.loads(triggered_id.replace("'", "\""))  # Ensure proper JSON format
                    p_id, var = prop_dict["index"].split("-")

                    # If psi_value (pillar_status_input_values) is not directly provided, ensure it's obtained properly
                    psi_value = [state['value'] for state in psi_values if state['id']['index'] == prop_dict["index"]]

                    if var not in ws_out:
                        ws_out[var] = {}

                    if psi_value:
                        
                        ws_out[var][p_id] = psi_value['value']  # Example of updating ws_out with the first relevant value
                        msg = f"Dynamic update for {var} on pillar {p_id}"
                except json.JSONDecodeError:
                    print("Error decoding JSON from triggered_id")
            else:
                ws_out = {}
                raise PreventUpdate

            print(f"WS_OUT: {ws_out}")
            return json.dumps(ws_out), msg
                
    """    
        def update_output(graph_click_data, psi_n_clicks):
            ctx = dash.callback_context
            msg = dash.no_update
            ws_out = {}
            #out = None
            if ctx.triggered:
                print("Triggered")
                triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
                if triggered_id == "pillar_graph" and graph_click_data:
                    print("Graph clicked")
                    print(graph_click_data)  
                    if 'points' in graph_click_data:
                        print("Points in graph click data")
                        data = graph_click_data['points']
                        print("Data",data)
                        if len(data) > 0:
                            point = data[0]
                            print("Point", point)
                            if "curveNumber" in point and "pointNumber" in point:
                                p_id = point['curveNumber']
                                t_id = point['pointNumber']
                                out = [False for _ in range(int(self.data["pillars"][str(p_id)]["num_tubes"]))]
                                out[t_id] = True
                    else:
                        out = [False for _ in range(int(self.data["pillars"][str(p_id)]["num_tubes"]))]
                        print("STOP TOUCHING THE PILLARS")
                    if "touch" not in ws_out:
                        print("STOP TOUCHING THE PILLARS")
                        ws_out["touch"]  = {}
                    ws_out["touch"][str(p_id)] = out
                elif "{" in triggered_id and any(psi_value):
                    
                    print("INSIDE ELSE IF")
                    
                    # One of the dynamic ones triggered lets find which one
                    print("Pillar status triggered")
                    prop_dict = json.loads(triggered_id)

                    l = [s["id"]['index'] for s in ctx.states_list[5]]
                    #psi_value_idx = l.index(prop_dict["index"])
                    
                    p_id, var = prop_dict["index"].split("-")
                    if var not in ws_out:
                        ws_out[var] = {}
                    #ws_out[var][p_id] = psi_value[psi_value_idx]
            #else:
            #    print("No trigger")
                #out = [False for _ in range(int(self.data["pillars"][str(0)]["num_tubes"]))]
                #if "touch" not in ws_out:
                #    ws_out["touch"]  = {}
                
            print(f"WS_OUT: {ws_out}")        
            if ws_out:
                print(f"Sending {ws_out}")
            print(f"Sending {json.dumps(ws_out)}")
            return json.dumps(ws_out), msg

        
        print("Callbacks initialized")
        """

    def generate_pillars_figure(self, data):
        pillars_dict, current_status = data['pillars'], data["current_state"]

        num_pillars = len(pillars_dict)
        #print("CURRENT STATUS", current_status)
        
        print("Pillars have been generated")


        def generate_coords_tubes(num_tubes, radius):
           # print("NUM TUBES", num_tubes)


            # Calculate the angles at which the points should be placed
            angles = np.linspace(0, 2*np.pi, num_tubes, endpoint=False)
            
            # Calculate the x and y coordinates of the points on the circle
            x = radius * np.cos(angles)
            y = radius * np.sin(angles)
            
            points = [[x[i], y[i]] for i in range(num_tubes)]

            # Move (0,0) to front if central tube is first in array
            return np.array([[0,0]] + points)
        
        dist_between_centers = np.array([0, 100])
        
        fig = make_subplots(rows=1, cols=num_pillars, 
                            subplot_titles=[f"Pillar {p_id}" for p_id in pillars_dict])

        for i, (p_id, pillar) in enumerate(pillars_dict.items()):
            #print("Pillar", pillar)
            tube_coords = generate_coords_tubes(int(pillar["num_sensors"]), 1)
            current_status_lights = current_status[str(i)]["lights"]
            colours = [f"hsv({l[0]}, 255, {l[1]})" for l in current_status_lights]
            marker_widths = [10 if bool(t) else 2 for t in pillar["touch_status"]]
            marker_colors = ["DarkSlateGrey" if bool(t) else "white" for t in pillar["touch_status"]]
            labels = [f"{i},hue:{l[0]}" for i, l in zip(range(pillar["num_tubes"]), current_status_lights)]
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
            
            fig.add_trace(trace, row=1, col=i+1)
        
        fig.update_layout(showlegend=False)
        fig.update_layout(clickmode='event+select')
            
        return fig


    def update_data(self, data):
        #print("Updating data", data["current_state"]['0'])
        num_pillars = data["num_pillars"]

        
        #print("Current state", data["current_state"])
        for p_id in range(num_pillars):
            print("DATA CURRENT STATE", data["current_state"])
            # data["pillars"] = {'id', 'num_tubes', 'num_sensors', 'touch_status', 'light_status', 'serial_status': {'connected':, 'port':, 'baud_rate'} --- 6 keys
            # data["current_state"] = {'lights', 'params'} --- 2 keys
            # Current state {{'lights': 
            # 'params': {'amp': 10, 'pitch': 60, 'synth': 'dsaw', 'bpm': 50, 'pan': -1, 'envelope': 1}}
            #["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]
            self.update_dat["serial_port"][p_id]=data["pillars"][str(p_id)]["serial_status"]["port"]
            self.update_dat["amp"][p_id] = data["current_state"][str(p_id)]["params"]["amp"]
            self.update_dat["pitch"][p_id] = data["current_state"][str(p_id)]["params"]["pitch"]#data.get("pitch", {}).get(str(p_id))
            self.update_dat["synth"][p_id] = data["current_state"][str(p_id)]["params"]["synth"]#data.get("synth", {}).get(str(p_id))
            self.update_dat["bpm"][p_id] = data["current_state"][str(p_id)]["params"]["bpm"]#data.get("bpm", {}).get(str(p_id))
            self.update_dat["pan"][p_id] = data["current_state"][str(p_id)]["params"]["pan"]#data.get("pan", {}).get(str(p_id))
            self.update_dat["envelope"][p_id] = data["current_state"][str(p_id)]["params"]["envelope"]#data.get("envelope", {}).get(str(p_id))         

            self.display_dat["touch"][p_id] = data["pillars"][str(p_id)]["touch_status"] # display what? where? GOT IT
            self.display_dat["touch"][p_id] = [int(t) for t in self.display_dat["touch"][p_id]]
            #self.display_dat["params"][p_id] = data["current_state"][str(p_id)]["params"] # put params in display data
            #self.display_dat["pan"][p_id] = data["pan"][str(p_id)]

    def generate_pillar_status(self, data):
        #print("I got here")
        num_pillars = data["num_pillars"]

        output_div = []
        for p_id in range(num_pillars):
            
            update_dat = {n: d[p_id] for n, d in self.update_dat.items() if p_id in d}

            display_dat = {n: d[p_id] for n, d in self.display_dat.items() if p_id in d}

            connected = bool(data["pillars"][str(p_id)]["serial_status"]["connected"])
            row_div = [
                html.Div(children=f"Pillar {p_id} status: {'connected' if connected else 'not-connected'}"),
            ]
            for n, val in display_dat.items():
                #print(f"Display data: {n} {val}")
                h = dbc.Col(dbc.Row([
                    dbc.Label(f"{n}", width=2),
                    dbc.Label(id={"type": f"pillar-status-label", "index": f"{p_id}-{n}"}, width=2), # add default value default_value = val
                ]))
                row_div.append(h)
                
            for n, val in update_dat.items():
                h = dbc.Row([
                    dbc.Label(f"{n}", width=2),
                    dbc.Label(id={"type": f"pillar-status-label", "index": f"{p_id}-{n}"}, width=2),
            #        dbc.Col(dbc.Input(id={"type": f"pillar-status-input", "index": f"{p_id}-{n}"}, placeholder=f"Enter {n}"),width="auto"),
            #        dbc.Col(dbc.Button("Update", id={"type": f"pillar-status-button", "index": f"{p_id}-{n}"}, color="primary"),width=1),
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
            p_id, var = name.split("-")
            if var in self.update_dat:
                value = self.update_dat[var][int(p_id)]
            elif var in self.display_dat:
                value = self.display_dat[var][int(p_id)]
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


