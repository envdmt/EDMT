from setuptools import setup, find_packages

versions = [
    '1.0.1+e',  # Local Version
    '1.0.1-e',  # Pre-Release Identifier
    '1.0.1.dev0',  # Development Release
    '1.0.1.post0' # Post-Release
    ]

release = [
    '1.0.1a1', # Alpha version 1
    '1.0.1b1', # Beta version 1
    '1.0.1rc1', # Release Candidate 1

]

setup(
    name='edmt',
    version=versions[0],        
    author='Odero & Kuloba',
    author_email='francisodero@maraelephantproject.org',
    description='Environmental Data Management Toolbox',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/envdmt/EDMT.git',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', 
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  
    install_requires=[
        'geopandas==0.14.2',
        'plotly==5.24.1',
        'seaborn==0.13.2',
        'folium==0.18.0',
        'mapclassify==2.8.1',
        'matplotlib==3.9.2',
        'contextily==1.6.2',
        'fiona==1.9.6'
    ],
    entry_points={
        'console_scripts': [
            'edmt-version=edmt.version:print_version',
        ],
    },
)