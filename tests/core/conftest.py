"""Shared fixtures for core tests: one engine per session; saved sample projects."""

import pytest

from engine.matlab_layer import MatlabLayer


@pytest.fixture(scope="session", autouse=True)
def _engine():
    layer = MatlabLayer()
    layer.launch()
    yield
    layer.exit()


@pytest.fixture(scope="session")
def sample_project(tmp_path_factory):
    """Build a small model and save it as a .sbproj; return the path."""
    path = str(tmp_path_factory.mktemp("proj") / "demo.sbproj")
    layer = MatlabLayer()
    e = layer.execute
    e("sbioreset;")
    e("m=sbiomodel('demo'); c=addcompartment(m,'cell'); "
      "addspecies(c,'glucose',10); addspecies(c,'lactate',0); "
      "addparameter(m,'k1',1.5); r=addreaction(m,'glucose -> lactate'); "
      "r.Name='glycolysis';")
    e(f"sbiosaveproject('{path}','m');")
    return path


@pytest.fixture(scope="session")
def two_model_project(tmp_path_factory):
    """A project containing two models, for the ambiguous get_model() branch."""
    path = str(tmp_path_factory.mktemp("proj2") / "two.sbproj")
    layer = MatlabLayer()
    e = layer.execute
    e("sbioreset;")
    e("m1=sbiomodel('demo'); addcompartment(m1,'cell'); "
      "m2=sbiomodel('demo2'); addcompartment(m2,'cell');")
    e(f"sbiosaveproject('{path}','m1','m2');")
    return path
