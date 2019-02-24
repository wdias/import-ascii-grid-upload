import logging
import os
from datetime import datetime

import netCDF4
import numpy as np
from flask import Blueprint
from flask import request
from netCDF4 import date2num
from werkzeug.utils import secure_filename

bp = Blueprint('ascii_grid', __name__)
logger = logging.getLogger(__name__)

NETCDF_FILE_FORMAT = 'NETCDF4'  # 'NETCDF4_CLASSIC
ALLOWED_EXTENSIONS = set(['txt', 'asc'])
DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
ADAPTER_GRID = 'http://adapter-grid.default.svc.cluster.local'


def create_netcdf_file_by_stream(timeseries_id, timestamp: datetime, f):
    f = f.split('\n')
    ncols = int(f.pop(0).split('\t')[1])
    nrows = int(f.pop(0).split('\t')[1])
    xllcorner = float(f.pop(0).split('\t')[1])
    yllcorner = float(f.pop(0).split('\t')[1])
    cellsize = float(f.pop(0).split('\t')[1])
    NODATA_value = int(f.pop(0).split('\t')[1])
    logger.info(f'Meta: {ncols}, {nrows}, {xllcorner}, {yllcorner}, {cellsize}, {NODATA_value}')

    data = np.empty(shape=(nrows, ncols))
    line_no = 0
    for line in f:
        if len(line):
            data[line_no, :] = [float(i) for i in line.split(' ')]
            line_no += 1

    if os.path.isfile(f'/tmp/grid_data_{timeseries_id}.nc'):
        ncfile = netCDF4.Dataset(f'/tmp/grid_data_{timeseries_id}.nc', mode='r+', format=NETCDF_FILE_FORMAT)
    else:
        logger.info('Initializing NetCDF file')
        ncfile = netCDF4.Dataset(f'/tmp/grid_data_{timeseries_id}.nc', mode='w', format=NETCDF_FILE_FORMAT)
    # logger.info(ncfile)
    if 'latitude' not in ncfile.dimensions or 'longitude' not in ncfile.dimensions or 'timestamp' not in ncfile.dimensions:
        lat_dim = ncfile.createDimension('latitude', nrows)  # Y axis
        lon_dim = ncfile.createDimension('longitude', ncols)  # X axis
        time_dim = ncfile.createDimension('timestamp', None)
        # logger.info("Dimentions: %s", ncfile.dimensions.items())

        ncfile.moduleId = 'HEC-HMS'
        ncfile.valueType = 'Scalar'
        ncfile.parameterId = 'O.Precipitation'
        ncfile.locationId = 'wdias_hanwella'
        ncfile.timeseriesType = 'External_Historical'
        ncfile.timeStepId = 'each_hour'

        lat = ncfile.createVariable('latitude', np.float32, ('latitude',))
        lat.units = "Kandawala"
        # logger.info("latitude: %s", lat)
        lon = ncfile.createVariable('longitude', np.float32, ('longitude',))
        lon.units = "Kandawala"
        time = ncfile.createVariable('timestamp', np.float64, ('timestamp',))
        time.units = "days since 1970-01-01 00:00"
        val = ncfile.createVariable('value', np.float32, ('timestamp', 'latitude', 'longitude',))
        val.units = 'O.Precipitation'
        # Write lat and lon
        lat[:] = (yllcorner + cellsize * nrows) - cellsize * np.arange(nrows)
        lon[:] = xllcorner + cellsize * np.arange(ncols)

    # Write data
    time = ncfile.variables['timestamp']
    val = ncfile.variables['value']

    dates = [timestamp]
    # logger.info('Date: %s', dates)
    times = date2num(dates, time.units)
    # logger.info('Times: %s %s', times, time.units)  # numeric values

    len_time = val.shape[0]
    # val[len_time, :, :] = data
    val[times[0], :, :] = data
    logger.info('Time: %s', time[:])
    # time[len_time] = times[0]
    time[:] = np.append(time, times)

    # first logger.info() the Dataset object to see what we've got
    logger.info(ncfile)
    # close the Dataset.
    ncfile.close()
    logger.info('Dataset is closed!')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/import/ascii-grid/upload/<string:timeseries_id>", methods=['POST'])
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
    for key, value in files_dict.items():
        logger.info("Processing ...")
        file = request.files.get(key)
        timestamp = datetime.strptime(key, DATE_TIME_FORMAT)
        # if user does not select file, browser also submit a empty part without filename
        if file.filename == '':
            return 'No selected file', 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            f = file.read()
            create_netcdf_file_by_stream(timeseries_id, timestamp, f.decode('utf-8'))
            # TODO: Save file size if greater than 500KB and then process
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    with open(f'/tmp/grid_data_{timeseries_id}.nc', 'rb') as f:
        import requests
        requests.post(f'{ADAPTER_GRID}/timeseries/{timeseries_id}', data=f)
    return "OK", 200
