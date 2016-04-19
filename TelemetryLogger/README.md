# ![logo](images/perseus_logo_sm.png) PERSEUS
Push Electronic Relay for Smart Alarms for End User Situational Awareness

[Derek Merck](email:derek_merck@brown.edu)  
[Leo Kobayashi](email:lkobayashi@lifespan.org)  

<https://github.com/derekmerck/PERSEUS>


## Configuring a Stand Alone Decoder with a Splunk Log Shipper

It is also possible to use any stand-alone monitor decoder, such as the one developed by CWRU.  The CWRU stack requires a separate install of a quality of signal post-processor and appropriate log forwarder for your choice of log server.  The log forwarder should ship alarms, numerics, and waveform quality logs to the log server.  

```bash
$ splunk add monitor C:\Patient\*numeric*.txt -sourcetype PERSEUS-Numerics -index perseus
$ splunk add monitor C:\Patient\*alarm*.txt -sourcetype PERSEUS-Alarms -index perseus
$ splunk list monitor
```

(Run `cmd.exe` as Admin on Windows)

This adds the following stanzas to `$SPLUNK_HOME\etc\apps\search\local\inputs.conf`.  The `InitCrcLength` key needs to be edited in directly (and possibly the `crcSalt` key) to improve recognition for log rotation.

```ini
[monitor://C:\Patients\*alarms*.txt]
disabled = false
sourcetype = PERSEUS-Alarms
index = perseus
initCrcLength = 1024
crcSalt = <SOURCE>

[monitor://C:\Patients\*numerics*.txt]
disabled = false
sourcetype = PERSEUS-Numerics
index = perseus
initCrcLength = 1024
crcSalt = <SOURCE>
```

This seems to work with the Splunk6+, but if pattern matching gives you a hard time, see <https://answers.splunk.com/answers/58665/inputs-conf-with-wildcards.html> and <https://answers.splunk.com/answers/2775/regexs-and-windows-paths-in-inputs-conf-and-props-conf.html>

Add `splunkd` to in and out firewalls (or ports 8000, 8089, 9997, 8080 and 514)
Restart the SplunkForwarder service



## Configuring a Splunk Event Server

Splunk is free for up to 500MB/day, which is probably enough for central telemetry on about 25 beds.  

Configure settings -> indexes -> add index -> add `perseus`

Configure settings -> forwarding and receiving -> configure receiving -> add port 9997

To configure Splunk to ingest CWRU log files, you must add source types for PERSEUS-Alarms, PERSEUS-Numerics.  You can do this through the web UI or directly by editing `$SPLUNK_HOME/etc/apps/search/local/props.conf`.
 
```ini
[PERSEUS-Alarms]
DATETIME_CONFIG = 
NO_BINARY_CHECK = true
category = Application
pulldown_type = 1
BREAK_ONLY_BEFORE = ^-*$
TIME_FORMAT = %H:%M:%S:%N
TIME_PREFIX = Time:
description = PERSEUS alarms log file
disabled = false

[PERSEUS-Numeric]
BREAK_ONLY_BEFORE = ^Year
DATETIME_CONFIG = 
MAX_TIMESTAMP_LOOKAHEAD = 256
NO_BINARY_CHECK = true
TIME_FORMAT = %Y %m %d %H %M %S %q
TIME_PREFIX = =+\n
category = Application
disabled = false
pulldown_type = true
```

Add field extractions (reg-exs) for PERSEUS-Alarms, PERSEUS-Numerics.  You can do this through the UI or directly, by editing `$SPLUNK_HOME/users/admin/search/local/props.conf`:
 
 ```ini
[PERSEUS-Alarms]
EXTRACT-perseus_alarms = Time: (?P<time>.*)\nDate: (?P<date>.*)\nAlert_source: (?P<alert_src>.*)\nAlert_code: (?P<alert_code>.*)\nAlert_type: (?P<alert_type>.*)\nAlert_state: (?P<alert_state>.*)\nAlert_flags: (?P<alert_flags>.*)\nAlert_message: (?P<alert_msg>.*)

[PERSEUS-Numerics]
EXTRACT-perseus_numerics = NOM_PULS_OXIM_PERF_REL.*?(?P<o2p_1>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_2>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_3>\d+\.\d+)\nNOM_ECG_CARD_BEAT_RATE.*?(?P<bpm_1>\d+\.\d+)\nNOM_ECG_CARD_BEAT_RATE.*?(?P<bpm_2>\d+\.\d+)\nNOM_ECG_V_P_C_CNT.*?(?P<ecgvpc>\d+\.\d+)\nNOM_PULS_OXIM_SAT_O2.*?(?P<spo2>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_4>\d+\.\d+)
```

Similar regular expressions should work with other log forwarders, such as [Logstash][] or [fluentd][], as well.

Add `splunkd` to in and out firewalls (or ports 8000, 8089, 9997, 8080 and 514)

If you want to be able to run Dispatch's event server unit tests, manually import the sample data sets as flat files using the appropriate data type templates.

## Troubleshooting

The Intel iCLS install can wreck havoc with the Splunk startup process.  If you get `python.exe` errors, try removing it from the system `%PATH%` variable.  See <http://stackoverflow.com/questions/14552348/runtime-error-r6034-in-embedded-python-application>2