# PERSEUS
Push Electronic Relay for Smart Alarms for End User Situational Awareness

[Derek Merck](derek_merck@brown.edu)  
[Leo Kobayashi](lkobayashi@lifespan.org)  

See PERSEUS.py docstring for usage.

### Purpose:

To be discussed...


### Dependencies:

- [numpy](http://www.numpy.org) for calculations
- [matplotlib](http://matplotlib.org) for plotting
- [Pyro4](https://pythonhosted.org/Pyro4/) for python-to-python communication

The [Anaconda](http://continuum.io/downloads) scientific python distribution includes numpy and matplotlib, and it
works well for PERSEUS.  Pyro4 can be simply installed with `pip` or `easy_install`.

See the docstring for additional package information.


### Usage:


```bash
main$ python -m Pyro4.naming
main$ ./PERSEUS.py -p control0  -c config.yaml
main$ ./PERSEUS.py -p display0  -c config.yaml
remote$ ./PERSEUS.py -p listener0 -c config.yaml
```

Where config.yaml looks like this:

```yaml
---
# Settings

LOGGING_LEVEL: warning
ENABLE_SMS: False
SMS_USER: perseus_dispatch
# ... etc.

---
# Topology

control0:
  type: control
  location: Main station

display0:
  type: display
  location: Main station

listener0:
  type: listener
  location: Remote patient monitor
  alert_device: phone001

--
# Alert Devices

phone001:
  number: 4014445555
  carrier: ***REMOVED***

---
```

And the controller for a listener or display node is the _first_ control-type node listed (with subsequent controls being used as backup)

PERSEUS can also be used without a config file to stand-up a single listener or display node and connect to an existing controller:

```bash
main$ ./PERSEUS.py --pid display0  --type display --controller control0
remote$ ./PERSEUS.py --pid listener0 --type listener --controller control0 --alert_device phone001
```

A similar mechanism exists for setting up new control nodes, but this require more complex arguments.  See `PERSEUS.py --help` for details.

```bash
main$ python -m Pyro4.naming
main$ ./PERSEUS.py --pid control0  --type control --devices '{"phone001": {"number": 4014445555, "carrier": "***REMOVED***"}}'
```

### Notes

If the SMS messenger is using gmail as a relay, this requires _either_ turning off app security in gmail, or assigning a special password in the context of 2-step auth.


### Acknowledgements:

SMS Messenger class cribbed in part from <https://github.com/CrakeNotSnowman/Python_Message>


### License:

To be determined ...

