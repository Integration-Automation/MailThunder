"""``dev.toml`` describes the same package as ``pyproject.toml`` under another name.

The dev channel (``je_mail_thunder_dev``) is built by writing ``dev.toml`` to ``pyproject.toml``, while
the tests run against the checked-out source and the stable metadata. A dependency, entry point or
package rule on one side only ships a dev package that differs from what was tested.
"""
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # reason: stdlib from 3.11; CI also runs 3.10

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> dict:
    with (REPO_ROOT / name).open("rb") as handle:
        return tomllib.load(handle)


STABLE_FILE = _load("pyproject.toml")
DEV_FILE = _load("dev.toml")
STABLE = STABLE_FILE["project"]
DEV = DEV_FILE["project"]


def test_package_names_differ():
    assert STABLE["name"] == "je_mail_thunder"
    assert DEV["name"] == "je_mail_thunder_dev"


def test_runtime_dependencies_match():
    assert sorted(DEV["dependencies"]) == sorted(STABLE["dependencies"])


def test_python_floor_matches():
    assert DEV["requires-python"] == STABLE["requires-python"]


@pytest.mark.parametrize("field", ["description", "authors", "maintainers", "license", "readme", "urls"])
def test_what_the_pypi_page_shows_matches(field):
    # One project under two names: both PyPI pages describe it the same way.
    assert DEV[field] == STABLE[field]


@pytest.mark.parametrize("field", ["keywords", "classifiers"])
def test_keywords_and_classifiers_match(field):
    assert sorted(DEV[field]) == sorted(STABLE[field])


def test_the_pypi_page_is_filled_in():
    # The description was an empty string, and the only link was the repository.
    assert STABLE["description"].strip()
    assert STABLE["keywords"]
    assert {"Homepage", "Documentation", "Repository", "Issues", "Changelog"} <= set(STABLE["urls"])
    assert all(url.startswith("https://") for url in STABLE["urls"].values())
    assert any(classifier.startswith("Topic :: Communications :: Email") for classifier in STABLE["classifiers"])


def test_optional_dependency_groups_match():
    assert DEV.get("optional-dependencies", {}) == STABLE.get("optional-dependencies", {})


@pytest.mark.parametrize("table", ["scripts", "gui-scripts", "entry-points"])
def test_entry_points_match(table):
    assert DEV.get(table, {}) == STABLE.get(table, {})


def test_shipped_files_match():
    # Package discovery and package data decide which files reach the wheel.
    assert DEV_FILE["tool"]["setuptools"] == STABLE_FILE["tool"]["setuptools"]
