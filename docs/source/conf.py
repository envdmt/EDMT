import os
import sys
sys.path.insert(0, os.path.abspath('../../')) 

import logging
logging.basicConfig()
logging.getLogger('nbsphinx').setLevel(logging.DEBUG)

project = 'EDMT'
copyright = '2026, EDMT'
author = 'Odero'
release = '1.0.8'

extensions = [        
    'autoapi.extension',
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
]

nb_execution_mode = "off"
autoapi_dirs = ['../../edmt']
templates_path = ['_templates']
autoapi_template_dir = '_templates/autoapi'
exclude_patterns = []
language = 'Python'

html_theme = 'furo'
html_static_path = ['_static']

autoapi_options = [
    'undoc-members',
    'show-inheritance',
    'imported-members',
]

autoapi_keep_files = True

autoapi_python_use_implicit_namespaces = True  
autoapi_python_imported_members = True   

autoapi_add_toctree_entry = False


autoapi_ignore = [
]