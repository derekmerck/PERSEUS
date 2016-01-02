"""
There are 2 parts to Dispatch:
- Alert generation (submit queries against Splunk or other APIs)
- Alert routing (route and submit messages to communication bridges such as email->SMS, Twilio, and Slack
"""

import logging
import time
import yaml
import os
from Messenger import EmailSMSMessenger, SlackMessenger, TwilioMessenger
from EventStore import SplunkEventStore

# Lookup credentials from either os.env or shadow.yaml
shadow = None
with file("shadow.yaml") as f:
    shadow_env = yaml.load(f)
os.environ.update(shadow_env)


class AlertGenerator(object):
    # Hard coded to work with a SplunkEventStore for now

    def __init__(self):
        self.rules = {}
        self.event_store = SplunkEventStore()
        self.router = None
        self.hosts = None

    def get_summary_for_rule(self, rule, query_args=None):

        if not query_args:
            query_args = {"earliest_time": "now",
                          "latest_time":   "-30s"}

        query_str = SplunkEventStore.perseus_rule_to_query_str(rule)
        logging.debug(query_str)
        response = self.event_store.get_summary(query_str, query_args, 5 )

        # Should format response to return a dictionary of violations for a rule
        # { host0: {summary_values},
        #   host1: {summary_values} ... }
        return response

    def run(self):
        while 1:
            for rule in self.rules:
                results = self.get_summary_for_rule(rule)
                if not results: break
                for host, values in results.iteritems():
                    self.router.alert(host, rule, values)
            time.sleep(15)


class AlertRouter(object):

    def __init__(self, zones, roles):
        self.zones = zones
        self.roles = roles
        self.bridges = {'slack': SlackMessenger(),
                        'twilio-sms': TwilioMessenger(),
                        'email-sms': EmailSMSMessenger()}

    def alert(self, host, rule, values):

        alerted_zones = []
        for zone, hosts in self.zones.iteritems():
            if host in hosts:
                alerted_zones.append(zone)

        # logging.debug(alerted_zones)

        alerted_roles = []
        for role, role_dict in self.roles.iteritems():
            for zone, priorities in role_dict['zones'].iteritems():

                # logging.debug(zone)
                # logging.debug(priorities)
                if zone in alerted_zones and rule['priority'] in priorities:
                    alerted_roles.append(role)

        # logging.debug(alerted_roles)
        #
        for role in alerted_roles:
            for relay, relay_args in self.roles[role]['relays'].iteritems():
                self.bridges[relay].message('ABC', **relay_args)



def test_alert_generator():

    generator = AlertGenerator()

    pass


def test_alert_router():

    with file('config2.yaml') as f:
        config = yaml.load(f)

    zones = config['zones']
    roles = config['roles']

    router = AlertRouter(zones, roles)

    host = 'sample1A'

    rule = {'name': 'dummy_rule',
            'priority': 'HIGH',
            'conditions': {}}

    values = {'bmp': -1,
              'spo2': -1,
              'alert_source': 'DUMMY_SRC',
              'alert_code': 'DUMMY_CODE',
              'ecg_quality': 'GOOD',
              'pleth_quality': 'GOOD'}

    # router.alert(host, rule, values)
    # # Should alert everyone

    host = 'dummy_host'
    router.alert(host, rule, values)
    # Should not alert anyone


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_alert_router()

