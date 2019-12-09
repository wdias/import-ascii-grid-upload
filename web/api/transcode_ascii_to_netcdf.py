import logging
import os
from datetime import datetime
from collections import namedtuple
from profilehooks import profile

import netCDF4
import numpy as np
from flask import Blueprint, request, jsonify
from netCDF4 import date2num
from werkzeug.utils import secure_filename
from secrets import token_urlsafe

bp = Blueprint('ascii_grid', __name__)
logger = logging.getLogger('rq.worker')

NETCDF_FILE_FORMAT = 'NETCDF4'  # 'NETCDF4_CLASSIC
ALLOWED_EXTENSIONS = {'txt', 'asc'}
DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
ADAPTER_GRID = 'http://adapter-grid.default.svc.cluster.local'
ADAPTER_STATUS = 'http://adapter-status.default.svc.cluster.local'
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/data')
# Data Types
Metadata = namedtuple('Metadata', 'ncols nrows xllcorner yllcorner cellsize NODATA_value')


# @profile(immediate=True)
def get_netcdf_file(timeseries_id, meta: Metadata, request_id):
    if os.path.isfile(f'/tmp/grid_data_{timeseries_id}_{request_id}.nc'):
        ncfile = netCDF4.Dataset(f'/tmp/grid_data_{timeseries_id}_{request_id}.nc', mode='r+', format=NETCDF_FILE_FORMAT)
    else:
        logger.info('Initializing NetCDF file')
        ncfile = netCDF4.Dataset(f'/tmp/grid_data_{timeseries_id}_{request_id}.nc', mode='w', format=NETCDF_FILE_FORMAT)
    # logger.info(ncfile)
    if 'latitude' not in ncfile.dimensions or 'longitude' not in ncfile.dimensions or 'timestamp' not in ncfile.dimensions:
        lat_dim = ncfile.createDimension('latitude', meta.nrows)  # Y axis
        lon_dim = ncfile.createDimension('longitude', meta.ncols)  # X axis
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
        # NOTE: There's an issue with storing larger value with collective mode. In order to reduce the size, decrease the date gap
        # time.units = "days since 1970-01-01 00:00"
        time.units = "days since 2015-01-01 00:00"
        val = ncfile.createVariable('value', np.float32, ('timestamp', 'latitude', 'longitude',))
        val.units = 'O.Precipitation'
        # Write lat and lon
        lat[:] = (meta.yllcorner + meta.cellsize * meta.nrows) - meta.cellsize * np.arange(meta.nrows)
        lon[:] = meta.xllcorner + meta.cellsize * np.arange(meta.ncols)
        ncfile.sync()
    return ncfile


# @profile(immediate=True)
def update_netcdf_file(ncfile, timestamp: datetime, data):
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
    ncfile.sync()


def close_ncfile(ncfile):
    # first logger.info() the Dataset object to see what we've got
    logger.info(ncfile)
    # close the Dataset.
    ncfile.close()
    logger.info('Dataset is closed!')


# @profile(immediate=True)
# @deprecated
def get_ascii_data(f):
    f = f.split('\n')
    meta = Metadata(
        int(f.pop(0).split('\t')[1]),  # ncols
        int(f.pop(0).split('\t')[1]),  # nrows
        float(f.pop(0).split('\t')[1]),  # xllcorner
        float(f.pop(0).split('\t')[1]),  # yllcorner
        float(f.pop(0).split('\t')[1]),  # cellsize
        int(f.pop(0).split('\t')[1])  # NODATA_value
    )
    logger.info(f'Meta: {meta.ncols}, {meta.nrows}, {meta.xllcorner}, {meta.yllcorner}, {meta.cellsize}, {meta.NODATA_value}')

    data = [np.fromstring(line, dtype=float, sep=" ") for line in f if len(line)]
    # data = np.fromstring(' '.join(f), dtype=float, sep=" ").reshape((nrows, ncols))
    return meta, data


def get_ascii_metadata(file_name: str):
    import linecache
    meta = Metadata(
        int(linecache.getline(file_name, 1).rstrip().split('\t')[1]),  # ncols
        int(linecache.getline(file_name, 2).rstrip().split('\t')[1]),  # nrows
        float(linecache.getline(file_name, 3).rstrip().split('\t')[1]),  # xllcorner
        float(linecache.getline(file_name, 4).rstrip().split('\t')[1]),  # yllcorner
        float(linecache.getline(file_name, 5).rstrip().split('\t')[1]),  # cellsize
        int(linecache.getline(file_name, 6).rstrip().split('\t')[1])  # NODATA_value
    )
    logger.info(f'Meta: {meta.ncols}, {meta.nrows}, {meta.xllcorner}, {meta.yllcorner}, {meta.cellsize}, {meta.NODATA_value}')
    return meta
