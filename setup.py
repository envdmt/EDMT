from setuptools import setup, find_packages

setup(
    name='edmt',  # Replace with your package name
    version='1.0',          # Initial version
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
        'geopandas==1.0.1'
    ],
)
