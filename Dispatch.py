"""
There are 2 parts to Dispatch:
- Alert generation (submit queries against Splunk or other APIs)
- Alert routing (route and submit messages to communication bridges such as email->SMS, Twilio, and Slack
"""

import logging
import time
import yaml
import os
import splunklib.client as SplunkClient
import splunklib.results as SplunkResults

from Messengers import EmailSMSMessenger, SlackMessenger, TwilioMessenger

shadow = None
with file("shadow.yaml") as f:
    shadow = yaml.load(f)


class SplunkEventStore(object):

    def rule_to_query(self, rule):
        # Accept a rule, return a disjunctive query string
        # (alarm conditions) OR (numeric conditions) OR (wave_quality conditions)

        def log_to_query_element(log):
            # Accept a subset of a rule for a single log type and return a conjunctive query string
            # (bpm>100 AND spo2<90)

            def item_to_query_element(condition, value):
                # Accept a condition within a log and return its query string
                # bpm: [GT,100] -> bpm>100

                def get_op(op_str):
                    if op_str == "GT": return ">"
                    elif op_str == "LT": return "<"
                    elif op_str == "EQ": return "="
                    raise NotImplementedError

                return "{cond}{op}{val}".format(cond=condition, op=get_op(value[0]), val=value[1])

            qq = []
            for key, value in log.iteritems():
                qq.append(item_to_query_element(key, value))
            return "(" + " ".join(qq) + ")"

        q = []
        for key, value in rule.iteritems():
            q.append(log_to_query_element(value))
        return "search index=perseus " + " OR ".join(q) + \
               "| stats values(alert_source) as alarm_source " + \
               "values(alert_code) as alarm_code " + \
               "avg(bpm_1) as bpm avg(spo2) as spo2 by host"

    def __init__(self):

        # Create a Service instance and log in
        self.service = SplunkClient.connect(
            host=shadow['credentials']['splunk']['host'],
            port=shadow['credentials']['splunk']['port'],
            username=shadow['credentials']['splunk']['user'],
            password=shadow['credentials']['splunk']['pword'])

        # Verify login
        if not self.service.apps:
            raise IOError

    def test_rule(self, rule, **kwargs):

        searchquery = self.rule_to_query(rule)
        logging.debug(searchquery)

        # searchquery_oneshot = "search index=perseus (alert_source=NOM_ECG_V_P_C_CNT alert_code=NOM_EVT_ECG_V_TACHY) OR (bpm_1>100 spo2>90) | stats values(alert_source) as alarm_source values(alert_code) as alarm_code avg(bpm_1) as bpm avg(spo2) as spo2 by host"

        response = self.service.jobs.oneshot(searchquery, **kwargs)

        # Get the results and display them using the ResultsReader
        reader = SplunkResults.ResultsReader(response)
        r = []
        for item in reader:
            # Remove anything that doesn't have all 4 variables (in particular, the relevant alerts)
            if len(item) < 5: continue
            r.append(dict(item))
            logging.debug(item)

        return r


class AlertGenerator(object):

    def __init__(self):
        self.rules = {}
        self.event_store = None
        self.router = None
        self.hosts = None

    def run(self):
        while 1:
            for host in self.hosts:
                for rule in self.rules:
                    events = self.event_store.test(host, rule)
                    if events:
                        self.router.dispatch(host, rule, events)
            time.sleep(5)


class AlertRouter(object):

    def __init__(self):
        self.zones = {}
        self.bridges = {}
        self.bridges['slack'] = SlackMessenger()
        self.bridges['twilio'] = TwilioMessenger()
        self.bridges['email-sms'] = EmailSMSMessenger()

    def dispatch(self, host, rule, events):

        # Figure out host -> zone
        # Figure out zone -> sink mapping

        devices = self.zones[host].devices

        for device in devices:
            message = rule.message(host, events)
            self.bridges[device.bridge].send(device.recipient, message)


def test_splunk_eventstore():
    S = SplunkEventStore()

    rule_str = """
    alarms:
        alert_source: [EQ, NOM_ECG_V_P_C_CNT]
        alert_code:   [EQ, NOM_EVT_ECG_V_TACHY]
    numerics:
        bpm_1:  [GT, 100]
        spo2:   [GT, 90]
    wave_quality:
        pleth:  [EQ, GOOD]
    """
    rule = yaml.load(rule_str)

    kwargs = {"earliest_time": "1441618949.544",
              "latest_time":   "1441618954.544"}

    response = S.test_rule(rule, **kwargs)
    logging.debug(response)
    assert response == [{'host': 'sample1D', 'alarm_code': 'NOM_EVT_ECG_V_TACHY', 'bpm': '140.000000', 'alarm_source': 'NOM_ECG_V_P_C_CNT', 'spo2': '98.850000'}]

    rule_str = """
    alarms:
        alert_source: [EQ, NOM_PULS_OXIM_SAT_O2]
        alert_code:   [EQ, NOM_EVT_LO]
    numerics:
        spo2:   [LT, 90]
    wave_quality:
        pleth:  [EQ, GOOD]
    """
    rule = yaml.load(rule_str)

    kwargs = {"earliest_time": "1441617114.568",
              "latest_time":   "1441617124.568"}

    response = S.test_rule(rule, **kwargs)
    logging.debug(response)
    assert response == [{'host': 'sample1B', 'alarm_code': 'NOM_EVT_LO', 'bpm': '80.000000', 'alarm_source': 'NOM_PULS_OXIM_SAT_O2', 'spo2': '86.537500'}]

    rule_str = """
    alarms:
        alert_source: [EQ, NOM_ECG_CARD_BEAT_RATE]
        alert_code:   [EQ, NOM_EVT_ECG_ASYSTOLE]
    numerics:
        bpm_1:   [GT, -1]
    wave_quality:
        pleth:  [EQ, POOR]
    """
    rule = yaml.load(rule_str)

    kwargs = {"earliest_time": "1441618275.64",
              "latest_time":   "1441618285.64"}

    response = S.test_rule(rule, **kwargs)
    logging.debug(response)
    assert response == [{'host': 'sample1F', 'alarm_code': 'NOM_EVT_ECG_ASYSTOLE', 'bpm': '0.000000', 'alarm_source': 'NOM_ECG_CARD_BEAT_RATE', 'spo2': '8388607.000000'}]

    kwargs = {"earliest_time": "2015-09-07T13:31:20.640+04:00",
              "latest_time":   "2015-09-07T13:32:20.640+04:00"}

    response = S.test_rule(rule, **kwargs)
    logging.debug(response)




if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)


