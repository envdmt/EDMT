# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html 

# -- Project information -----------------------------------------------------
project = 'EDMT'
copyright = '2025, Odero, Kuloba, Musasia'
author = 'Odero, Kuloba, Musasia'
release = '1.0.1.dev0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autosummary',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # For NumPy/Google-style docstrings
    'sphinx_togglebutton',  # For dropdown support
    'sphinx.ext.todo',      # Optional: Enable to-do sections
]

# Templates path (ensure this folder exists)
templates_path = ['_templates']

# Files or patterns to exclude
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '**/.venv',             # Skip virtual environments
    '**/__pycache__',       # Skip Python cache
]

# -- Options for HTML output -------------------------------------------------

# Use a better theme for technical documentation
html_theme = 'sphinx_rtd_theme'  # Better than Alabaster for API docs

# If you want to keep Alabaster, install it explicitly:
# pip install alabaster
# html_theme = 'alabaster'

html_static_path = ['_static']

# Optional: Add logo, favicon, custom CSS
html_logo = '_static/edmt.jpeg' 
# html_favicon = '_static/favicon.ico'
# html_css_files = ['custom.css'] 

# -- Extension settings ------------------------------------------------------

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True

# Autosummary settings
autosummary_generate = True  # Automatically generate stub pages
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'special-members': False,
    'inherited-members': False,
    'show-inheritance': True,
}

# Toggle button settings
togglebutton_hint = "Click to expand"
togglebutton_hint_hide = "Click to collapse"

# Todo extension settings
todo_include_todos = True