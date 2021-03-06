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
import urllib.parse, urllib.request
import json
from ast import literal_eval

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['profile', 'email']
API_SERVICE_NAME = 'plus'
API_VERSION = 'v1'

# initialize Flask
app = Flask(__name__)

# connect to Google Maps API
GoogleMaps(app, key='AIzaSyDC7vvV9T9pQBTeXIc-edWfP20tPO-dx0A')

app.config.update(
    SECRET_KEY='secret_xxx'
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
# testmapping collection
testmapping = db.testmapping

# units
units = {"orp": " mV", "tds": " mg/L", "turbidity": " NTU", "conductivity": " uS/cm"}
# sensor globals
orp, tds, turbidity, ph, conductivity = 3, 4, 5, 6, 7
# marker globals
green_marker = 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
yellow_marker = 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png'
red_marker = 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'

@app.route("/")
def index():
    # main page
    if 'user' not in flask.session:
        return render_template('index.html', not_logged_in=1)
    else:
        return render_template('index.html', logged_in=1, fname=flask.session['user']['first_name'])

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

    email = user_document['emails'][0]['value']

    if users.find({'_id': email }).count() == 0:
        lastName = user_document['name']['familyName']
        firstName = user_document['name']['givenName']
        users.insert_one(
            {
            '_id': email,
            'first_name': firstName,
            'last_name': lastName,
            'products': [],
            }
        )
    user = users.find_one({'_id': email })

    flask.session['user'] = user

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    flask.session['credentials'] = credentials_to_dict(credentials)

    return render_template('index.html', logged_in=1, fname=flask.session['user']['first_name'])

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
        del flask.session['user']

    return render_template('index.html', not_logged_in=1)

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
        return ('You need to authorize before revoking credentials.')

    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        return ('Credentials successfully revoked')
    else:
        return ('An error occurred.')


@app.route('/mapview', methods=['POST'])
def mapview():
    """ View function to display results from an address in the database
        Makes get request to Google Maps Geocode API ro obtain formatted address, latitude and longitude
    """
    try:
        # obtain input from user
        address = request.form.get('search')
        # make a get http request to geocode api
        response = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + urllib.parse.quote(
            address) + "&key=AIzaSyD96hi-erVEjBU2037BUp7gbRkP8xvdzq8").content.decode("utf-8")
        # convert string to list of dictionaries
        response = literal_eval(response)
        # handle invalid address
        if (response['status'] != 'OK'):
            message = "Invalid address. Try again."
            if 'user' not in flask.session:
                return render_template('index.html', location=address, message=message, not_logged_in=1)
            else:
                return render_template('index.html', location=address, message=message, fname=flask.session['user']['first_name'],
                                       logged_in=1)
        # obtain values from response
        address = response['results'][0]['formatted_address']
        latitude = response['results'][0]['geometry']['location']['lat']
        longitude = response['results'][0]['geometry']['location']['lng']
        lat_range = [latitude - 0.005, latitude + 0.005]
        lon_range = [longitude - 0.05, longitude + 0.05]
        cursor = list(data.find({'$and': [{"latitude": {'$gte': lat_range[0]}}, {"latitude": {'$lte': lat_range[1]}},
                                         {"longitude": {'$gte': lon_range[0]}}, {"longitude": {'$lte': lon_range[1]}}]}))
        # query
        # cursor = list(testmapping.find({"address": address}))
        # results from query
        results = []
        zero_results = True
        for i in range(len(cursor)):
            current = cursor[i]
            results += [[current['address'], current['latitude'], current['longitude'], current['orp'], current['tds'],
                         current['turbidity'], current['ph'], current['conductivity']]]
            if (current['address'] == address):
                zero_results = False
        if (len(results) == 0):
            message = "No data for this location or its surroundings yet"
            if 'user' not in flask.session:
                return render_template('index.html', location=address, message=message, not_logged_in=1)
            else:
                return render_template('index.html', location=address, message=message, fname=flask.session['user']['first_name'],
                                       logged_in=1)
        elif (zero_results):
            message = "No data for this location yet, but there is some data for its surroundings"
            map_dict = {}
            # calculate the average for each sensor
            if (len(results) > 1):
                for i in range(len(results)):
                    if (results[i][0] not in map_dict):
                        map_dict[results[i][0]] = results[i] + [1]
                    else:
                        map_dict[results[i][0]][orp] += results[i][orp]
                        map_dict[results[i][0]][tds] += results[i][tds]
                        map_dict[results[i][0]][turbidity] += results[i][turbidity]
                        map_dict[results[i][0]][ph] += results[i][ph]
                        map_dict[results[i][0]][conductivity] += results[i][conductivity]
                        map_dict[results[i][0]][8] += 1
                for key in map_dict:
                    map_dict[key][orp] /= map_dict[key][8]
                    map_dict[key][tds] /= map_dict[key][8]
                    map_dict[key][turbidity] /= map_dict[key][8]
                    map_dict[key][ph] /= map_dict[key][8]
                    map_dict[key][conductivity] /= map_dict[key][8]
            # create markers
            data_marker_tuples = []
            for key in map_dict:
                data_marker_tuples += [map_dict[key][:-1]]
            marker_tuples = []
            for m in data_marker_tuples:
                marker_tuples += [
                    (m[1], m[2], None, determine_marker(m[orp], m[tds], m[turbidity], m[ph], m[conductivity]))]
            # create map
            my_map = Map(identifier="view-side", lat=latitude, lng=longitude,
                         style="height:600px;width:900px;margin:0px;", zoom=16,
                         markers=marker_tuples)
            if 'user' not in flask.session:
                return render_template('mapview.html', location=address, message=message, mymap=my_map, not_logged_in=1)
            else:
                return render_template('mapview.html', location=address, message=message, mymap=my_map,
                                       fname=flask.session['user']['first_name'], logged_in=1)
        else:
            map_dict = {}
            # calculate the average for each sensor
            if (len(results) > 1):
                for i in range(len(results)):
                    if (results[i][0] not in map_dict):
                        map_dict[results[i][0]] = results[i] + [1]
                    else:
                        map_dict[results[i][0]][orp] += results[i][orp]
                        map_dict[results[i][0]][tds] += results[i][tds]
                        map_dict[results[i][0]][turbidity] += results[i][turbidity]
                        map_dict[results[i][0]][ph] += results[i][ph]
                        map_dict[results[i][0]][conductivity] += results[i][conductivity]
                        map_dict[results[i][0]][8] += 1
                for key in map_dict:
                    map_dict[key][orp] /= map_dict[key][8]
                    map_dict[key][tds] /= map_dict[key][8]
                    map_dict[key][turbidity] /= map_dict[key][8]
                    map_dict[key][ph] /= map_dict[key][8]
                    map_dict[key][conductivity] /= map_dict[key][8]
            results = [map_dict[address][:-1]]
            res_img = determine_marker(results[0][orp], results[0][tds], results[0][turbidity], results[0][ph],
                                       results[0][conductivity])
            # add units to results displayed in html page
            results[0][orp] = str(results[0][orp]) + units["orp"]
            results[0][tds] = str(results[0][tds]) + units["tds"]
            results[0][turbidity] = str(results[0][turbidity]) + units["turbidity"]
            results[0][conductivity] = str(results[0][conductivity]) + units["conductivity"]
            # create markers
            data_marker_tuples = []
            for key in map_dict:
                data_marker_tuples += [map_dict[key][:-1]]
            marker_tuples = []
            for m in data_marker_tuples:
                marker_tuples += [(m[1], m[2], None, determine_marker(m[orp], m[tds], m[turbidity], m[ph], m[conductivity]))]
            # create map
            my_map = Map(identifier="view-side", lat=latitude, lng=longitude,
                         style="height:600px;width:900px;margin:0px;", zoom=16,
                         markers=marker_tuples)
            if 'user' not in flask.session:
                return render_template('mapview.html', location=address, results=results, res_img=res_img, mymap=my_map,
                                       not_logged_in=1)
            else:
                return render_template('mapview.html', location=address, results=results, res_img=res_img, mymap=my_map,
                                       fname=flask.session['user']['first_name'], logged_in=1)
    except:
        message = "Invalid address. Try again."
        if 'user' not in flask.session:
            return render_template('index.html', message=message, not_logged_in=1)
        else:
            return render_template('index.html', message=message, fname=flask.session['user']['first_name'], logged_in=1)

