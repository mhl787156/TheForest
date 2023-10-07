import argparse
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
from dash_extensions import WebSocket 
import dash_bootstrap_components as dbc

class GUI():

    def __init__(self):

        self.app = Dash(__name__, external_stylesheets=[dbc.themes.QUARTZ])

        self.init_layout()
        self.init_callbacks()

    def init_layout(self):
        ###############
        ## Layouts ##
        ###############

        self.html_main_content = html.Div(className='container-fluid', children=[
            html.Div(className='row', children=[
                html.Div(id='output'),
                # html_side_bar,
                # dbs_side_bar,
                # html_graph_content,
                # dbc_recompute_modal
            ])
            ], style={
                # 'backgroundColor': 'rgb(250, 250, 250)',
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

        read_websocket = """
        function(msg) {
            if(!msg){return "Nothing Received Yet";}
            return JSON.parse(msg.data);
        }"""
        self.app.clientside_callback(read_websocket, Output("output", "children"), Input("ws", "message"))

        # @self.app.callback(Output("output", "children"), [Input("ws", "message")])
        # def message(e):
        #     if e is not None:
        #         return f"Response from websocket: {e['data']}"
        #     return "Nothing received yet"

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


