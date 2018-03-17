###########################################
## AquaWatch
##
##
###########################################

from flask import Flask, render_template, request
from pymongo import MongoClient
from bson import json_util
import sys, urllib.request, json, pprint
from ast import literal_eval

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

@app.route('/sensors', methods=['POST'])
def getData():
    # for debugging purposes I empty the database before inserting every time this function is called
    # we only have limited storage space
    data.remove({})
    # to get data
    response = request.get_data().decode("utf-8")
    # don't include .decode("utf-8") if data is json instead of raw
    # convert string to dictionary
    response = [literal_eval(response)]
    # if data is json instead of raw uncomment line below and comment line above
    # response = json.loads(response.read())
    pprint.pprint(response)
    # convert dictionary to javascript object
    response = json.dumps(response)
    # convert javascript object to MongoDB document
    docs = json_util.loads(response)
    # insert into database
    data.insert_many(docs)
    # to test for correctness look at your_water_quality view function and your_water_quality.html
    return "successful"

@app.route('/your_water_quality', methods=['GET', 'POST'])
def your_water_quality():
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
