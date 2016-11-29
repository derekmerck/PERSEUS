"""
Should support a range of event storage types.  Splunk is free for small workloads and easy
to setup, so we focused on that.  We could also easily support an ELK stack or a custom Python
shipper/indexer (as I wrote in the previous Perseus v0.2).
"""

import logging
import yaml
import os
import splunklib.client as SplunkClient
import splunklib.results as SplunkResults

# Lookup credentials from either os.env or shadow.yaml
try:
    with file("shadow.yaml") as f:
        shadow_env = yaml.load(f)
    os.environ.update(shadow_env)
except IOError as e:
    print("Unable to open shadow.yaml file for additional environment vars") #Does not exist OR no read permissions


class EventStore(object):

    # Returns a table of fields from matching events ordered by host name
    # time_span refers to the duration of each row of the table
    # Start and stop time for the entire table should be set in the query_args dictionary
    def get_summary(self, host, rule, time_span, query_args):
        raise NotImplementedError


class SplunkEventStore(EventStore):

    # Mapping between cardinal field names (keys), and splunk instance field names (values)
    # in case the fields aren't assigned properly in a test environment
    field_names = { 'bpm': "Heart Rate",
                    'spo2': "SpO2",
                    'alarm_code': "alarms.{}.code",
                    'alarm_source': "alarms.{}.source"}

    def __init__(self, **kwargs):

        # Create a Service instance and log in
        self.service = SplunkClient.connect(
            host=os.environ['SPLUNK_HOST'],
            port=os.environ['SPLUNK_PORT'],
            username=os.environ['SPLUNK_USER'],
            password=os.environ['SPLUNK_PWORD'])

        self.index = kwargs.get('index', "perseus")

        # Verify login
        if not self.service.apps:
            raise IOError

    @classmethod
    def perseus_rule_to_query_str(cls, index, host, rule, time_span=30):
        # Accept a rule, return a conjunctive query string

        def item_to_query_element(condition, value):
            # Accept a condition within a log and return its query string
            # bpm: [GT,100] -> bpm>100
            # alert_code: [MATCH, ERROR*, MY_CODE] -> match(alert_code, "ERROR*|MY_CODE")

            def get_op(op_str):
                if op_str == "GT": return ">"
                elif op_str == "TGT": return ">"
                elif op_str == "GTE": return ">="
                elif op_str == "LT": return "<"
                elif op_str == "TLT": return "<"
                elif op_str == "LTE": return "<="
                elif op_str == "EQ": return "="
                elif op_str == "NEQ": return "!="
                elif op_str == "MATCH": return "match"
                raise NotImplementedError

            def get_regex(values):
                if type(values) is list:
                    return "|".join(values)
                else:
                    return values

            op = get_op(value[0])
            if op == "match":
                qe = "{op}({cond}, \"{regex}\")".format(op=op, cond=condition, regex=get_regex(value[1:]))
            else:
                # For "trending lt" or "trending gt" conditions, we want to consult the "predicted_X" variable
                if value[0] == "TLT":
                    condition = "pred_" + condition
                elif value[0] == "TGT":
                    condition = "pred_" + condition
                qe = "{cond}{op}{val}".format(cond=condition, op=op, val=value[1])

            return qe

        qitems = []
        if rule:
            for key, value in rule.iteritems():
                qitems.append(item_to_query_element(key, value))

        q = "search index={index} host={host} | "\
            "eval alarm_sources=\"\" | "\
            "foreach alarms.*.source " \
                "[eval alarm_sources='<<FIELD>>'+\",\"+alarm_sources] | " \
            "makemv delim=\",\" alarm_sources | " \
            "eval alarm_codes=\"\" | " \
            "foreach alarms.*.code " \
                "[eval alarm_codes='<<FIELD>>'+\",\"+alarm_codes] | " \
            "makemv delim=\",\" alarm_codes | " \
            "timechart span={time_span}s " \
                "avg(\"{bpm_fn}\") as bpm, "\
                "avg(\"{spo2_fn}\") as spo2, " \
                "values(alarm_codes) as alarm_code, " \
                "values(alarm_sources) as alarm_source | " \
            "predict bpm as pred_bpm future_timespan=4 | " \
            "predict spo2 as pred_spo2 future_timespan=4 | " \
            "where {filter}" \
            .format( index=index,
                     host=host,
                     time_span=time_span,
                     bpm_fn="Heart Rate",
                     spo2_fn="SpO2",
                     filter=" AND ".join(qitems) )

        return q

    def get_summary(self, host, rule, time_span=30, query_args={}):

        query_str = self.perseus_rule_to_query_str(self.index, host, rule, time_span)
        response = self.service.jobs.oneshot(query_str, **query_args)
        # Get the results and convert to array of dictionaries using the ResultsReader
        reader = SplunkResults.ResultsReader(response)
        r = []
        # Should only have 1 item, b/c the timechart is collapsed w max's
        for item in reader:
            r.append(dict(item))
            # logging.debug(dict(item))
        return r


def test_splunk_event_store():

    index="ppg"
    host = "s20"

    splunk = SplunkEventStore(index=index)

    # TEST A SIMPLE QUERY
    rule_str = """
    bpm: [GT, 0]
    """
    rule = yaml.load(rule_str)
    query_str = SplunkEventStore.perseus_rule_to_query_str(index, host, rule)
    logging.debug(query_str)

    assert query_str == '''search index=ppg host=s20 | eval alarm_sources="" | foreach alarms.*.source [eval alarm_sources='<<FIELD>>'+","+alarm_sources] | makemv delim="," alarm_sources | eval alarm_codes="" | foreach alarms.*.code [eval alarm_codes='<<FIELD>>'+","+alarm_codes] | makemv delim="," alarm_codes | timechart span=30s avg("Heart Rate") as bpm, avg("SpO2") as spo2, values(alarm_codes) as alarm_code, values(alarm_sources) as alarm_source | predict bpm as pred_bpm future_timespan=4 | predict spo2 as pred_spo2 future_timespan=4 | where bpm>0'''

    # TEST THAT VALID QUERY RETURNS ALL LINES
    response = splunk.get_summary(host, rule, 30)
    logging.debug(response)
    logging.debug(len(response))
    assert len(response) == 42

    # TEST THAT A TIME RESTRICTED QUERY RETURNS FEWER LINES
    query_args = {"earliest_time": "2016-07-28T11:30:00.000-4:00",
                  "latest_time":   "2016-07-28T11:50:00.000-4:00"}

    response = splunk.get_summary(host, rule, 30, query_args)
    logging.debug(response)
    logging.debug(len(response))
    assert len(response) == 29

    # TEST A COMPLEX QUERY
    rule_str = """
    pred_bpm: [GT, 100]
    """
    rule = yaml.load(rule_str)
    query_str = SplunkEventStore.perseus_rule_to_query_str(index, host, rule)
    logging.debug(query_str)

    response = splunk.get_summary(host, rule, 30, query_args)
    logging.debug(response)
    logging.debug(len(response))
    assert len(response) == 15

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_splunk_event_store()
