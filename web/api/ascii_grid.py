import logging
import os
from datetime import datetime
from collections import namedtuple
from profilehooks import profile
from rq import Queue
from rq.decorators import job
from redis import Redis
from web import worker_settings as conf
from web.api import transcode_ascii_to_netcdf

import netCDF4
import numpy as np
from flask import Blueprint, request, jsonify
from netCDF4 import date2num
from werkzeug.utils import secure_filename
from secrets import token_urlsafe

bp = Blueprint('ascii_grid', __name__)
logger = logging.getLogger(__name__)
w_logger = logging.getLogger('rq.worker')

NETCDF_FILE_FORMAT = 'NETCDF4'  # 'NETCDF4_CLASSIC
ALLOWED_EXTENSIONS = {'txt', 'asc'}
DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
ADAPTER_GRID = 'http://adapter-grid.default.svc.cluster.local'
ADAPTER_STATUS = 'http://adapter-status.default.svc.cluster.local'
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/data')
# Data Types
Metadata = namedtuple('Metadata', 'ncols nrows xllcorner yllcorner cellsize NODATA_value')

redis_conn = Redis(host=conf.REDIS_HOST, port=conf.REDIS_PORT, db=conf.REDIS_DB, password=conf.REDIS_PASSWORD)


@job(os.getenv('HOSTNAME', 'default'), connection=redis_conn, timeout=15)
def transcode_ascii_netcdf(timeseries_id, files, request_id):
    w_logger.info(f'processing timeseries_id:{timeseries_id}, request_id:{request_id}')
    ncfile = None
    for i, item in enumerate(files):
        file, timestamp = item
        if not ncfile:
            meta = transcode_ascii_to_netcdf.get_ascii_metadata(file)
            w_logger.info(f"{file} -> {meta}")
            ncfile = ncfile or transcode_ascii_to_netcdf.get_netcdf_file(timeseries_id, meta, request_id)
        data = np.loadtxt(file, skiprows=6)
        transcode_ascii_to_netcdf.update_netcdf_file(ncfile, timestamp, data)
    if ncfile is not None:
        transcode_ascii_to_netcdf.close_ncfile(ncfile)
    # Send data to adapter-grid
    import requests
    with open(f'/tmp/grid_data_{timeseries_id}_{request_id}.nc', 'rb') as f:
        grid_res = requests.post(f'{ADAPTER_GRID}/timeseries/{timeseries_id}', data=f)
        grid_res.raise_for_status()
    status_res = requests.post(f'{ADAPTER_STATUS}/{timeseries_id}', data={
        'requestId': request_id,
        'service': 'Import',
        'type': 'Grid'
    })
    status_res.raise_for_status()
    w_logger.info(f"updated status requestId: {request_id} @ timeseries: {timeseries_id}")
    return True


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/import/ascii-grid/upload/<string:timeseries_id>", methods=['POST'])
# @profile(immediate=True)
def upload_file(timeseries_id):
    assert timeseries_id, 'Timeseries ID should be provided.'
    # check if the post request has the file part
    files_dict = request.files.to_dict()
    if len(files_dict.items()) < 1:
        return 'No file parts found.', 400
    # Verify all the files before processing them
    try:
        for key, value in files_dict.items():
            file = request.files.get(key)
            assert file.filename, f'No selected file for: {key}'
            assert file and allowed_file(file.filename), f'Invalid file: {file.filename}'
            datetime.strptime(key, DATE_TIME_FORMAT)
    except ValueError as ex:
        return f'Timestamp should be in {DATE_TIME_FORMAT}. Error: {str(ex)}', 400
    except Exception as err:
        return 'Error' + str(err), 400
    # No need the verification, but for the safety ;)
    saved_files = []
    request_id = token_urlsafe(16)
    logger.info(f"Processing files for timeseries_id: {timeseries_id}, request_id: {request_id}")
    for key, value in files_dict.items():
        file = request.files.get(key)
        timestamp = datetime.strptime(key, DATE_TIME_FORMAT)
        # if user does not select file, browser also submit a empty part without filename
        if file.filename == '':
            return 'No selected file', 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # f = file.read()
            # meta, data = get_ascii_data(f.decode('utf-8'))
            # ncfile = ncfile or get_netcdf_file(timeseries_id, meta)
            # update_netcdf_file(ncfile, timestamp, data)
            # create_netcdf_file_by_stream(timeseries_id, timestamp, f.decode('utf-8'))
            # TODO: Save file size if greater than 500KB and then process
            file.save(os.path.join(UPLOAD_FOLDER, f'{timeseries_id}-{filename}'))
            saved_files.append([os.path.join(UPLOAD_FOLDER, f'{timeseries_id}-{filename}'), timestamp])
    transcode_ascii_netcdf.delay(timeseries_id, saved_files, request_id)

    return jsonify(requestId=request_id), 200
