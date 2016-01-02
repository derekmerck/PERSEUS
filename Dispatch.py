import logging
import time
import yaml
from Messenger import EmailSMSMessenger, SlackMessenger, TwilioMessenger
from EventStore import SplunkEventStore


class Dispatch(object):

    def __init__(self, rules, zones, roles, update_interval=30):
        self.event_store = SplunkEventStore()
        self.alert_router = AlertRouter(zones, roles)
        self.alert_generator = AlertGenerator(rules, self.event_store, self.alert_router, update_interval)

    def run(self):
        self.alert_generator.run()


class AlertGenerator(object):
    # Hard coded to work with a SplunkEventStore for now

    def __init__(self, rules=None, event_store=None, alert_router=None, update_interval=30):
        self.rules = []
        # Convert rule dictionaries into Rule objects
        if rules:
            for rule_args in rules:
                self.rules.append(Rule(**rule_args))

        # If this is None, create a SplunkEventStore()
        if not event_store:
            self.event_store = SplunkEventStore()
        else:
            self.event_store = event_store

        # Okay if this is None for testing
        self.router = alert_router
        self.update_interval = update_interval

    def get_summary_for_rule(self, rule, query_args=None):

        # Use last 30 seconds if no query args were passed in
        if not query_args:
            query_args = {"earliest_time": "now",
                          "latest_time":   "-{0}s".format(self.update_interval)}

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
                    if self.router:
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
        alerted_roles = []
        for role, role_dict in self.roles.iteritems():
            for zone, priorities in role_dict['zones'].iteritems():
                if zone in alerted_zones and rule.priority in priorities:
                    alerted_roles.append(role)
        for role in alerted_roles:
            for relay, relay_args in self.roles[role]['relays'].iteritems():
                self.bridges[relay].message(rule.alert_msg(host, values), **relay_args)



class Rule(object):

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.priority = kwargs.get('priority')
        self.conditions = kwargs.get('conditions')
        self.alert_str = kwargs.get('alert_str')

    def condition_string(self):
        # Could move SplunkEventStore Perseus specific code here
        pass

    def alert_msg(self, host, values):
        s = self.alert_str.format(priority=self.priority,
                                  host=host,
                                  bpm=values['bpm'],
                                  spo2=values['spo2'])
        return s


def test_alert_generator():

    generator = AlertGenerator()

    rule_args = {'name': 'dummy_rule',
                 'priority': 'LOW',
                 'conditions': {},
                 'alert_str': "{priority} alert at {host} | bmp: {bpm}"}
    rule = Rule(**rule_args)
    query_args = None
    response = generator.get_summary_for_rule(rule, query_args=query_args)


def test_alert_router():

    with file('config2.yaml') as f:
        config = yaml.load(f)

    zones = config.get('zones')
    roles = config.get('roles')

    router = AlertRouter(zones, roles)

    host = 'sample1A'

    rule_args = {'name': 'dummy_rule',
                 'priority': 'LOW',
                 'conditions': {},
                 'alert_str': "{priority} alert at {host} | bmp: {bpm}"}
    rule = Rule(**rule_args)

    values = {'bpm': -1,
              'spo2': -1,
              'alert_source': 'DUMMY_SRC',
              'alert_code': 'DUMMY_CODE',
              'ecg_quality': 'GOOD',
              'pleth_quality': 'GOOD'}

    router.alert(host, rule, values)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    # test_alert_generator()
    # test_alert_router()

