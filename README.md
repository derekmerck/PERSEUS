# ![logo](images/perseus_logo_sm.png) PERSEUS
Push Electronic Relay for Smart Alarms for End User Situational Awareness

[Derek Merck](email:derek_merck@brown.edu)  
[Leo Kobayashi](email:lkobayashi@lifespan.org)  

<https://github.com/derekmerck/PERSEUS>


## Overview

_To be discussed by Leo._

Original test site is at [Rhode Island Hospital](http://www.rhodeislandhospital.org) Emergency Department.


### Dependencies

- Python 2.7
- [PyYAML](http://pyyaml.org) for configuration info
- [Splunk API](http://dev.splunk.com/python) (optional for event routing)
- [Twilio API](https://github.com/twilio/twilio-python) (optional for alert routing)


## Installation

PERSEUS has three basic components:
 
1. A set of client systems equipped with decoders and waveform analyzers for bedside monitors.
2. A central log server, such as such as [Splunk][] or an open-source "ELK" stack ([Elastic][], [Logstash][], and Kibana).
3. A central server with the PERSEUS Dispatch daemon

In testing, the log server and dispatch server are separate components running on the same central machine.


### Client Setup

Install the monitor parser and waveform analyzer on each client machine.  

Install an appropriate log forwarder for your choice of log server.  The log forwarder should ship alarms, numerics, and waveform quality logs to the log server.  Setup each client with a separate host name that will be used in the zone descriptions.


### Log Server Setup

Install and configure a central log server.  Splunk is free for up to 500MB/day, which is probably enough for central telemetry on about 250 beds.  

Templates for Splunk data types for alarm, numeric, and waveform logs are provided.
 
In `/opt/splunk/etc/apps/search/local/props.conf` and 
 
```
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
  
In `/opt/splunk/users/admin/search/local/props.conf`:
 
 ```
[PERSEUS-Alarms]
EXTRACT-alert_source,alert_code,alert_type,alert_state,alert_flags,alert_msg = Alert_source: (?<alert_source>.+)Alert_code: (?P<alert_code>.+)Alert_type: (?P<alert_type>.+)Alert_state: (?P<alert_state>.+)Alert_flags: (?P<alert_flags>.+)Alert_message: (?P<alert_msg>.+)
EXTRACT-time,date,alert_src,alert_code,alert_type,alert_state,alert_flags,alert_msg = Time: (?P<time>.*)\nDate: (?P<date>.*)\nAlert_source: (?P<alert_src>.*)\nAlert_code: (?P<alert_code>.*)\nAlert_type: (?P<alert_type>.*)\nAlert_state: (?P<alert_state>.*)\nAlert_flags: (?P<alert_flags>.*)\nAlert_message: (?P<alert_msg>.*)

[PERSEUS-Numeric]
EXTRACT-perseus_numerics = NOM_PULS_OXIM_PERF_REL.*?(?P<o2p_1>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_2>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_3>\d+\.\d+)\nNOM_ECG_CARD_BEAT_RATE.*?(?P<bpm_1>\d+\.\d+)\nNOM_ECG_CARD_BEAT_RATE.*?(?P<bpm_2>\d+\.\d+)\nNOM_ECG_V_P_C_CNT.*?(?P<ecgvpc>\d+\.\d+)\nNOM_PULS_OXIM_SAT_O2.*?(?P<spo2>\d+\.\d+)\nNOM_PULS_OXIM_PERF_REL.*?(?P<o2p_4>\d+\.\d+)
```

The same regular expressions should work with other log forwarders, such as [Logstash][] or [fluentd][], as well.

If you want to be able to run Dispatch's event server unit tests, manually import the sample data sets as flat files using the appropriate data type templates.


### PERSEUS Dispatch Setup

Install PERSEUS Dispatch and dependencies on the central server.

`$ pip install git+https://github.com/derekmerck/PERSEUS`

Modify the config.yaml file to represent the local rules, zone topology, and alert roles.


### PERSEUS Dispatch Configuration

`config.yaml` includes three required keys:  _rules_, _zones_, and _roles_.  See the example provided.

Credentials for the log server, any email relays, [Twilio][] auth tokens, and [Slack][] webhook urls must be provided as environment variables or using a `shadow.yaml` file.  Both Twilio and Slack provide free trial services.


## Usage

To bring up PERSEUS manually:

1. Startup your log server
2. Startup all client machine monitoring processes
3. Startup PERSEUS Dispatch

```bash
$ ./PERSEUS.py start
```

Future work includes developing a fabric or Ansible based system to bringing up the entire PERSEUS network automatically.


## Security

### Using Gmail for Email-SMS Alerts

Using gmail as an SMS relay requires either turning off app security in gmail, or assigning a unique relay password in the context of 2-step auth.


## Code Organization Overview

![Network organization](images/perseus3_overview.png)


## Acknowledgements

- Initial development funded through a healthcare quality improvement award from the AHRQ
- EmailSMSMessenger class cribbed in part from <https://github.com/CrakeNotSnowman/Python_Message>
- Splunk generously provided a _gratis_ academic license for their product
- Indebted to discussion of pip at <https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/>
- SimpleDisplay based on matplotlib's [strip_chart example](http://matplotlib.org/1.4.0/examples/animation/strip_chart_demo.html)


## License

[MIT](http://opensource.org/licenses/mit-license.html)



[Splunk]: http://www.splunk.com
[Slack]: http://www.slack.com
[Twilio]: http://www.twilio.com
[Fluentd]: http://www.fluentd.org
[Logstash]: https://www.elastic.co/products/logstash
[Elastic]: https://www.elastic.co/products/elasticsearch

