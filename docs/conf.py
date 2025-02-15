# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath("../.."))  # Necessary for viewcode
sys.path.insert(0, os.path.abspath(".."))

project = 'EDMT'
copyright = '2025, envdmt'
author = 'envdmt'

source_suffix = {
    ".rst": "restructuredtext",
}

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'autoapi.extension',
    'sphinx.ext.autodoc', 
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    ]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'Python'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = 'sphinx_rtd_theme' #pydata_sphinx_theme
html_static_path = ['_static']

autoapi_dirs = ['../edmt']


html_title = "EDMT Docs"
# html_favicon = "_static/images/favicon.ico"
# html_logo = "_static/images/logo.svg"

# material theme options (see theme.conf for more information)
html_theme_options = {
    "github_url": "https://github.com/envdmt/EDMT",
    "pygment_light_style": "rainbow_dash",
    "pygment_dark_style": "dracula",
}