# ![logo](images/perseus_logo_sm.png) PERSEUS
Push Electronic Relay for Smart Alarms for End User Situational Awareness

[Derek Merck](email:derek_merck@brown.edu)  
[Leo Kobayashi](email:lkobayashi@lifespan.org)  

<https://github.com/derekmerck/PERSEUS>


## Overview

_To be discussed by Leo._

Original test site is at [Rhode Island Hospital](http://www.rhodeislandhospital.org) Emergency Department.


### Dependencies

General:
- Python 2.7
- [PyYAML](http://pyyaml.org) for configuration info
- [splunk-sdk](http://dev.splunk.com/python) (optional for event routing)

For Dispatch:
- [Twilio API](https://github.com/twilio/twilio-python) (optional for alert routing)

For Listener:
- pyserial for RS232 serial connection protocol
- numpy for array math functions
- scipy (optional for quality of signal function)
- matplotlib (optional for simple GUI display)


## Setup

PERSEUS Dispatch has three components:

1. A set of **client** systems running the PERSEUS Listener or other decoder for bedside monitors.
2. A central **event store**, such as [Splunk][] or an open-source "ELK" stack ([Elastic][], [Logstash][], and Kibana).
3. A central **dispatch server** running the PERSEUS Dispatch daemon

In testing, the event and dispatch server are separate components running on the same central machine.

### General Setup

[Anaconda]() simplifies cross-platform installation of the Python binary library dependencies required for the client systems.  Pip can be used for any pure-Python packages.


### Client Setup

Setup each client with a separate host name that will be used in the zone descriptions.

PERSEUS Listener bedside clients for Philips Intellivue monitors can be setup quickly by installing the Anaconda Python distribution as above, and using pip to install the latest PERSEUS scripts.

```bash
$ conda update conda
$ conda install numpy scipy matplotlib
$ pip install pyserial pyyaml splunk-sdk
$ pip install git+https://github.com/derekmerck/PERSEUS
$ python -m perseus listener --values Pleth 128 ECG 256 --port /dev/cu.usbserial --splunk perseus
```

See the [TelemetryStream README](TelemetryStream/README.md) for more details on how to setup a PERSEUS Listener client with a simple GUI and using Raspberry Pi hardware.

See the [TelemetryLogs README](TelemetryLogger/README.md) for details on how to setup a client system with CWRU's stand alone decoder and a log shipper.


### PERSEUS Dispatch Setup

Install PERSEUS Dispatch and dependencies on the central server.

```bash
$ pip install pyyaml splunk-sdk twilio
$ pip install git+https://github.com/derekmerck/PERSEUS
```

Modify the example `config.yaml` file to represent the local rules, zone topology, and alert roles.

Credentials for the event store, any email relays, [Twilio][] auth tokens, and [Slack][] webhook urls can be provided as environment variables or using a `shadow.yaml` file.  Both Twilio and Slack provide free trial services.

Once the event store (Splunk, for example) is setup and the clients are running, Dispatch can be started from the command line:

```bash
$ python -m perseus dispatch --config my_config.yaml
```

Future work includes developing a fabric- or Ansible-based system to deploy and bring up the entire PERSEUS network automatically.


## Security

### Using Gmail for Email-SMS Alerts

Using gmail as an SMS relay requires either turning off app security in gmail, or assigning a unique relay password in the context of 2-step auth.


## Code Organization Overview

![Network organization](images/perseus31_overview.png)


## Acknowledgements

- Initial development funded through a healthcare quality improvement award from the AHRQ
- The Intellivue Decoder portion of this package was forked from the RIH NeuroLogic package developed by [Agrawal](mailto:uagrawal61@gmail.com), [Oyalowo](mailto:adewole_oyalowo@brown.edu), Asaad, and others.  See <https://bitbucket.org/uagrawal61/neurologic> for documentation of the NeuroLogic project.
- The default QoS code was adapted from Xiao Hu, PhD's MATLAB code for waveform quality checks (see [TelemetryStream README](TelemetryStream/README.md) for reference).
- EmailSMSMessenger class cribbed in part from <https://github.com/CrakeNotSnowman/Python_Message>
- Splunk generously provided a _gratis_ academic license for their product
- Indebted to discussion of pip at <https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/>
- SimpleDisplay in version 0.2 based on matplotlib's [strip_chart example](http://matplotlib.org/1.4.0/examples/animation/strip_chart_demo.html)


## License

[MIT](http://opensource.org/licenses/mit-license.html)


[Splunk]: http://www.splunk.com
[Slack]: http://www.slack.com
[Twilio]: http://www.twilio.com
[Fluentd]: http://www.fluentd.org
[Logstash]: https://www.elastic.co/products/logstash
[Elastic]: https://www.elastic.co/products/elasticsearch

