"""
PERSEUS Setup
Merck, Spring 2015

Indebted to discussion of pip at <https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/>
"""

import os
from setuptools import setup
import PERSEUS


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    name=PERSEUS.__name__,
    description=PERSEUS.__description__,
    author=PERSEUS.__author__,
    author_email=PERSEUS.__email__,
    version=PERSEUS.__version__,
    long_description=read('README.md'),
    url=PERSEUS.__url__,
    license=PERSEUS.__license__,
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
    ]
)