from dash import Dash, html
import dash_bootstrap_components as dbc

class GUI():

    def __init__(self, controller):

        self.controller = controller

        self.app = Dash(__name__, external_stylesheets=[dbc.themes.QUARTZ])


        ###############
        ## Layouts ##
        ###############

        html_main_content = html.Div(className='container-fluid', children=[
            html.Div(className='row', children=[
                # html_side_bar,
                # dbs_side_bar,
                # html_graph_content,
                # dbc_recompute_modal
            ])
            ], style={
                # 'backgroundColor': 'rgb(250, 250, 250)',
                'padding': '10px 5px',
            })


        self.app.layout = html.Div([
                html.Div(
                    html.H1('RaveForest Dashboard'),
                    style=dict(padding=5)
                ),
            ], style={
                'height': '100%',
                'overflow': "hidden",
                'borderBottom': 'thin lightgrey solid',
        })


        ###############
        ## CALLBACKS ##
        ###############

    def run(self, **kwargs):
        self.app.run(**kwargs)
        

if __name__ == '__main__':
    GUI(None).run(debug=True)