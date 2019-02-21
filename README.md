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