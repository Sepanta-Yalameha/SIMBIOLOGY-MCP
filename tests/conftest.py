"""Shared fixtures: one engine per session; a saved sample project."""
import pytest
from engine.matlab_layer import MatlabLayer


@pytest.fixture(scope="session", autouse=True)
def _engine():
    MatlabLayer.launch()
    yield
    MatlabLayer.exit()


@pytest.fixture(scope="session")
def sample_project(tmp_path_factory):
    """Build a small model and save it as a .sbproj; return the path."""
    path = str(tmp_path_factory.mktemp("proj") / "demo.sbproj")
    e = MatlabLayer.execute
    e("sbioreset;")
    e("m=sbiomodel('demo'); c=addcompartment(m,'cell'); "
      "addspecies(c,'glucose',10); addspecies(c,'lactate',0); "
      "addparameter(m,'k1',1.5); r=addreaction(m,'glucose -> lactate'); "
      "r.Name='glycolysis';")
    e(f"sbiosaveproject('{path}','m');")
    return path
