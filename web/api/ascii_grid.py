from flask import Blueprint, request, jsonify
import logging
import sys
import netCDF4
import numpy as np
import os
from flask import Flask, request, redirect, url_for
from flask import current_app as app
from werkzeug.utils import secure_filename


bp = Blueprint('ascii_grid', __name__)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = set(['txt', 'asc'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/import/ascii-grid/upload/<string:timeseries_id>", methods=['POST'])
def upload_file(timeseries_id):
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.read()
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return "OK", 200
