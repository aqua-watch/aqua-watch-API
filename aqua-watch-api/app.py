###########################################
##
## AquaWatch
##
###########################################

from flask import Flask, render_template, request, redirect, url_for, session
import flask
import os
import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from flask_googlemaps import GoogleMaps, Map
from pymongo import MongoClient
from bson import json_util
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from ast import literal_eval
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['profile','email']
API_SERVICE_NAME = 'plus'
API_VERSION = 'v1'

# initialize Flask
app = Flask(__name__)

# connect to Google Maps API
GoogleMaps(app, key='AIzaSyDC7vvV9T9pQBTeXIc-edWfP20tPO-dx0A')


"""
# begin code used for login
login_manager = LoginManager()
login_manager.init_app(app)
"""

app.config.update(
    SECRET_KEY = 'secret_xxx'
)
app.config['SESSION_TYPE'] = 'mongodb'

# connect to cloud Mongo database (MongoDB Atlas)
client = MongoClient("mongodb+srv://AquaWatch:I3WjjOcRO0tdLdAQ@aquawatch-pdkfe.mongodb.net/test")
# select database
db = client.leadmap
# select collections
# data collection
data = db.data
# users collection
users = db.users

# the user
user = None


"""
class User():

    def __init__(self, email, first_name, last_name, displayName):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.displayName = displayName

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False 

    def get_id(self):
        return self.email
"""

"""
class User(UserMixin):
    # User class that represents an arbitrary user
    first_name = None
    last_name = None
    email = None

    def __init__(self, email):
        # initialize class
        #    :param id: email

        self.email = email


@login_manager.user_loader
def user_loader(email):
    # to load user
    user = User(email)
    return user
"""

@app.route("/")
def index():
    # main page
    """
    message = "Insert address above to see water quality"
    if (user):
        return render_template('index.html', message=message, fname=user.first_name, logged_in=1)
    else:
        return render_template('index.html', message=message, not_logged_in=1)
    """
    message = "Insert address above to see water quality"

    if 'credentials' in flask.session:

        # Temporary fix for user_firstName not found error, but should be fixed with database
        # Load credentials from the session.
        credentials = google.oauth2.credentials.Credentials(
            **flask.session['credentials'])

        SERVICE = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials)

        user_resource = SERVICE.people()
        user_document = user_resource.get(userId='me').execute()
        user_firstName = user_document['name']['givenName']
        return render_template('index.html', message=message, logged_in=1, fname=user_firstName)
    else:
        return render_template('index.html', message=message, not_logged_in=1)



# User login with Google account
@app.route('/login', methods=['GET'])
def login():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    SERVICE = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    user_resource = SERVICE.people()
    user_document = user_resource.get(userId='me').execute()


    user_displayName = user_document['displayName']
    user_lastName = user_document['name']['familyName']
    user_firstName = user_document['name']['givenName']
    user_email = user_document['emails'][0]['value']
    user_image = user_document['image']['url']


    print user_displayName
    print user_firstName
    print user_lastName
    print user_email
    print user_image

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    flask.session['credentials'] = credentials_to_dict(credentials)

    message = "Insert address above to see water quality"

    return render_template('index.html', message=message, logged_in=1, fname=user_firstName)



# Getting authorization from user through Google
@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    flow.redirect_uri = flask.url_for('gCallback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true',
        prompt='select_account')

    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state


    return flask.redirect(authorization_url)



@app.route('/gCallback')
def gCallback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('gCallback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('login'))



# Logout from app, but remained logged in to Google
# Orginally '/clear' and def clear_credentials()
@app.route('/logout')
def logout():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    message = "Insert address above to see water quality"

    return render_template('index.html', message=message, not_logged_in=1)

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}




# This will disconnect a user's Google account from the app
@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return ('Credentials successfully revoked')
  else:
    return('An error occurred.')

