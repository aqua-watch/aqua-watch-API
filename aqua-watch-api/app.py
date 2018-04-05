###########################################
## AquaWatch
##
##
###########################################

from flask import Flask, render_template, request
from flask_googlemaps import GoogleMaps, Map
from pymongo import MongoClient
from bson import json_util
import bson
import urllib.parse, urllib.request, json, pprint
from ast import literal_eval
import requests
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user

# initialize Flask
app = Flask(__name__)

# connect to Google Maps API
GoogleMaps(app, key='AIzaSyDC7vvV9T9pQBTeXIc-edWfP20tPO-dx0A')

# begin code used for login
login_manager = LoginManager()
login_manager.init_app(app)
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

class User(UserMixin):
    """ User class that represents an arbitrary user
    """
    first_name = None
    last_name = None

    def __init__(self, email):
        """ initialize class
            :param id: email
        """
        self.id = email

@login_manager.user_loader
def user_loader(email):
    """ to load user
    """
    user = User(email)
    return user

@app.route("/", methods=['GET'])
def index():
    """ main page
    """
    message = "Insert address above to see water quality"
    if (user):
        return render_template('index.html', message=message, fname=user.first_name, logged_in=1)
    else:
        return render_template('index.html', message=message, not_logged_in=1)

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

@app.route('/login', methods=['GET'])
def login():
    """ For user to provide email and password
    """
    return render_template('login.html')

@app.route('/login_attempt', methods=['POST'])
def login_attempt():
    """ To handle what happens after user provides email and password
    """
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
    """ For the user to provide personal data
    """
    return render_template('register.html')

@app.route('/register_attempt', methods=['POST'])
def register_attempt():
    """ To handle what happens whe user provides personal data
    """
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
    """ When action requires login
    """
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    """ Log out user and update user global
    """
    global user
    user = None
    logout_user()
    message = "Insert address above to see water quality"
    return render_template('index.html', message=message, not_logged_in=1)

@app.route('/map', methods=['GET'])
def map():
    if (user):
        return render_template('map.html', fname=user.first_name, logged_in=1)
    else:
        return render_template('map.html', not_logged_in=1)

@app.route('/sensors', methods=['POST'])
def extract_data():
    # tested with: [{"address": "111 Cummington Mall, Boston, MA 02215, USA", "latitude": 42.3490961,
    # "longitude": -71.1041893, "orp": "200 mV", "tds": "500 mg/L", "turbidity": "0.90 NTU", "ph": "7.5",
    # "conductivity": "500 uS/cm", "item-code": "99MQQR9M"}]

    # has to be a list of one or more javascript objects
    # for debugging purposes I empty the database before inserting every time this function is called
    # we only have limited storage space
    #data.remove({})
    
    cursor = data.find({})
    for document in cursor:
          print(document)

    
    # to get data as string
    response = request.get_data().decode("utf-8")
    # don't include .decode("utf-8") if data is json instead of raw
    # convert string to list of dictionaries
    docs = literal_eval(response)
    docs["address"] = ""
    docs["latitude"] = ""
    docs["longitude"] = ""
    #docs['item-code'] = ""
    # if data is json instead of raw uncomment line below and comment line above
    #response = json.loads(response)
    # convert list of dictionaries to list of javascript objects
    docs = json.dumps([docs])
    docs = json_util.loads(docs)
    
    #docs = bson.BSON.encode(docs)
    #print(docs)
    #print(type(docs))

    data.insert_many(docs)
    return "successful"

@app.route('/your_water_quality', methods=['GET'])
def your_water_quality():
    """ View function so far used for debugging
    """
    item_code = request.args.get("item-code")
    
    if(item_code == "" or item_code is None):   
        #generate the view so that they can add an item code
        return render_template('your_water_quality.html', has_item_code=0)
    item_code = item_code.strip()
    cursor = list(data.find({"product-code":item_code}))
    # to store results from cursor
    results = cursor[0]
    results = removekey(results, "_id")

    if results["address"] == "" or results["address"] == None:
        has_address = 0
    else:
        has_address = 1

    if (user):
        return render_template('your_water_quality.html', item_code=item_code, has_item_code=1,
         results=results, fname=user.first_name, logged_in=1, has_address= 0)
    else:
        return render_template('your_water_quality.html', item_code=item_code, has_item_code=1,
         results=results, not_logged_in=1, has_address= 0)

def removekey(d, key):
    r = dict(d)
    del r[key]
    return r


@app.route('/addAddress', methods=['POST'])
def add_address():
    try:
        address = request.form.get('address')
        code = request.form.get('code')

    except Exception as e:
        return json.dumps("incorrect request" + str(e))

    #format address and get lat and long
    response = requests.get("https://maps.googleapis.com/maps/api/geocode/json?address=" + urllib.parse.quote(address) + "&key=AIzaSyCHdvF13xoB27xgdUQzmylu5mW320-7mjc").content.decode("utf-8")
    response = literal_eval(response)

    if (response['status'] != 'OK'):
        return json.dumps("incorrect address")

    address = response['results'][0]['formatted_address']
    latitude = response['results'][0]['geometry']['location']['lat']
    longitude = response['results'][0]['geometry']['location']['lng']
    
    #update the collection
    data.update_one(
        {"code": code},
        {
        "$set": {
            "address":address,
            "latitude":latitude,
            "longitude":longitude
            }
        }
    )

    return "True"


@app.route('/report_guide', methods=['GET'])
def report_guide():
    if (user):
        return render_template('report_guide.html', fname=user.first_name, logged_in=1)
    else:
        return render_template('report_guide.html', not_logged_in=1)

if __name__ == "__main__":
    """ to run Flask locally
    """
    app.run(port=5000, debug=True)
