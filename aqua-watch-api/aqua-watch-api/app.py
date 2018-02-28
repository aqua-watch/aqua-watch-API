from flask import Flask, render_template, request, url_for, request, redirect, session, flash

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/your_water_quality')
def your_water_quality():
    return render_template('your_water_quality.html')

@app.route('/report_guide')
def report_guide():
    return render_template('report_guide.html')