def determine_marker(s_orp, s_tds, s_tur, s_ph, s_con):
    """ to determine the color of the marker
    """
    if (s_orp >= 200 and s_orp <= 600 and s_tds <= 300 and s_tur <= 200 and s_ph >= 6.8 and s_ph <= 7.2 and s_con <= 4):
        return green_marker
    elif (s_orp >= 0 and s_orp <= 750 and s_tds <= 600 and s_tur <= 300 and s_ph >= 6.5 and s_ph <= 7.5 and s_con <= 6):
        return yellow_marker
    else:
        return red_marker


@app.route('/sensors', methods=['POST'])
def extract_data():
    # has to be a list of one or more javascript objects
    # for debugging purposes I empty the database before inserting every time this function is called
    # we only have limited storage space
    data.remove({})

    # to get data as string
    response = request.get_data().decode("utf-8")
    # don't include .decode("utf-8") if data is json instead of raw
    # convert string to list of dictionaries
    docs = literal_eval(response)
    # if data is json instead of raw uncomment line below and comment line above
    # response = json.loads(response)
    # docs["address"] = ""
    # docs["latitude"] = ""
    # docs["longitude"] = ""
    # docs["product-code"] = ""
    # convert list of dictionaries to list of javascript objects
    docs = json.dumps(docs)
    # convert list of javascript objects to MongoDB documents
    docs = json_util.loads(docs)
    # insert many documents into cloud database
    data.insert_many(docs)
    return "successful"

