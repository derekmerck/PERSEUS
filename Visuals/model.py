from __future__ import division
import logging
import pandas as pd

logger = logging.getLogger()
# logger.disabled = True

class Alarms(object):

    def __init__(self,alarms_csv):

        self.alarms = None
        self.alarms_csv = alarms_csv
        self.number_of_alarms = None
        self.current_alarm_number = None

    def load_alarms(self):
        alarms_csv = self.alarms_csv
        alarms_df = pd.read_csv(alarms_csv,parse_dates=[0])
        alarms_df.set_index("_time", inplace=True)
        alarms_df.tz_localize("UTC",copy=False).tz_convert('Etc/GMT+4',copy=False)
        alarms_df.sort_index(inplace=True)

        self.desc = alarms_df.values
        self.alarms = alarms_df.index.to_pydatetime()
        self.number_of_alarms = self.alarms.size
        self.current_alarm_number = 0

class Data(object):

    def __init__(self,physio_csv):
        self.physio_df = None
        self.physio_csv = physio_csv
        self.load_then_display = None

    def load_physio_data(self):

        # Note: Timestamps are read in and kept as object dtype
        physio_csv = self.physio_csv
        physio_df = pd.read_json(physio_csv, lines=True)
        physio_df.set_index("timestamp",inplace=True)
        physio_df.tz_localize('Etc/GMT+4',copy=False)
        physio_df.sort_index(inplace=True)

        self.physio_df = physio_df

    def create_single_data_streams(self, load_then_display=True):

        self.pleth = self.physio_df['Pleth'].dropna()
        self.ecg = self.physio_df['ECG'].dropna()
        self.hr = self.physio_df['Heart Rate'].apply(pd.to_numeric,errors='coerce').dropna()
        self.spo2 = self.physio_df['SpO2'].apply(pd.to_numeric,errors='coerce').dropna()
        qos = self.physio_df['qos'].apply(pd.to_numeric,errors='coerce').dropna()
        self.qos = qos[~qos.index.duplicated(keep='first')].dropna()

        if load_then_display:
            # Uncomment for long load time but short page time
            self.nibp = self.physio_df['Non-invasive Blood Pressure'].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna()
            self.load_then_display = True

        else:
            ## Uncomment for short load time but long page time
            self.nibp = self.physio_df['Non-invasive Blood Pressure']
            self.load_then_display = False


        del self.physio_df
