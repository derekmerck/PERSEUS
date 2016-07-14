# PERSEUS Listener
Push Electronic Relay for Smart Alarms for End User Situational Awareness

[Derek Merck](email:derek_merck@brown.edu)  
[Leo Kobayashi](email:lkobayashi@lifespan.org)  

<https://github.com/derekmerck/PERSEUS>


## Overview

Python interface for Philips Intellivue vital sign telemetry for use with PERSEUS

## Dependencies

- Python 2.7.10+
- [PyYAML](http://pyyaml.org) for configuration info
- [pyserial](https://github.com/pyserial/pyserial) for RS232 serial connection protocol
- [numpy](http://www.numpy.org) for array math functions
- [splunk-sdk](http://dev.splunk.com/python) (_optional for event routing_)
- [scipy](http://www.scipy.org) (_optional for quality of signal post-processing_)
- [matplotlib](http://www.matplotlib.org) (_optional for simple GUI display_)


## Setup

This code has fairly minimal hardware requirements, and appears to be operating system agnostic.  The RIH pilot setup used small form-factor Win10 boxes on wired ethernet connections, and it has also been tested on Mac laptops running OSX 10.11.  In both cases, the RS232 serial connections were mediated by a USB-to-serial dongle which required its own drivers.


## Usage

Generate a pair of test wave forms and display the result with matplotlib:

```bash
$ python TelemetryStream.py --values Pleth 32 ECG 128 --gui SimpleStripchart
```

Connect to a Philips Intelliviue monitor via a USB-to-serial converter and route the output to a splunk index using splunk server credentials from the user environment.

```bash
$ python PhilipsTelemetryStream.py --values Pleth 128 ECG 256 --device /dev/cu.usbserial --splunk perseus
```

### Command line arguments

```bash
$ python TelemetryStream.py --help
usage: TelemetryStream.py [-h] [-V] [-b BINARY] [-f FILE] [-s SPLUNK] [-g GUI]
                          [-p PORT] [--values VALUES [VALUES ...]]

Monitor decoder for PERSEUS (Push Electronic Relay for Smart Alarms for End
User Situational Awareness)

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -b BINARY, --binary BINARY
                        Name of an hdf5 file for binary logging
  -f FILE, --file FILE  Name of a text file for event logging
  -s SPLUNK, --splunk SPLUNK
                        Name of a Splunk index for event logging
  -g GUI, --gui GUI     Display a graphic user interface, e.g.,
                        'SimpleStripchart'
  -p PORT, --port PORT  Device port
  --values VALUES [VALUES ...]
                        List of paired value names and frequencies to monitor,
                        e.g. 'ecg 100 pleth 64'
```

## Output

Each message is condensed into a compact `json` format and can be routed to the console, a text file, or a log server such as [Splunk](http://www.splunk.com).

### Sample Output Format

```json
{  
   "timestamp":"2016-03-10 07:41:16.594432",
   "ecg_samples":[  
      -0.010472588789229728,
      0.002685061088021719,
      0.015842246110379692,
      0.028996926740417938,
      0.042146348848978395,
      0.055288474312932885,
      0.06842102788373682,
      0.08154173596999278,
      0.0946485643793299,
      0.10773876900116826,
      0.12081032120045625,
      0.1338609579467428,
      0.1468886556630582,
      0.1598906868060168,
      0.17286503665393346,
      0.18580945900464788,
      0.19872171283723883,
      0.21159979571993354,
      0.2244410114334496,
      0.23724337048820018
   ],
   "pleth_samples":[  
      -0.9999451609383645,
      -0.9999963952169796,
      -0.999874503744434,
      -0.9995795007099789,
      -0.9991114478769124,
      -0.9984704225004104,
      -0.997656535558873,
      -0.9966699279575962,
      -0.9955107479384298,
      -0.9941792381930499,
      -0.9926756097998191,
      -0.9910001230764709,
      -0.989153033072992,
      -0.9871347265053034,
      -0.984945520880538,
      -0.98258579520793,
      -0.9800559580182318,
      -0.977356396843691,
      -0.9744876768778198,
      -0.9714502473927311
   ],
   "alarm_source":null,
   "alarm_type":null,
   "spo2":95,
   "bpm":80,
   "qos":false
}
```

### Timestamping

The `timestamp` field is shuffled to the front of the dictionary so that event parsers can easily identify it.  (Although technically `JSON` keys can be read in any order, Splunk will not extract it automatically if it is presented at the end of these large messages.)

Each message has a single timestamp and uses the monitor reported time by default.  If the `--host_time` flag is present, the time reported by the host computer will be used instead, which can be useful when syncing multiple data streams.


## Organization

The main interface to this package is the "TelemetryStream" class, which is sub-classed by the PhilipsTelemetryStream module.

The PhilipsTelemetryStream module opens an RS232 connection, passes it to the IntellivueDecoder module, initiates an extended polling data transfer (required for wave data), and passes the decoded messages returned to the IntellivueDistiller module.

Each update yields a timestamped dictionary of alarm, numerics, and wave data.  Wave data is returned at 0.25sec intervals, which determines the polling frequency.  The wave data is stored in an internal sample buffer with a default duration of 7-9 seconds.  This buffer can be accessed for signal post-processing and annotation.

See the _Intellivue Programmers Guide_ for details of the protocol.


## Failure Recovery

The code can be modified to run in `blocking` or `non-blocking` modes.  When `blocking`, a failure of the serial device (the monitor is shut off) throws an exception and the listener blocks until it can re-open the serial device (the monitor is turned back on).  In `non-blocking` mode, the code simply shuts down gracefully.


## Signal Post-Processing and Quality of Signal

Post-processing functions that use the current message, as well as a few seconds of sample history, can easily be included.

The default QoS code was adapted from Xiao Hu, PhD's MATLAB code for waveform quality checks and follows the algorithm described in:

> Zong, W., T. Heldt, G. B. Moody, and R. G. Mark. 2003. “An Open-Source Algorithm to Detect 
  Onset of Arterial Blood Pressure Pulses.” In Computers in Cardiology, 2003, 259–62. 
  doi:10.1109/CIC.2003.1291140.
  
According to this paper, the same method is also implemented in the [PhysioToolkit](http://www.physionet.org)


## PERSEUS on Embedded Devices

### Raspberry Pi

Testing is underway using [Raspberry Pi](https://www.raspberrypi.org) boards as listener.  This would be an extremely inexpensive solution for retrofitting a large number of older, non-networked monitors with Listeners.

[Raspbian](https://www.raspbian.org) requires a little bit of work to get Python 2.7.9+ and the dependencies installed.

```bash
$ sudo apt-get update && sudo apt-get upgrade
$ sudo pip install virtualenv virtualenvwrapper
$ export WORKON_HOME=envs                            # Put this in .bash_profile
$ source /usr/local/bin/virtualenvwrapper.sh         # Put this in .bash_profile
$ sudo apt-get install python-dev python-numpy python-scipy python-matplotlib  # global installations
$ mkvirtualenv perseus --system-site-packages
$ workon perseus
(perseus)$ pip install pyyaml pyserial splunk-sdk python-dateutil requests twilio
(perseus)$ mkdir perseus
(perseus)$ cd perseus/
(perseus)$ git clone https://github.com/derekmerck/PERSEUS.git
``` 

The standard usb-to-serial converters work with Raspberrian's default drivers.  It is also possible to build RS232 connectors for the GPIO header using this [expansion card](http://www.amazon.com/dp/B0088SNIOQ).  Using an rPi3 with a serial-to-usb dongle, connect to `--port /dev/ttyUSB0`, for a direct connection from the GPIO header, connect to `--port /dev/ttyS0`.  Using the GPIO headers, you have to turn off the kernel console from the Desktop. 

### CHIP

We have also tested this with [C.H.I.P.](https://getchip.com).  CHIP also runs Debian, so setup follows the same procedure described above, although you need to install `pip` and `git` as well.

```
$ curl https://bootstrap.pypa.io/ez_setup.py -o - | sudo python
$ sudo easy_install pip
$ sudo apt-get install git
```

PERSEUS runs in test mode, but we have not been able to get the USB-to-serial adaper to work (CHIP wants to be a gadget not a host, I think) nor the GPIO pins.  May need to disable the console to free up the UART <https://bbs.nextthing.co/t/second-serial-port/4163>.


## Acknowledgements

The Intellivue Decoder portion of this package was forked from the RIH pyMIND package (Multimodal Integration of Neural Data; previously known as NeuroLogic) developed by [Agrawal](mailto:uagrawal61@gmail.com), [Oyalowo](mailto:adewole_oyalowo@brown.edu), Asaad, and others under the MIT License provided below.

See <https://bitbucket.org/asaadneurolab/pymind> for documentation of the pyMIND project.

Contributions to the Intellivue Decoder by the current project (PERSEUS) include backporting to Python 2.7 and improving overall system robustness (e.g. handling when a connection is broken). PERSEUS is also available under a MIT License (see PERSEUS/README.md).

pyMIND: Multimodal Integration of Neural Data

Copyright (c) 2015-2016, Uday Agrawal, Adewole Oyalowo, Asaad Lab

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
