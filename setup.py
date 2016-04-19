"""
PERSEUS Setup
Merck, Summer 2015

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2016

<https://github.com/derekmerck/PERSEUS>

Dependencies: PyYAML, splunk-sdk, Twilio, numpy, scipy, matplotlib, pyserial

See README.md for usage, notes, and license info.

## Distribution to a pypi server:

```bash
$ pandoc --from=markdown --to=rst --output=README.rst README.md
$ python setup.py sdist
$ python setup.py register [-r https://testpypi.python.org/pypi]
$ python setup.py sdist upload [-r https://testpypi.python.org/pypi]
```
"""

import os
from setuptools import setup
from PERSEUS import __url__, __package__, __license__, __description__, __author__, __email__, __version__

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
    name=__package__,
    description=__description__,
    author=__author__,
    author_email=__email__,
    version=__version__,
    long_description=long_desc,
    url=__url__,
    license=__license__,
    py_modules=["PERSEUS",
                "Dispatch.Dispatch", "Dispatch.Messenger", "Dispatch.EventStore",
                "TelemetryLogger.CWRU_utils",
                "TelemetryStream.TelemetryStream",
                "TelemetryStream.SimpleStripChart",
                "TelemetryStream.PhilipsTelemetryStream",
                "TelemetryStream.QualityOfSignal",
                "TelemetryStream.IntellivueProtocol.IntellivueDecoder",
                "TelemetryStream.IntellivueProtocol.IntellivueDistiller",
                "TelemetryStream.IntellivueProtocol.RS232"],
    include_package_data=True,
    zip_safe=True,
    install_requires=['PyYAML', 'Twilio', 'splunk-sdk', 'pyserial', 'numpy', 'scipy', 'matplotLib'],
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