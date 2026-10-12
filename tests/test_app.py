"""Runs the whole Streamlit script headless against the synthetic workbook."""
import os

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from tests.make_sample import write

    path = tmp_path_factory.mktemp("data") / "sample.xlsx"
    write(str(path))
    os.environ["TROLLEY_XLSX_PATH"] = str(path)
    at = st_testing.AppTest.from_file("../app.py", default_timeout=90)
    at.run()
    yield at
    os.environ.pop("TROLLEY_XLSX_PATH", None)


def test_runs_without_errors(app):
    assert not app.exception, app.exception
    assert len(app.error) == 0, [e.value for e in app.error]


def test_has_all_tabs(app):
    labels = [t.label for t in app.tabs]
    assert labels[0] == "Overview"
    assert "Follow-up" in labels and "All records" in labels
    assert any(lbl.startswith("Data health") for lbl in labels)


def test_filters_rerun(app):
    app.multiselect[0].select(app.multiselect[0].options[0]).run()
    assert not app.exception, app.exception


def test_empty_state(monkeypatch):
    monkeypatch.delenv("TROLLEY_XLSX_PATH", raising=False)
    at = st_testing.AppTest.from_file("../app.py", default_timeout=60)
    at.run()
    assert not at.exception, at.exception
