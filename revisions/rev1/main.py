#!/usr/bin/python

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import time
from flask import Flask, flash, render_template, request, send_file
import os
from werkzeug.utils import secure_filename

matplotlib.style.use('ggplot')
app = Flask(__name__, static_url_path='/static')
app.secret_key = 'some_secret'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(APP_ROOT, 'static/')
ALLOWED_EXTENSIONS = set(['txt'])
app.config['UPLOAD_FOLDER'] = TARGET
chart = None


@app.route("/")
def start():
    return render_template('index.pt')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

    flash('Program started')
    flash("=============")
    average_connectivity(file)
    connectivity_chart(file)
    flash("Program Complete")
    file.close()
    return render_template('upload.html')


def average_connectivity(file):
    raw_data = pd.read_csv(TARGET + file.filename, sep='\t', comment='#', names=["Source", "Destination"])
    grouped_counted_data = raw_data.groupby(by="Source").count()
    mean_connectivity = grouped_counted_data['Destination'].mean()

    flash("Average number of connections:")
    flash(mean_connectivity)
    flash("=============")


def connectivity_chart(file):
    raw_data = pd.read_csv(TARGET + file.filename, sep='\t', comment='#', names=["Source", "Destination"])
    counted_sorted_data = raw_data.groupby(by="Source").count().sort_values(by="Destination", ascending=False).rename(columns={'Destination' : 'Count'})
    counted_sorted_data.plot.hist(bins=20).set_xlabel(file.filename + " Analysis")

    plt.savefig(TARGET + "chart.svg")
    #chart_path = TARGET + "chart.png?t=" + str(time.time())[:9]
    #os.rename(TARGET + "chart.png", chart_path)

    flash("Sources with most connections:")
    flash(str(counted_sorted_data.iloc[0]))
    flash("=============")

    #global chart
    #chart = chart_path


#@app.route("/get_image", methods=['GET', 'POST'])
#def get_image():
#    return send_file(chart, mimetype='image/png')


if __name__ == '__main__':
    app.run()
