# Data IO Overview

PyNetworkGT currently supports two input/output formats for fracture networks, both mapped to the shared `FractureNetwork` domain object.

## TXT Format
- Parser: `pynetworkgt_app.io.read_fracture_txt`
- Writer: `pynetworkgt_app.io.write_fracture_txt`
- Expectations: each line contains an even number of tab- or whitespace-separated numeric values interpreted as `x1 y1 x2 y2 ...`.
- Result: every line becomes a `FractureLine` with a Shapely `LineString` geometry. Writing preserves the vertex order, emits optional comments for CRS/source metadata, and defaults to tab-separated output.
- Errors: malformed coordinates, odd number of values, blank files, or empty geometries raise `FractureTxtError`.

## GeoPackage (GPKG)
- Parser: `pynetworkgt_app.io.read_fracture_gpkg`
- Writer: `pynetworkgt_app.io.write_fracture_gpkg`
- Dependencies: requires `geopandas` (and its GDAL stack) at runtime.
- Behaviour: loads a specified layer (default: first). Only `LineString`/`MultiLineString` features are accepted; multi-lines explode into individual `FractureLine` entries by default. Export uses `FractureNetwork.to_geodataframe()` and overwrites the target file unless `overwrite=False`.
- Attributes: non-geometry columns are preserved inside `FractureLine.properties` when `include_attributes=True`; round-trips maintain these values.
- Errors: missing files, unsupported geometry types, empty layers, or read/write failures raise `FractureGpkgError`.

## Export / Round-trip
- `FractureNetwork.to_geodataframe()` converts the in-memory network to a `geopandas.GeoDataFrame`, enabling further export (`to_file`) or analysis.
- TXT and GPKG writers allow reserialisation of processed networks. Additional formats (GeoJSON, CSV with WKT, etc.) will be added in future iterations.

