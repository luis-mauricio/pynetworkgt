from pathlib import Path

import pytest

shapely_geometry = pytest.importorskip("shapely.geometry")
from shapely.geometry import LineString  # type: ignore  # noqa: E402

from pynetworkgt_app.core.fracture import FractureLine, FractureNetwork
from pynetworkgt_app.io.txt import (
    FractureTxtError,
    read_fracture_txt,
    write_fracture_txt,
)


def test_read_fracture_network_sample():
    project_root = Path(__file__).resolve().parents[1]
    txt_path = project_root / "Dataset" / "Fracture_Network.txt"

    network = read_fracture_txt(txt_path)

    assert len(network) > 0
    first_line = network.lines[0].geometry
    assert isinstance(first_line, LineString)
    assert first_line.coords[0] == pytest.approx((219534.9701, 128550.54371))
    assert network.source == txt_path


def test_invalid_coordinate_count(tmp_path):
    faulty_path = tmp_path / "broken.txt"
    faulty_path.write_text("1\t2\t3")

    with pytest.raises(FractureTxtError):
        read_fracture_txt(faulty_path)


def test_blank_file(tmp_path):
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("\n\n")

    with pytest.raises(FractureTxtError):
        read_fracture_txt(empty_path)


def test_roundtrip_write_and_read(tmp_path):
    network = FractureNetwork(
        lines=[
            FractureLine(LineString([(0, 0), (1, 1)])),
            FractureLine(LineString([(1, 1), (2, 3), (4, 5)])),
        ],
        crs="EPSG:4326",
    )

    out_path = write_fracture_txt(network, tmp_path / "out.txt")
    reloaded = read_fracture_txt(out_path)

    assert len(reloaded) == len(network)
    assert list(reloaded.lines[1].geometry.coords) == [
        (1.0, 1.0),
        (2.0, 3.0),
        (4.0, 5.0),
    ]