"""
@app.route('/login_attempt', methods=['POST'])
def login_attempt():
    # To handle what happens after user provides email and password
    global user
    email = str(request.form.get('email'))
    password = str(request.form.get('password'))
    cursor = list(users.find({"email": email}))
    if (len(cursor) == 0):
        return render_template('login.html', message="You have to register first")
    elif (cursor[0]["password"] != password):
        return render_template('login.html', message="Wrong password")
    else: # cursor[0]["password"] == password
        message = "Insert address above to see water quality"
        fname = cursor[0]["first name"]
        lname = cursor[0]["last name"]
        user = user_loader(email)
        user.first_name = fname
        user.last_name = lname
        login_user(user)
        return render_template('index.html', message=message, fname=fname, logged_in=1)

@app.route('/register', methods=['GET'])
def register():
    # For the user to provide personal data
    return render_template('register.html')

@app.route('/register_attempt', methods=['POST'])
def register_attempt():
    # To handle what happens whe user provides personal data
    email = str(request.form.get('email'))
    password = str(request.form.get('password'))
    firstname = str(request.form.get('firstname'))
    lastname = str(request.form.get('lastname'))
    cursor = list(users.find({"email": email}))
    if (len(cursor) == 0):
        dicts = [{"email": email, "password": password, "first name": firstname, "last name": lastname}]
        docs = json.dumps(dicts)
        docs = json_util.loads(docs)
        users.insert_many(docs)
        return render_template('register.html', message="Registration successful!")
    else:
        return render_template('register.html', message="Already registered!")

@login_manager.unauthorized_handler
def unauthorized_handler():
    # When action requires login
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    # Log out user and update user global
    global user
    user = None
    logout_user()
    message = "Insert address above to see water quality"
    return render_template('index.html', message=message, not_logged_in=1)
"""
@app.route('/mapview', methods=['POST'])
def mapview():
    """ View function to display results from an address in the database
        Makes get request to Google Maps Geocode API ro obtain formatted address, latitude and longitude
    """
    try:
        # obtain input from user
        address = request.form.get('search')
        # make a get http request to geocode api
        response = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + urllib.parse.quote(address) + "&key=AIzaSyCHdvF13xoB27xgdUQzmylu5mW320-7mjc").content.decode("utf-8")
        # convert string to list of dictionaries
        response = literal_eval(response)
        # handle invalid address
        if (response['status'] != 'OK'):
            message = "Invalid address. Try again."
            if (user):
                return render_template('index.html', location=address, message=message, fname=user.first_name, logged_in=1)
            else:
                return render_template('index.html', location=address, message=message, not_logged_in=1)
        # obtain values from response
        address = response['results'][0]['formatted_address']
        latitude = response['results'][0]['geometry']['location']['lat']
        longitude = response['results'][0]['geometry']['location']['lng']
        # query
        cursor = list(data.find({"address": address}))
        # results from query
        results = []
        for i in range(len(cursor)):
            current = cursor[i]
            results += [[current['address'], current['latitude'], current['longitude'], current['orp'], current['tds'],
                         current['turbidity'], current['ph'], current['conductivity']]]
        if (len(results) == 0):
            message = "No data for this location yet"
            if (user):
                return render_template('index.html', location=address, message=message, fname=user.first_name, logged_in=1)
            else:
                return render_template('index.html', location=address, message=message, not_logged_in=1)
        else:
            # create map
            my_map = Map(identifier="view-side", lat=latitude, lng=longitude, style="height:600px;width:900px;margin:0px;", zoom=16,
                         markers=[(latitude, longitude, None, 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png')])
            if (user):
                return render_template('mapview.html', location=address, results=results, mymap=my_map, fname=user.first_name, logged_in=1)
            else:
                return render_template('mapview.html', location=address, results=results, mymap=my_map, not_logged_in=1)
    except:
        message = "Invalid address. Try again."
        if (user):
            return render_template('index.html', message=message, fname=user.first_name, logged_in=1)
        else:
            return render_template('index.html', message=message, not_logged_in=1)


@app.route('/map', methods=['GET'])
def map():
    if (user):
        return render_template('map.html', fname=user.first_name, logged_in=1)
    else:
        return render_template('map.html', not_logged_in=1)

@app.route('/sensors', methods=['POST'])
def extract_data():
    # tested with: [{"address": "111 Cummington Mall, Boston, MA 02215, USA", "latitude": 42.3490961, "longitude": -71.1041893, "orp": "200 mV", "tds": "500 mg/L", "turbidity": "0.90 NTU", "ph": "7.5", "conductivity": "500 uS/cm"}]
    # has to be a list of one or more javascript objects
    # for debugging purposes I empty the database before inserting every time this function is called
    # we only have limited storage space
    data.remove({})
    # to get data as string
    response = request.get_data().decode("utf-8")
    # don't include .decode("utf-8") if data is json instead of raw
    # convert string to list of dictionaries
    response = literal_eval(response)
    # if data is json instead of raw uncomment line below and comment line above
    # response = json.loads(response.read())
    # convert list of dictionaries to list of javascript objects
    response = json.dumps(response)
    # convert list of javascript objects to MongoDB documents
    docs = json_util.loads(response)
    # insert many documents into cloud database
    data.insert_many(docs)
    # to test for correctness look at your_water_quality view function and your_water_quality.html
    return "successful"

@app.route('/your_water_quality', methods=['GET'])
def your_water_quality():
    """ View function so far used for debugging
    """
    # simple query
    cursor = list(data.find({"address": "111 Cummington Mall, Boston, MA 02215, USA"}))
    # to store results from cursor
    results = []
    for i in range(len(cursor)):
        current = cursor[i]
        results += [[current['address'], current['latitude'], current['longitude'], current['orp'], current['tds'], current['turbidity'], current['ph'], current['conductivity']]]
    if (user):
        return render_template('your_water_quality.html', results=results, fname=user.first_name, logged_in=1)
    else:
        return render_template('your_water_quality.html', results=results, not_logged_in=1)

@app.route('/report_guide', methods=['GET'])
def report_guide():
    if (user):
        return render_template('report_guide.html', fname=user.first_name, logged_in=1)
    else:
        return render_template('report_guide.html', not_logged_in=1)

if __name__ == "__main__":
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # To run Flask locally
    app.run(port=5000, debug=True)
