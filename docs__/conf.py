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
    'sphinx.ext.napoleon', 
    'sphinx_togglebutton', 
    'sphinx.ext.todo',  
    'nbsphinx', 
]

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '**/.venv',            
    '**/__pycache__',      
    '**.ipynb_checkpoints'
]

# -- Options for HTML output -------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_theme_path = ["."]
html_static_path = ['_static']
html_logo = '_static/edmt.jpeg'

nbsphinx_pygments_lexer = 'python3'

# -- Extension settings ------------------------------------------------------

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True

autosummary_generate = True 
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'special-members': False,
    'inherited-members': False,
    'show-inheritance': True,
}

togglebutton_hint = "Click to expand"
togglebutton_hint_hide = "Click to collapse"

todo_include_todos = True