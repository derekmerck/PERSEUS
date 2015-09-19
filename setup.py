"""
PERSEUS Setup
Merck, Spring 2015

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Numpy, matplotlib

See README.md for usage, notes, and license info.


## Distribution to a pypi server:

```
$ pandoc --from=markdown --to=rst --output=README.rst README.md
$ python setup.py sdist
$ python setup.py register [-r https://testpypi.python.org/pypi]
$ python setup.py sdist upload  [-r https://testpypi.python.org/pypi]
```
"""

import os

from setuptools import setup

import PERSEUS

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

# README.md is preferred
long_desc = read('README.md')
# pypi requires a README.rst, so we create one with pandoc and include it in the source distribution
if os.path.exists('README.rst'):
    long_desc = read('README.rst')

setup(
    name=PERSEUS.__package__,
    description=PERSEUS.__description__,
    author=PERSEUS.__author__,
    author_email=PERSEUS.__email__,
    version=PERSEUS.__version__,
    long_description=long_desc,
    url=PERSEUS.__url__,
    license=PERSEUS.__license__,
    py_modules=["PERSEUS"],
    include_package_data=True,
    zip_safe=True,
    install_requires=['Pyro4', 'PyYAML', 'Numpy', 'Fabric', 'matplotlib'],
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