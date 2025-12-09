# app.py

from flask import Falsk
from markupsafe import escape
from flask import render_template

app = Flask(__name__) # name of the application’s module or package.

@app.route("/home/<name>")
def home(name = None):
    ''' return "<p> Hello this is front page </p>" #returning HTML (the default response type in Flask)
                or
        name = request.args.get("name", "Flask")
        return f"Hello, {escape(name)}!"
    '''
    return render_template('home.html', person = name)




'''
Externally Visible Server

If you run the server you will notice that the server is only accessible from your own computer, not from any other in the network. This is the default because in debugging mode a user of the application can execute arbitrary Python code on your computer.

If you have the debugger disabled or trust the users on your network, you can make the server publicly available simply by adding --host=0.0.0.0 to the command line:

$ flask run --host=0.0.0.0

This tells your operating system to listen on all public IPs.

'''

