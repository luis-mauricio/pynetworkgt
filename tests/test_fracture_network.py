import pytest

shapely_geometry = pytest.importorskip("shapely.geometry")
LineString = shapely_geometry.LineString

from pynetworkgt_app.core.fracture import FractureLine, FractureNetwork


def test_total_length():
    network = FractureNetwork(
        lines=[
            FractureLine(LineString([(0, 0), (3, 4)])),
            FractureLine(LineString([(0, 0), (0, 5)])),
        ]
    )
    assert pytest.approx(network.total_length()) == 10


def test_to_geodataframe_requires_geopandas(monkeypatch):
    network = FractureNetwork(lines=[FractureLine(LineString([(0, 0), (1, 1)]))])

    # If geopandas is missing this call should raise ImportError.
    monkeypatch.setattr("pynetworkgt_app.core.fracture.gpd", None, raising=False)
    with pytest.raises(ImportError):
        network.to_geodataframe()

