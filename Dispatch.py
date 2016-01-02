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

    def __init__(self):
        self.zones = {}
        self.bridges = {'slack': SlackMessenger(),
                        'twilio': TwilioMessenger(),
                        'email-sms': EmailSMSMessenger()}

    def alert(self, host, rule, values):

        # Figure out host -> zone
        # Figure out zone -> sink mapping

        devices = self.zones[host].devices

        for device in devices:
            message = rule.message(host, events)
            self.bridges[device.bridge].send(device.recipient, message)


def test_alert_generator():

    generator = AlertGenerator()

    pass


def test_alert_router():

    router = AlertRouter()

    pass

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)


