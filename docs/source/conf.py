# Configuration file for the Sphinx documentation builder.
#
# For the full list of configuration options see:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("source"))
sys.path.insert(1, str(Path(__file__).parent))
sys.path.insert(2, str(Path(__file__).parent.parent))

# -- Project information -----------------------------------------------------

project = "MailThunder"
project_copyright = "2020 ~ Now, JE-Chen"
author = "JE-Chen"

# -- General configuration ---------------------------------------------------

extensions = []

templates_path = ["_templates"]

exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

# -- Options for sphinx_rtd_theme --------------------------------------------

html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "titles_only": False,
}
