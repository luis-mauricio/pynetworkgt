from pathlib import Path

import pytest

shapely_geometry = pytest.importorskip("shapely.geometry")
LineString = shapely_geometry.LineString

geopandas_module = pytest.importorskip("geopandas")
import geopandas as gpd  # type: ignore  # noqa: E402

from pynetworkgt_app.core.fracture import FractureLine, FractureNetwork
from pynetworkgt_app.io.gpkg import (
    FractureGpkgError,
    read_fracture_gpkg,
    write_fracture_gpkg,
)


def test_read_fracture_gpkg(tmp_path):
    path = Path(tmp_path) / "fractures.gpkg"
    geometry = [LineString([(0, 0), (1, 1), (2, 2)])]
    gdf = gpd.GeoDataFrame({"id": [1], "geometry": geometry}, geometry="geometry", crs="EPSG:4326")
    gdf.to_file(path, layer="fractures", driver="GPKG")

    network = read_fracture_gpkg(path, layer="fractures")
    assert len(network) == 1
    assert network.crs is not None
    assert network.lines[0].properties["id"] == 1


def test_roundtrip_gpkg(tmp_path):
    path = Path(tmp_path) / "roundtrip.gpkg"
    network = FractureNetwork(
        lines=[
            FractureLine(LineString([(0, 0), (1, 1)]), {"name": "A"}),
            FractureLine(LineString([(1, 1), (1, 4)]), {"name": "B"}),
        ],
        crs="EPSG:3857",
    )

    write_fracture_gpkg(network, path, layer="network")
    reloaded = read_fracture_gpkg(path, layer="network")

    assert len(reloaded) == 2
    assert reloaded.crs is not None
    names = {line.properties["name"] for line in reloaded.lines}
    assert names == {"A", "B"}


def test_read_fracture_gpkg_missing_file(tmp_path):
    missing = Path(tmp_path) / "missing.gpkg"
    with pytest.raises(FractureGpkgError):
        read_fracture_gpkg(missing)

