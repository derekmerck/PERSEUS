# DockerSplunk Up!

[Derek Merck](email:derek_merck@brown.edu)  

<https://github.com/derekmerck/PERSEUS/DockerSplunk>


## Overview

Sets up a Splunk instance, exposes ports 8000 and 8089, changes admin password, and creates a `perseus` index.

## Usage

Startup a PERSEUS index:

```bash
$ cd perseus/DockerSplunk
$ export SPLUNK_PWORD=passw0rd
$ docker-compose up
```

Load some sample data:

```bash
$ docker cp samples/x00-01-06232016b.json dockersplunk_splunk_1:/sample.json
$ docker exec dockersplunk_splunk_1 /opt/splunk/bin/splunk add oneshot "/sample.json" -sourcetype _json -index perseus -host sample1 -auth admin:${SPLUNK_PWORD}
```

For data files that don't have timestamp at the front of each message, you may need to manually change the timestamp extraction for \_json to look for the "timestamp" field _before_ importing the data.


## Acknowledgements

Uses docker container maintained by `outcoldman/splunk`