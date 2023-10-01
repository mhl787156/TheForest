from dash import Dash, html
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.QUARTZ])


###############
## Layouts ##
###############




app.layout = html.Div([
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


if __name__ == '__main__':
    app.run(debug=True)