@app.route('/your_water_quality', methods=['GET'])
def your_water_quality():
    """ View function so far used for debugging
    """
    if 'user' not in flask.session:
        return render_template('your_water_quality.html', not_logged_in=1)

    else:
        item_code = request.args.get("item-code")

        if (item_code == "" or item_code is None):
            # generate the view so that they can add an item code
            return render_template('your_water_quality.html', no_item_code=1, fname=flask.session['user']['first_name'], logged_in=1)

        item_code = item_code.strip()
        cursor = list(data.find({"product-code": item_code}))
        # to store results from cursor
        # results = removekey(results, "_id")
        results = []
        for i in range(len(cursor)):
            current = cursor[i]
            results += [[current['address'], current['latitude'], current['longitude'], current['orp'], current['tds'],
                         current['turbidity'], current['ph'], current['conductivity']]]

        if (len(results) == 0):
            message = "No data for this product code yet"
            return render_template('your_water_quality.html', no_item_code=1, fname=flask.session['user']['first_name'],
                                   logged_in=1, message=message)

        if (len(results) > 1):
            for i in range(len(results)):
                if (results[i][0] == ""):
                    results[0][0] = ""
                    results[0][1] = ""
                    results[0][2] = ""
                    break
            results[0] = results[0] + [1]
            for i in range(1, len(results)):
                results[0][orp] += results[i][orp]
                results[0][tds] += results[i][tds]
                results[0][turbidity] += results[i][turbidity]
                results[0][ph] += results[i][ph]
                results[0][conductivity] += results[i][conductivity]
                results[0][8] += 1
            results = [results[0]]
            results[0][orp] /= results[0][8]
            results[0][tds] /= results[0][8]
            results[0][turbidity] /= results[0][8]
            results[0][ph] /= results[0][8]
            results[0][conductivity] /= results[0][8]
            results = [results[0][:-1]]
        res_img = determine_marker(results[0][orp], results[0][tds], results[0][turbidity], results[0][ph],
                                   results[0][conductivity])
        # add units to results displayed in html page
        results[0][orp] = str(results[0][orp]) + units["orp"]
        results[0][tds] = str(results[0][tds]) + units["tds"]
        results[0][turbidity] = str(results[0][turbidity]) + units["turbidity"]
        results[0][conductivity] = str(results[0][conductivity]) + units["conductivity"]

        if results[0][0] == "" or results[0][0] == None:
            return render_template('your_water_quality.html', fname=flask.session['user']['first_name'], item_code=item_code,
                                   has_item_code=1, results=results, res_img=res_img, logged_in=1, no_address=1)
        else:
            return render_template('your_water_quality.html', fname=flask.session['user']['first_name'], item_code=item_code,
                                   has_item_code=1, results=results, res_img=res_img, logged_in=1, has_address=1)

def removekey(d, key):
    r = dict(d)
    del r[key]
    return r

@app.route('/addAddress', methods=['POST'])
def add_address():
    try:
        address = request.form.get('address')
        code = request.form.get('item_code')

    except Exception as e:
        return json.dumps("incorrect request" + str(e))

    # format address and get lat and long
    response = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + urllib.parse.quote(
        address) + "&key=AIzaSyCHdvF13xoB27xgdUQzmylu5mW320-7mjc").content.decode("utf-8")
    response = literal_eval(response)

    if (response['status'] != 'OK'):
        return json.dumps("incorrect address")

    address = response['results'][0]['formatted_address']
    latitude = response['results'][0]['geometry']['location']['lat']
    longitude = response['results'][0]['geometry']['location']['lng']

    # update the collection
    testmapping.update_many(
        {"product-code": code},
        {"$set": {
            "address": address,
            "latitude": latitude,
            "longitude": longitude
            }
        }
    )

    return "Perfect"

@app.route('/report_guide', methods=['GET'])
def report_guide():
    if 'user' not in flask.session:
        return render_template('report_guide.html', not_logged_in=1)
    else:
        return render_template('report_guide.html', fname=flask.session['user']['first_name'], logged_in=1)

if __name__ == "__main__":
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # To run Flask locally
    app.run(port=5000, debug=True)
