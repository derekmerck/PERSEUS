"""
data['s1']['summary']['b0']['segments']['A1']['monitor']['HR-count']
"""

import logging
import yaml
import os
import splunklib.client as SplunkClient
import splunklib.results as SplunkResults
import datetime
from dateutil import parser
import pprint
import csv
import json

# Lookup credentials from either os.env or shadow.yaml
try:
    with file("shadow.yaml") as f:
        shadow_env = yaml.load(f)
    os.environ.update(shadow_env)
except IOError as e:
    print("Unable to open shadow.yaml file for additional environment vars") #Does not exist OR no read permissions

class Splunk:
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

DATA_DIR = "/Users/derek/Data/PPG"

def get_experimental_ppg():

    splunk = Splunk()

    # Get all subjects and dates
    query_str = "search index = ppg | stats earliest(_time) as datestr by host | " \
                "eval datestr = strftime(datestr, \"%Y-%m-%d\")"
    query_args = {}

    response = splunk.service.jobs.oneshot(query_str, **query_args)
    # Get the results and convert to array of dictionaries using the ResultsReader
    reader = SplunkResults.ResultsReader(response)
    subjects = {}
    for item in reader:
        logging.debug(dict(item))
        subject = item['host']
        date = item['datestr']
        subjects[subject] = {'date': date}

    subjects['s27']['date'] = '2016-08-11'  # Error in the data -- has same tag on earlier day
    logging.debug(subjects)

    for subject in ['s22', 's24', 's27']:
    # for subject, value in subjects.iteritems():

        value = subjects[subject]

        date = value['date']

        # Get window names and start times
        with open('{dir}/extraction segments + windows for s1-s30/{subject} segments + windows.csv'.format(dir=DATA_DIR, subject=subject)) as csvfile:
            reader = csv.reader(csvfile)
            r=[]
            for item in reader:
                r.append(item)

            window_names = r[0][1:]
            window_times = r[1][1:]
            window_times = [w.replace('.', ':') for w in window_times]

            windows = dict(zip(window_names, window_times))
            logging.debug(windows)

        # Segment offsets are constant
        segments = {
            "A1": {"start": 10, "duration": 20},
            "A2": {"start": 50, "duration": 10},
            "B1": {"start": 20, "duration": 10},
            "B2": {"start": 20, "duration": 10},
            "C":  {"start": 30, "duration": 30},
            "D":  {"start": 50, "duration": 10},
            "E":  {"start":  0, "duration": 60},
        }

        window_summaries = {}

        for window, time in windows.iteritems():

            query_str = "search index=ppg host={host} \"Heart Rate\"!=null \"Respiration Rate\"!=null | " \
                        "eval _time=if(isnotnull(host_time),strptime(host_time,\"%Y-%m-%dT%H:%M:%S.%f\"),_time) | " \
                        "stats " \
                            "count(\"Heart Rate\") as HR-count " \
                            "avg(\"Heart Rate\") as HR-mean " \
                            "stdev(\"Heart Rate\") as HR-std " \
                            "count(\"Respiration Rate\") as RR-count " \
                            "avg(\"Respiration Rate\") as RR-mean " \
                            "stdev(\"Respiration Rate\") as RR-std" \
                        .format(host=subject)

            query_str2 = "search index=ppg host={host} \"pulserate\"!=0 \"resprate\"!=0 | " \
                        "eval _time=if(isnotnull(host_time),strptime(host_time,\"%Y-%m-%dT%H:%M:%S.%f\"),_time) | " \
                        "stats " \
                            "count(pulserate) as HR-count " \
                            "avg(pulserate) as HR-mean " \
                            "stdev(pulserate) as HR-std " \
                            "count(resprate) as RR-count " \
                            "avg(resprate) as RR-mean " \
                            "stdev(resprate) as RR-std" \
                        .format(host=subject)

            logging.debug(query_str)
            logging.debug(query_str2)

            # Create a start and end time
            base = parser.parse("{date}T{time}.000".format(date=date, time=time))

            segment_summaries = {}

            for segment, values in segments.iteritems():

                start = base + datetime.timedelta(seconds=values['start'])
                end = start + datetime.timedelta(seconds=values['duration'])

                # THESE THAT A TIME RESTRICTED QUERY RETURNS NO LINES
                query_args = {"earliest_time": "{start_time}".format(start_time = start.isoformat()),
                              "latest_time":   "{end_time}".format(end_time = end.isoformat())}

                logging.debug(query_args)

                response = splunk.service.jobs.oneshot(query_str, **query_args)
                # Get the results and convert to array of dictionaries using the ResultsReader
                reader = SplunkResults.ResultsReader(response)
                r = []
                for item in reader:
                    r.append(dict(item))
                    logging.debug(dict(item))

                response = splunk.service.jobs.oneshot(query_str2, **query_args)
                # Get the results and convert to array of dictionaries using the ResultsReader
                reader = SplunkResults.ResultsReader(response)
                rr = []
                for item in reader:
                    rr.append(dict(item))
                    logging.debug(dict(item))

                S = {'times': query_args, 'monitor': r[0], 'vsc': rr[0]}

                segment_summaries[segment] = S

            window_summaries[window] = {'base time': base.isoformat(),
                                        'segments': segment_summaries}

        subjects[subject]['summary'] = window_summaries

    logging.debug( pprint.pformat(subjects) )

    # Save all data to file
    with open('data1.json', 'w') as outfile:
        json.dump(subjects, outfile, sort_keys=True, indent=4,
                  ensure_ascii=False)

    # Return all summary data in dictionary
    return subjects

def convert_ppg_data_to_csv():

    # Read in file
    with open("data1.json", 'r') as infile:
        data = json.load(infile)

    csv_text = ""

    for subject in data.keys():
        if 'summary' not in data[subject].keys(): continue
        for window in data[subject]['summary'].keys():
            for segment in data[subject]['summary'][window]['segments'].keys():

                monitor_data = data[subject]['summary'][window]['segments'][segment]['monitor']
                vsc_data = data[subject]['summary'][window]['segments'][segment]['vsc']

                # Construct this data line
                line="{sub},{win},{seg}," \
                     "{mon_HR_mean},{mon_HR_std},{mon_HR_count}," \
                     "{mon_RR_mean},{mon_RR_std},{mon_RR_count}," \
                     "{vsc_HR_mean},{vsc_HR_std},{vsc_HR_count}," \
                     "{vsc_RR_mean},{vsc_RR_std},{vsc_RR_count}," \
                    .format(
                        sub=subject,
                        win=window,
                        seg=segment,
                        mon_HR_mean=monitor_data.get('HR-mean', ""),
                        mon_HR_std=monitor_data.get('HR-std', ""),
                        mon_HR_count=monitor_data.get('HR-count', ""),
                        mon_RR_mean=monitor_data.get('RR-mean', ""),
                        mon_RR_std=monitor_data.get('RR-std', ""),
                        mon_RR_count=monitor_data.get('RR-count', ""),
                        vsc_HR_mean=vsc_data.get('HR-mean', ""),
                        vsc_HR_std=vsc_data.get('HR-std', ""),
                        vsc_HR_count=vsc_data.get('HR-count', ""),
                        vsc_RR_mean=vsc_data.get('RR-mean', ""),
                        vsc_RR_std=vsc_data.get('RR-std', ""),
                        vsc_RR_count=vsc_data.get('RR-count', "")
                    )
                csv_text += line + "\n"

    logging.debug(csv_text)
    with open("data1.csv", "w") as text_file:
        text_file.write(csv_text)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    # get_experimental_ppg()
    convert_ppg_data_to_csv()
