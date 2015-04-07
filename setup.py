import os
from setuptools import setup, find_packages

version_info = ('0', '1', '2')
version = '.'.join(version_info)

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    author='Derek Merck',
    author_email="derek_merck@brown.edu",
    name="PERSEUS",
    version=version,
    description="Push Electronic Relay for Smart Alarms for End User Situational Awareness",
    long_description=read('README.rst'),
    url="https://github.com/derekmerck/PERSEUS",
    license="MIT",
    #packages=find_packages(exclude=['tests*']),
    #packages = ["PERSEUS"],
    py_modules=["PERSEUS", "SimpleDisplay"],
    include_package_data=True,
    zip_safe=True,
    install_requires=['Pyro4', 'PyYAML', 'Numpy'],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Healthcare Industry',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Medical Science Apps.'
    ],
)