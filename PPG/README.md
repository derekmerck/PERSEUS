PPG Data Processing with Splunk
===============================

Data Import
----------------------

Remove any `*.txt` file extensions, and then rename all extension-less files to `*.json`:

```
$ rename 's/(\.txt$)//' * 
$ rename 's/(.*)/$1\.json/' *
```

I copied the data onto the Splunk container so I wouldn't have to upload them one at a time.

```
$ docker cp DATA_DIR splunk:/home/splunk/DATA_DIR
$ docker exec -it splunk /bin/bash
$$ sudo chmod splunk:splunk /home/splunk/DATA_DIR/*
```

Setup Splunk with a new data _type_ based on `_json` that expects a `timestamp` field for `_time`.  

Setup Splunk with a new data _source_ for the MP90 data in your target folder that extracts the host name with this regex:

`.*-(?<host>.*).json`

This will assign each subject to a different hostname, which is convenient for scripting.

Repeat for vcs data.

Setup Splunk with a new data _type_ based on `csv` that uses the regex `%m,%d,%Y,%H,%M,%S` for `TIME_FORMAT` AND `0000,` for `TIME_PREFIX`.

Copy the csv files over to the container and then make a data _source_ that assigns the host name with this regex:

`.*(?<host>s.*)\smod\.csv`

It looks like it may help to set both data sources to default to America/NY time as well (or whatever timezone the Splunk server thinks that it lives in).

.json files for 22, 24, and 27 are too big to parse in a monitored file, and need to be loaded individually.

You can run both as one-shot imports.  If it doesn't work, make your corrections, drop the index, rebuild the index, and disable and then re-enable the data source to re-import.

https://regex101.com is very useful for working out the regular expressions.


Graphing
---------------------- 

Create a Dashboard using a query something like this:
 
```
index=ppg host=$host$ (resprate!=0 pulserate!=0) OR ("Heart Rate"!=null "Respiration Rate"!=null) | eval _time=if(isnotnull(host_time),strptime(host_time,"%Y-%m-%dT%H:%M:%S.%f"),_time) | timechart span=10s avg("Heart Rate") as HR-mon avg(pulserate) as HR-ppg avg("Respiration Rate") as RR-mon avg(resprate) as RR-ppg
```

I assigned the subject token `$host$` in a type-in field as `s1`, `s2`, etc...