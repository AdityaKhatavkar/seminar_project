#client_new.py

import sys
import os
import signal
import subprocess
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security  import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy 
from authlib.integrations.flask_client import OAuth
from ip2geotools.databases.noncommercial import DbIpCity #ip --> location

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configure SQL Alchemy
# URI : Uniform Resource Identifier : A string (text) that tells SQLAlchemy how and where to connect to your database.
app.config["SQLALCHEMY_DATABASE_URI"] =  "sqlite:///users.db" # can be "mysql://user:pass@localhost/dbname"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


from dotenv import load_dotenv
load_dotenv()

#auth
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id = os.getenv("GOOGLE_CLIENT_ID"),
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    #authorize_url='https://accounts.google.com/o/oauth2/auth',
    #access_token_url='https://oauth2.googleapis.com/token',
    client_kwargs={
        'scope': 'openid profile email'
    }
)


# Database Model ~ single row in our database 
class User(db.Model):
    #class variables
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(25), unique = True, nullable = False)
    password_hash = db.Column(db.String(150), nullable=True)
    location = db.Column(db.String(150), nullable=True) #modify for location, keep in the mind
    fl_pid = db.Column(db.Integer, nullable=True)   # PID of client process (optional)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



# Helping Functions : 
"""ip to location conversion"""
def get_ip_location(): # ip-->location(lat & long) function
    try:
        ip = request.remote_addr
        response = DbIpCity.get(ip, api_key='free')

        lat = response.latitude
        lon = response.longitude
        
        return f"{lat},{lon}"
    except:
        return "unknown"
    


#starting swap client_runner.py
def spawn_fl_client_process(agent_name: str) -> int:
    """
    Spawn client_runner.py as a background process.
    Returns the process PID.
    """
    print("Entered in spawn_fl_client_process_function")
    python_exec = sys.executable
    runner_path = os.path.join(os.path.dirname(__file__), "client_runner.py")
    project_root = "/home/aditya/seminar_project/simple_fl"

    if not os.path.exists(runner_path):
        raise FileNotFoundError(f"client_runner.py not found at {runner_path}")

    cmd = [python_exec, "-m", "fl_main.agent.client_runner", agent_name]

    # Start background process (detached-ish). Adjust stdout/stderr as needed.
    proc = subprocess.Popen(cmd, cwd = project_root)
    print("Completed spawn_fl_client_process.")
    return proc.pid
    

# Helping routs
@app.route("/save_location", methods=["POST"])
def save_location():
    session["location"] = request.json.get("location", "unknown")
    return {"status": "Location ok"} 



# Admin endpoints
# stopping fl client
@app.route("/admin/stop/<username>", methods =['POST'])
def stop_fl_client(username):
    user = User.query.filter_by(username=username).first_or_404()

    if not user.fl_pid:
        return {"Status : No Running Process"}

    try : 
        os.kill(user.fl_pid, signal.SIGTERM)
        user.fl_pid = None
        db.session.commit()
        return {"Status : Session Stopped"}
    
    except Exception as e:
        return {"Error " : str(e)},500
    
    
#list all clients
@app.route("/admin/clients")
def list_clients():
    users = User.query.all()
    data = []
    for u in users:
        data.append({
            "username": u.username,
            "location": u.location,
            "pid": u.fl_pid
        })
    return {"clients": data}

    
# Routs 
@app.route("/")
def home():
    if "username" in session : 
        return redirect(url_for("dashboard"))
    return render_template("home_extends.html")


# Login
@app.route("/login", methods = ["POST"])
def login():
    #collect data from the user 
    username = request.form['username']
    password = request.form['password']
    location = request.form.get("location", "unknown")
    #location = session.get("location")


    if not location or location == "unknown":
        location = get_ip_location()


    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['username'] = username
        return redirect(url_for("dashboard"))
    else:
        return redirect(url_for("home"))
    

# Register
@app.route("/register", methods = ["POST"])
def register():
    username = request.form['username']
    password = request.form['password']
    # location = request.form[''] # Location part, keep in the mind
    location = request.form.get("location", "unknown")

    if not location or location == "unknown":
        location = get_ip_location()
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return render_template("home_extends.html", error="User already exitst.")
    
    new_user = User(username= username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    print("In register route, about to start fl client by entering in the try block")

    #start fl client process : 
    try: 
        pid = spawn_fl_client_process(username)
        new_user.fl_pid = pid
        db.session.commit()
        app.logger.info(f"started fl client for user: {username} with pid: {pid} ")
        print(f"started fl client for user: {username} with pid: {pid} ")
    
    except Exception as e:
        app.logger.info(f"Error starting fl client process for user: {username} with pid: {pid}")
        print(f"Error starting fl client process for user: {username} with pid: {pid}")

    session['username']=username
    return redirect(url_for('dashboard'))



# Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username = session['username'])
    else:
        return redirect(url_for('home'))

# Logout
@app.route("/logout")
def logout():
        session.pop('username',None)
        return redirect(url_for('home'))


# authorize for google
@app.route("/authorize/google")
def authorize_google():
    token = google.authorize_access_token()
    userinfo_endpoint = google.server_metadata['userinfo_endpoint']
    resp = google.get(userinfo_endpoint)
    user_info = resp.json()
    username = user_info['email']

    # Try to get browser-side location stored in session temporarily
    location = session.get("location", "Unknown")


    user = User.query.filter_by(username = username).first()
    if not user : 
        user = User(username = username, location = location)
        db.session.add(user)
        db.session.commit()
    
    session['username']=username
    session['oauth_token'] = token

    #start fl client process : 
    try: 
        pid = spawn_fl_client_process(username)
        user.fl_pid = pid
        db.session.commit()
        app.logger.info(f"started fl client for user: {username} with pid: {pid} ")
        print(f"started fl client for user: {username} with pid: {pid} ")
    
    except Exception as e:
        app.logger.info(f"Error starting fl client process for user: {username} with pid: {pid}")
        print(f"Error starting fl client process for user: {username} with pid: {pid}")

    return redirect(url_for('dashboard'))


# Login for google
@app.route("/login/google")
def login_google():
    try: 
        redirect_uri = url_for('authorize_google', _external= True)
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print("Hello check ")
        app.logger.error(f"Error during login : str{e}")
        return  "Error occured during login"   , 500 
    
    
        


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug = True)

