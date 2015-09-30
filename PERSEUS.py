"""
PERSEUS Core
Push Electronic Relay for Smart Alarms for End User Situational Awareness (PERSEUS)

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Pyro4, Numpy, matplotlib, PyYAML

See README.md for usage, notes, and license info.
"""

import sys
# Assume that duppy may be in PERSEUS/duppy or ../duppy
sys.path.extend(['duppy', '../duppy'])
import logging
from PyroNode import PyroNode
from PERSEUSNode import PERSEUSNode, ControlNode, getNode
import argparse
import yaml

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '2', '1')
__version__ = '.'.join(__version_info__)


def parse_args():

    parser = argparse.ArgumentParser(description='PERSEUS Core')
    parser.add_argument('pn_id',
                        nargs='+',
                        metavar='node_id',
                        help='List of nodes in the topology to run on this instance')
    parser.add_argument('--config',
                        default='config.yaml',
                        help='YAML description of the topology and alert rules')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    p = parser.parse_args()

    with open(p.config, 'rU') as f:
        topology, rules, zones = yaml.load_all(f)

    # try:
    with open('shadow_'+p.config, 'rU') as f:
        shadow_topology, shadow_rules, shadow_zones = yaml.load_all(f)
        if shadow_topology:
            shadow_topology.update(shadow_topology)
        if shadow_zones:
            if shadow_zones.get('sms_relay'):
                zones['sms_relay'].update(shadow_zones['sms_relay'])
            if shadow_zones.get('devices'):
                zones['devices'].update(shadow_zones['devices'])
    # except:
    #     logging.debug('Can not read {0}'.format('shadow_'+p.config))

    return p, topology, rules, zones


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    p, topology, rules, zones = parse_args()

    for item in p.pn_id:
        node = PERSEUSNode(item, **topology[item])
        if isinstance(node, ControlNode):
            node.setup_alerts( rules, zones )
        node.run()

    logging.debug("Up: {0}".format(p.pn_id))
    PyroNode.daemon.requestLoop()

