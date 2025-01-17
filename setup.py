from setuptools import setup, find_packages

setup(
    name='edmt',
    version='1.0.0.1',        
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
)