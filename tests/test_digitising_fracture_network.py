import numpy as np
import pytest

pytest.importorskip("networkx")
pytest.importorskip("skimage")


from pynetworkgt_app.algorithms.digitising import digitise_fracture_network, DigitiseOptions


def test_digitise_cross_shape():
    array = np.zeros((9, 9), dtype=bool)
    array[4, :] = True
    array[:, 4] = True

    network = digitise_fracture_network(array)

    assert len(network.lines) == 4
    lengths = sorted(line.geometry.length for line in network.lines)
    assert all(length > 3.5 for length in lengths)


def test_digitise_inverted_binary():
    array = np.ones((5, 5), dtype=int)
    array[1:4, 2] = 0

    options = DigitiseOptions(invert=True)
    network = digitise_fracture_network(array, options=options)

    assert len(network.lines) == 1
    line = network.lines[0].geometry
    assert np.isclose(line.length, 3.0, atol=1e-6)


def test_digitise_with_simplify_and_min_length():
    array = np.zeros((6, 6), dtype=bool)
    array[2, 1:5] = True

    options = DigitiseOptions(simplify_tolerance=0.5, min_branch_length=2.0)
    transform = (1.0, 0.0, 10.0, 0.0, 1.0, 20.0)
    network = digitise_fracture_network(array, transform=transform, options=options)

    assert len(network.lines) == 1
    line = network.lines[0].geometry
    assert line.coords[0][0] == 10 + 1.5
    assert np.isclose(line.length, 4.0, atol=1e-6)
