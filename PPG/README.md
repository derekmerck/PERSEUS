PPG Data Processing with Splunk
===============================

Data Import
----------------------

Remove any `*.txt` file extensions, and then rename all extension-less files to `*.json`:

```
$ rename 's/(\.txt$)//' * 
$ rename 's/(.*)/$1\.json/' *
```

Setup Splunk with a new data type based on `_json` that expects a `timestamp` field for `_time`.

I copied the data onto the Splunk container so I wouldn't have to upload them one at a time.

```
$ docker cp DATA_DIR splunk:/home/splunk/DATA_DIR
$ docker exec -it splunk /bin/bash
$$ sudo chmod splunk:splunk /home/splunk/DATA_DIR/*
```

Setup Splunk with a new data source in your target folder that extracts the host name with this regex:

`.*-(?<host>.*).json`

This will assign each subject to a different hostname, which is convenient for scripting.

Repeat for vcs data.

Setup Splunk with a new data type based on `csv` that uses the rex `%m,%d,%Y,%H,%M,%S` for `TIME_FORMAT` AND `0000,` for `TIME_PREFIX`.

Copy the csv files over and then make a data source that assigns the host name with this regex:

`.*(?<host>s.*)\smod\.csv`

You can run both as a one-shot import.  If it doesn't work, make your corrections, drop the index, rebuild the index, and disable and then re-enable the data source to reimport.

https://regex101.com is very useful for working out the regular expressions.


Graphing
---------------------- 

Create a dashboard something like this:
 
```xml
<form>
  <label>PPG Graph</label>
  <fieldset submitButton="false">
    <input type="text" token="host">
      <label>Subject</label>
    </input>
  </fieldset>
  <row>
    <panel>
      <chart>
        <title>VSC Agreement for $host$</title>
        <search>
          <query>index=ppg host=$host$ | timechart span=10s avg("Heart Rate") avg("pulserate") avg("Respiration Rate") avg("resprate")</query>
          <earliest>0</earliest>
          <latest></latest>
        </search>
        <option name="charting.chart">line</option>
        <option name="charting.axisLabelsX.majorLabelStyle.overflowMode">ellipsisNone</option>
        <option name="charting.axisLabelsX.majorLabelStyle.rotation">0</option>
        <option name="charting.axisTitleX.visibility">visible</option>
        <option name="charting.axisTitleY.visibility">visible</option>
        <option name="charting.axisTitleY2.visibility">visible</option>
        <option name="charting.axisX.scale">linear</option>
        <option name="charting.axisY.scale">linear</option>
        <option name="charting.axisY2.enabled">0</option>
        <option name="charting.axisY2.scale">inherit</option>
        <option name="charting.chart.bubbleMaximumSize">50</option>
        <option name="charting.chart.bubbleMinimumSize">10</option>
        <option name="charting.chart.bubbleSizeBy">area</option>
        <option name="charting.chart.nullValueMode">gaps</option>
        <option name="charting.chart.showDataLabels">none</option>
        <option name="charting.chart.sliceCollapsingThreshold">0.01</option>
        <option name="charting.chart.stackMode">default</option>
        <option name="charting.chart.style">shiny</option>
        <option name="charting.drilldown">all</option>
        <option name="charting.layout.splitSeries">0</option>
        <option name="charting.layout.splitSeries.allowIndependentYRanges">0</option>
        <option name="charting.legend.labelStyle.overflowMode">ellipsisMiddle</option>
        <option name="charting.legend.placement">right</option>
      </chart>
    </panel>
  </row>
</form>
```