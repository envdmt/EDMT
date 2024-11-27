from setuptools import setup, find_packages

setup(
    name='edmt',  # Replace with your package name
    version='1.0.0.1',          # Initial version
    author='Odero & Kuloba',
    author_email='francisodero@maraelephantproject.org',
    description='Environmental Data Management Toolbox',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/envdmt/EDMT.git',  # Replace with your repo URL
    packages=find_packages(),  # Automatically find packages in your repo
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',  # Adjust as needed
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  # Specify the Python versions supported
    install_requires=[
        'geopandas==1.0.1',
        'plotly==5.24.1',
        'seaborn==0.13.2',
        'folium==0.18.0',
        'mapclassify==2.8.1',
        'matplotlib==3.9.2',
        'contextily==1.6.2'
    ],
)
