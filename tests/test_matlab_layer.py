import pytest

from engine.matlab_layer import MatlabLayer

def test_singleton_behavior():
    # Ensure that multiple calls to launch return the same engine instance
    eng1 = MatlabLayer.launch()
    eng2 = MatlabLayer.launch()
    assert eng1 == eng2, "Multiple calls to launch should return the same engine instance"

def test_execute_command():
    MatlabLayer.launch()
    result = MatlabLayer.execute("1 + 1", nargout=1)
    assert result == 2, "MATLAB should correctly evaluate simple expressions"

def test_is_alive():
    MatlabLayer.launch()
    assert MatlabLayer.is_alive(), "MATLAB engine should be alive after launch"
    MatlabLayer.exit()
    assert not MatlabLayer.is_alive(), "MATLAB engine should not be alive after exit"

