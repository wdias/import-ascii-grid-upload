# import-ascii-grid-upload
Import ASCII Grid as upload files microservice.

### /import/ascii-grid/upload/<timeseries_id>

Upload files with `headers`
```json
Content-Type: multipart/form-data
```

In the body of `form-data`;
- Each **key** should be the `Timestamp` of the ASCII GRID file in `2017-09-15T00:00:00Z` format.
- The **value** should be a  [ERIS ASCII GRID](https://en.wikipedia.org/wiki/Esri_grid) file with `.asc` file extension.

Files should be `utf-8` encoded.

### References:
- [Forum: Converting ascii to netCDF files - CDO](https://code.mpimet.mpg.de/boards/1/topics/3631)
- [Flask Profiling](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xvi-debugging-testing-and-profiling)
- [Merge NetCDF Files with xarray](https://stackoverflow.com/questions/47226429/join-merge-multiple-netcdf-files-using-xarray)
