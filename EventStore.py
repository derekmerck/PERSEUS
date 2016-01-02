"""
Should support a range of event storage types.  Splunk is easy to setup, so we focused on that.
Could also easily support an ELK stack or a custom python shipper/indexer (as I wrote in the
previous Perseus v0.2).
"""

import logging
import yaml
import os
import splunklib.client as SplunkClient
import splunklib.results as SplunkResults


# Lookup credentials from either os.env or shadow.yaml
shadow = None
with file("shadow.yaml") as f:
    shadow_env = yaml.load(f)
os.environ.update(shadow_env)


class EventStore(object):

    def get_events(self, query_str, query_args):
        raise NotImplementedError


class SplunkEventStore(object):

    def __init__(self):

        # Create a Service instance and log in
        self.service = SplunkClient.connect(
            host=os.environ['SPLUNK_HOST'],
            port=os.environ['SPLUNK_PORT'],
            username=os.environ['SPLUNK_USER'],
            password=os.environ['SPLUNK_PWORD'])

        # Verify login
        if not self.service.apps:
            raise IOError

    # This is particular to the PERSEUS application, could be peeled out and put in perseus rule
    @classmethod
    def perseus_rule_to_query_str(cls, rule):
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
                    elif op_str == "GTE": return ">="
                    elif op_str == "LT": return "<"
                    elif op_str == "LTE": return "<="
                    elif op_str == "EQ": return "="
                    elif op_str == "NE": return "!="
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

    def get_summary(self, query_str, query_args, nitems=5):

        response = self.service.jobs.oneshot(query_str, **query_args)
        # Get the results and iterate through them using the ResultsReader
        reader = SplunkResults.ResultsReader(response)
        r = []
        for item in reader:
            # Remove anything that doesn't have all items
            if len(item) < nitems: continue
            r.append(dict(item))
            logging.debug(item)

        return r


    def get_events(self, query_str, query_args):

        response = self.service.jobs.oneshot(query_str, **query_args)
        # Get the results and iterate through them using the ResultsReader
        reader = SplunkResults.ResultsReader(response)
        r = []
        for item in reader:
            r.append(dict(item))
            logging.debug(item)

        return r


def test_splunk_event_store():

    splunk = SplunkEventStore()

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
    query_str = SplunkEventStore.perseus_rule_to_query_str(rule)
    logging.debug(query_str)

    query_args = {"earliest_time": "1441618949.544",
                  "latest_time":   "1441618954.544"}

    response = splunk.get_summary(query_str, query_args, 5 )
    assert response == [{'host': 'sample1D', 'alarm_code': 'NOM_EVT_ECG_V_TACHY', 'bpm': '140.000000', 'alarm_source': 'NOM_ECG_V_P_C_CNT', 'spo2': '98.850000'}]

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
    query_str = SplunkEventStore.perseus_rule_to_query_str(rule)
    logging.debug(query_str)

    query_args = {"earliest_time": "1441618275.64",
                  "latest_time":   "1441618285.64"}

    response = splunk.get_summary(query_str, query_args, 5 )
    assert response == [{'host': 'sample1F', 'alarm_code': 'NOM_EVT_ECG_ASYSTOLE', 'bpm': '0.000000', 'alarm_source': 'NOM_ECG_CARD_BEAT_RATE', 'spo2': '8388607.000000'}]

    query_args = {"earliest_time": "2015-09-07T13:31:20.640+04:00",
                  "latest_time":   "2015-09-07T13:32:20.640+04:00"}

    response = splunk.get_summary(query_str, query_args, 5 )
    assert response == [{'host': 'sample1F', 'alarm_code': 'NOM_EVT_ECG_ASYSTOLE', 'bpm': '0.000000', 'alarm_source': 'NOM_ECG_CARD_BEAT_RATE', 'spo2': '8388607.000000'}]


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_splunk_event_store()
