import logging
import time
import yaml
import os
from Messenger import EmailSMSMessenger, SlackMessenger, TwilioMessenger
from EventStore import SplunkEventStore
import datetime
import dateutil.parser

# Lookup credentials from either os.env or shadow.yaml
shadow = None
with file("shadow.yaml") as f:
    shadow_env = yaml.load(f)
os.environ.update(shadow_env)


class Dispatch(object):

    def __init__(self, rules, zones, roles, update_interval=30):
        self.event_store = SplunkEventStore()
        self.alert_router = AlertRouter(zones, roles)
        self.alert_generator = AlertGenerator(rules, self.event_store, self.alert_router)

    def run(self):
        self.alert_generator.run()


class AlertGenerator(object):
    # Hard coded to work with a SplunkEventStore for now

    def __init__(self, rules=None, event_store=None, alert_router=None):
        self.rules = []
        # Convert rule dictionaries into Rule objects
        if rules:
            for rule_args in rules:
                self.rules.append(Rule(**rule_args))

        # If event_store is not given, create a SplunkEventStore()
        if not event_store:
            self.event_store = SplunkEventStore()
        else:
            self.event_store = event_store

        self.router = alert_router
        if not self.router:
            # Create a log alert only for testing
            self.router = AlertRouter()

        # Some default timings (in secs)
        self.update_interval = 30
        self.history_interval = 120    # query earliest time offset (seconds)
        self.entry_interval = 10       # timechart time span

    def review(self, host, rule, start_time, end_time):
        # Assess historical data against a particular rule and return the number of violations
        # Useful for testing

        number_of_alerts = 0

        this_time = start_time
        while this_time < end_time:
            tic = time.clock()
            query_args = {"latest_time": this_time.isoformat(),
                          "earliest_time": (this_time - datetime.timedelta(seconds=self.history_interval)).isoformat()}

            logging.debug(query_args)

            results = self.event_store.get_summary(host, rule.conditions, self.entry_interval, query_args)
            logging.debug(results)

            if results:
                self.router.alert(host, rule, results[0])
                number_of_alerts += 1

            toc = time.clock()
            logging.debug("Update time: " + str(toc - tic))
            this_time += datetime.timedelta(seconds=self.update_interval)

        return number_of_alerts

    def run(self):
        while 1:
            tic = time.clock()

            query_args = {"latest_time": "now",
                          "earliest_time": "-{0}s".format(self.history_interval)}

            for host in self.router.hosts:
                for rule in self.rules:
                    results = self.event_store.get_summary(host, rule.conditions, self.entry_interval, query_args)
                    if results:
                        self.router.alert(host, rule, results[0])
            toc = time.clock()
            logging.debug("Update time: " + str(toc - tic))
            time.sleep(self.update_interval - (toc - tic))


class AlertRouter(object):

    def __init__(self, zones=None, roles=None):
        self.zones = zones
        self.roles = roles
        self.bridges = {'slack': SlackMessenger(),
                        'twilio-sms': TwilioMessenger(),
                        'email-sms': EmailSMSMessenger()}

        hosts = []
        if self.zones:
            for zone in self.zones.values():
                hosts = hosts + zone
        self.hosts = set(hosts)

    def alert(self, host, rule, values):

        logging.info(rule.alert_msg(host, values))
        if not self.zones or not self.roles:
            # Just log all alerts
            return

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

    def alert_msg(self, host, values):
        logging.debug(values)

        s = self.alert_str.format(priority=self.priority,
                                  host=host,
                                  **values)
        return s


def test_alert_generator():

    generator = AlertGenerator()

    rule_args = {'name': 'dummy_rule',
                 'priority': 'LOW',
                 'conditions': {'bpm': ['GT', 50]},
                 'alert_str': "{priority} alert at {host} | bmp: {bpm}"}
    rule = Rule(**rule_args)
    host = "sample1A"
    start_time = dateutil.parser.parse('2015-09-07T12:59:00.000')
    end_time = start_time + datetime.timedelta(minutes=10)
    number_of_alerts = generator.review(host, rule, start_time, end_time)

    logging.debug(number_of_alerts)
    assert number_of_alerts == 8


def test_alert_router():

    with file('config.yaml') as f:
        config = yaml.load(f)

    zones = config.get('zones')
    roles = config.get('roles')

    router = AlertRouter(zones, roles)

    assert router.hosts == {'sample1A', 'sample1C', 'sample1B', 'sample1E', 'sample1D', 'sample1F'}

    host = 'sample1A'

    rule_args = {'name': 'dummy_rule',
                 'priority': 'LOW',
                 'conditions': {},
                 'alert_str': "{priority} alert at {host} | bmp: {bpm}"}
    rule = Rule(**rule_args)

    values = {'bpm': -1,
              'spo2': -1,
              'alarm_source': 'DUMMY_SRC',
              'alarm_code': 'DUMMY_CODE',
              'pleth_quality': 'DUMMY_VAL'}

    msg = rule.alert_msg(host, values)
    assert msg == "LOW alert at sample1A | bmp: -1"

    router.alert(host, rule, values)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_alert_generator()
    #test_alert_router()

