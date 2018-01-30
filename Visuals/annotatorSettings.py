###############
#### CODES ####
###############

ekgCodes = ["EKG INTERPRETABLE", "EKG NOT Interpretable", "EKG OFF", "EKG DISCONNECT event",     "Clin. SIGNIFICANT EKG alarm", "Clin. NOT Significant EKG alarm", "Clin. INDETERMINATE EKG alarm",     "Annotation ERROR"]
ppgCodes = ["PPG INTERPRETABLE", "PPG NOT Interpretable", "PPG OFF", "PPG DISCONNECT event",     "Clin. SIGNIFICANT PPG alarm", "Clin. NOT Significant PPG alarm", "Clin. INDETERMINATE PPG alarm",     "Annotation ERROR"]
#bpCodes = ["Clin. SIGNIFICANT BP alarm", "Clin. NOT Significant BP alarm", "Clin. INDETERMINATE BP alarm",     "Annotation ERROR"]
#significanceCodes = ["EMERGENT", "URGENT", "NON-urgent", "INDETERMINATE",     "Annotation ERROR"]
qosCodes = ["QoS CORRECT", "QoS NOT Correct",     "Annotation ERROR"]

# Color options for annotations.
ekgColorSelector = ["green", "red", "teal", "gray","orange","lime","brown","black"]
ppgColorSelector = ["green", "red", "teal", "gray","orange","lime","brown","black"]
qosColorSelector = ["#FF00FF", "blue", "gray","orange"]

####################
#### APPEARANCE ####
####################

ppgYRange = [0,5000]
ekgYRange = [-1.5,1.5]
spo2YRange = [50,120]
hrYRange = [0,250]
YRange3 = [0,250]
YRange4 = [0,250]
YRange5 = [0,250]


# Width and height options for viewers.
viewerWidth = 1500
ekgViewerHeight = 250
ppgViewerHeight = 250
spo2ViewerHeight = 150
hrViewerHeight = 150
nibpViewerHeight = 150
defaultViewerHeights = 250

# Line color and qos color options.
alarmColor = 'purple'
ekgLineColor = "green"
ppgLineColor = "blue"
qosMarkerColor = "red"
hrLineColor = 'black'
spo2LineColor = 'black'
nibpSysLineColor = 'blue'
nibpMeanLineColor = 'black'
nibpDiaLineColor = 'red'

##############
#### MISC ####
##############

# Starting page before file gets initialized.
initializePage = -1

# Initial amount of data to display (in seconds).
windowInSecs = 60

timeAroundAlarm = 315  #ORIGINAL VALUE 300

# Frequency of PPG signal. Helps determine number of datapoints to grab per window.
ppgFrequency = 125

## Slider attributes for adjusting the amount of data (in seconds) displayed in the window. ##

# Smallest window size possible (in seconds).
timeSliderStart = 15

# Largest window size possible (in seconds).
timeSliderEnd = 120

timeSliderInitialValue = windowInSecs
timeSliderStep = 15
