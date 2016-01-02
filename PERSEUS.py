"""
PERSEUS Core
Push Electronic Relay for Smart Alarms for End User Situational Awareness (PERSEUS)

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: PyYAML, splunk-sdk, Twilio

See README.md for usage, notes, and license info.
"""

import logging
import argparse
import yaml
from Dispatch import Dispatch

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '3', '0')
__version__ = '.'.join(__version_info__)


def parse_args():

    parser = argparse.ArgumentParser(description='PERSEUS Core')
    parser.add_argument('--config',
                        default='config.yaml',
                        help='YAML description of the alert rules, zones, and roles (default: config.yaml)')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    p = parser.parse_args()

    with open(p.config, 'rU') as f:
        config = yaml.load(f)

    return config.get('rules'), config.get('zones'), config.get('roles')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    rules, zones, roles = parse_args()

    dispatch = Dispatch(rules, zones, roles)
    dispatch.run()

