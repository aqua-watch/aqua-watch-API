###########################################
## AquaWatch
##
##
###########################################

from flask import Flask, render_template
from pymongo import MongoClient
from bson import json_util
import sys, urllib.request, json, pprint

# initialize Flask
app = Flask(__name__)

# connect to cloud Mongo database (MongoDB Atlas)
client = MongoClient("mongodb+srv://AquaWatch:I3WjjOcRO0tdLdAQ@aquawatch-pdkfe.mongodb.net/test")
# select database
db = client.leadmap
# select collection
data = db.data

@app.route("/", methods=['GET', 'POST'])
def index():
    """ main page
    """
    return render_template('index.html')

@app.route('/map', methods=['GET', 'POST'])
def map():
    return render_template('map.html')

@app.route('/your_water_quality', methods=['GET', 'POST'])
def your_water_quality():
    # for purposes of this example I empty the database before inserting every time localhost:5000 is loaded
    data.remove({})
    # open .JSON file. In this case the file is opened locally
    response = urllib.request.urlopen("file:///C:/Users/Victor/Documents/Boston%20University/Semester%206%20-%20Spring%202018/CS%20591%20M1/AquaWatch/aqua-watch-API-frontend/aqua-watch-api/data.json")
    # convert json to list of python dictionaries
    dict_list = json.loads(response.read()) # we can change these dictionaries to create our actual data to be stored in the database
    # convert list of python dictionaries to json
    docs = json.dumps(dict_list)
    # convert list of JavaScript objects (.JSON file) into Mongo documents
    # docs = json_util.loads(response.read()) --> if doing directly from first file read
    docs = json_util.loads(docs) # --> if we do something in the middle (changing the python dictionaries)
    # insert all documents
    data.insert_many(docs)
    # simple query
    cursor = list(data.find({"address.street": "111 Cummington Mall"}))
    # to store results from cursor
    results = []
    for i in range(len(cursor)):
        current = cursor[i]
        results += [[current['address']['street'] + ", " + current['address']['zipcode'] + ", " + current['address']['city'] + ", " + \
                     current['address']['state'], current['orp'], current['tds'], current['turbidity'], current['ph'], current['conductivity']]]
    return render_template('your_water_quality.html', results=results)

@app.route('/report_guide', methods=['GET', 'POST'])
def report_guide():
    return render_template('report_guide.html')

if __name__ == "__main__":
    """ to run Flask locally
    """
    app.run(port=5000, debug=True)
