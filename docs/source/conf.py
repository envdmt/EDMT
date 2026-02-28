import os
import sys
sys.path.insert(0, os.path.abspath('../../')) 

import logging
logging.basicConfig()
logging.getLogger('nbsphinx').setLevel(logging.DEBUG)

project = 'EDMT'
copyright = '2026, EDMT'
author = 'Odero,Kuloba & Musasia'
release = '1.0.2'

# General configuration
extensions = [        
    'autoapi.extension',
]

# Path to your source code
autoapi_dirs = ['../../edmt']
templates_path = ['_templates']
autoapi_template_dir = '_templates/autoapi'
exclude_patterns = []

language = 'Python'

# Options for HTML output
html_theme = 'furo'
html_static_path = ['_static']

# Optional: Include private members
autoapi_options = ['members', 'undoc-members', 'private-members']
autoapi_keep_files = True