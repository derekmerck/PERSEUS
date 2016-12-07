"""
Adapted from Xiao Hu, PhD's MATLAB code for waveform quality checks

Dependencies:  numpy, scipy
"""

from __future__ import division
import numpy as np
import scipy
from scipy import signal
import logging
from matplotlib import pyplot as plt
import scipy.io

class QualityOfSignal():
    # just need to run isPPGGoodQuality(signal, timestamp, samplingFreq)
    # and it will output 1 or -1
    def __init__(self):
        pass

    def isPPGGoodQuality(self, ppgSig, fs, **kwargs):

        # Check to see if opt specified, otherwise use default
        if 'opt' in kwargs:
            opt = kwargs.get('opt')
        else:
            opt = self.makeDefaultPPGSignalQualityParameter()

        # Derek -- this throws div0 error sometimes, appears to be unused?
        # dt = 1./np.diff(tsofSig)

        onset = self.DetectPulseOnset(ppgSig, fs, opt['pulseWidth'])

        if (len(onset) < 3):
            qualityFlag = 0
            return qualityFlag

        sigMat, idx = self.formSignalMatrix(ppgSig, onset, fs)

        if len(sigMat) != 0:

            try:
                u, s, v = np.linalg.svd(sigMat)
            except np.linalg.linalg.LinAlgError:
                logging.warn("Single value decomposition failed! Returning indeterminate (0)")
                return 0

        else:
            qualityFlag = 0
            return qualityFlag

        ai = np.array([np.NaN, np.NaN, np.NaN])
        for j in range(1, np.minimum(4,len(s))):
            ai[j-1] = s[j-1]/s[j]

        if ai[0] > opt['AI1Threshold'] or ai[1] > opt['AI2Threshold'] or ai[2] > opt['AI3Threshold']:
            qualityFlag = 1
        else:
            qualityFlag = -1

        return qualityFlag

    def formSignalMatrix(self, sig, fiducialPnt, fs, **kwargs):

        # Check to see if opt specified, otherwise use default
        if 'algoParam' in kwargs:
            algoParam = kwargs.get('algoParam')
        else:
            algoParam = self.makeDefaultSig2MatrixParam()

        if type(fiducialPnt) == list:
            fiducialPnt = np.array(fiducialPnt)

        if type(sig) == list:
            sig = np.array(sig)

        if fiducialPnt.size == 0 or sig.size == 0:
            sigMat = []
            return sigMat

        # make sure the signal is a column vector
        if len(sig.shape) > 1:
            if sig.shape[1] > sig.shape[0]:
                sig = sig.T

        maxBeatLeninMS = 60/algoParam['minHR'] * 1000
        minBeatLeninMS = 60/algoParam['maxHR'] * 1000

        # determine the appropriate length of the pulse
        beatLeninMS = 1000*np.diff(fiducialPnt)/fs

        # find beats with the length between the max and min beat length
        idx_min = np.where(beatLeninMS > minBeatLeninMS)
        idx_max = np.where(beatLeninMS < maxBeatLeninMS)
        idx = np.intersect1d(idx_min, idx_max)
        if idx.size == 0:
            sigMat = []
            return sigMat, idx

        finalBeatLeninMS = np.percentile(beatLeninMS[idx], algoParam['prctile4BeatLength'])
        minimalBeatLeninMS = np.percentile(beatLeninMS[idx], algoParam['prctile4MinimalBeatLength'])

        # also remove pulses with a length less than minimal length
        idxx = np.where(beatLeninMS[idx] < minimalBeatLeninMS)
        idx[idxx] = []

        beatLen = int(np.fix(finalBeatLeninMS * fs/1000))
        sigMat = np.zeros((beatLen, len(idx)))

        for i in range(0, len(idx)):

            lenofPulse = fiducialPnt[idx[i]+1] - fiducialPnt[idx[i]]

            if lenofPulse >= beatLen:
                sigMat[:,i] = sig[fiducialPnt[idx[i]]:fiducialPnt[idx[i]]+beatLen]

            else:
                deltaW = beatLen - lenofPulse

                if deltaW < 3:
                    samplesToFitData = 3

                elif deltaW > 10:
                    samplesToFitData = 10

                else:
                    samplesToFitData = deltaW

                vv = self.PolyReSample(sig[fiducialPnt[idx[i]+1] - samplesToFitData: fiducialPnt[idx[i]+1]], np.r_[0:samplesToFitData].T, np.r_[samplesToFitData:samplesToFitData+deltaW].T, 1)
                sigMat[:,i] = np.hstack((sig[fiducialPnt[idx[i]]:fiducialPnt[idx[i]+1]], vv))

            # remove mean and normalized by standard deviation
            sigMat[:,i] = self.NormalizeSig(sigMat[:,i],2)

        return sigMat, idx

    def makeDefaultPPGSignalQualityParameter(self):

        opt = {}

        #length of the window in milliseconds to form sum fraction for pulse onset detection
        opt['pulseWidth'] = 120

        # lower threshold for three alignment indices to just signal quality
        opt['AI1Threshold'] = 2
        opt['AI2Threshold'] = 2
        opt['AI3Threshold'] = 2

        return opt

    # Is off by some values...
    def DetectPulseOnset(self, asig, fs, wMS):
        """
        Detect locations of onset for a pulsatile signal

        sig: single-channel pulsatile signal
        fs: sampling frequency
        wMS: window in milliseconds to search for onset after a
            threshold-crossing point is detected. This value will
            also create a lag between the detected onset and the
            actual onset. This lag is very desirable for using
            our subsequent algorithm of finding the onset. As it can
            be used a surrogate QRS R Peak position. Hence, we should
            use the maximal onset latency as a window. ICP: 120 ms.
            ABP: 220 ms. CBFV: 160 ms.
        """
        # the percentage of the maximal value of the slope sum function
        # to detect the onset
        AmplitudeRatio = .01

        # low pass filter
        sig = self.zpIIR(asig, 3, .1, 20, 5 * 2/fs)
        wSmp = int(np.round(wMS*fs/1000))

        BlankWindowRatio = .9

        # delta x
        diffsig = np.diff(sig)

        z = np.empty((sig.size - 1 - wSmp, 1))
        z[:] = np.NaN

        # calculate slope sum function
        for i in range(wSmp,sig.size-1):
            subsig = diffsig[i-wSmp:i]
            z[i-wSmp] = np.sum(subsig[subsig>0])

        z0 = np.mean(z)
        onset = [0]
        tPnt = []
        zThres = 0
        blankWin = int(np.round(400*fs/1000))
        subIdx = np.r_[onset[0]: onset[0] + 4*blankWin + 1]
        MedianArrayWinSize = 5

        # this value controls the final acceptance
        PrcofMaxAMP = .2
        SSFAmpArray = np.ones((MedianArrayWinSize,1))*(np.max(z) - np.min(z)) * PrcofMaxAMP
        # the percentage of maximal amplitude for threshold crossing
        DetectionThreshold = .2
        SSFCrossThresholdArray = np.ones((MedianArrayWinSize,1))*z0*DetectionThreshold
        idx = 1

        # Keep loop going while onsets detected
        while(1):

            # look for the first location where z > z0
            try:

                # Look in z[subIdx] (and make sure it doesn't go past z's size)
                # find first index where z > the mean of z
                tempIndex = np.trim_zeros(subIdx*(z.size>subIdx), 'b')
                ix = np.amin(np.where(z[tempIndex] > z0)[0])
            except:
                break

            ix = tempIndex[ix]
            tPnt.append(ix)
            srcWin = np.r_[np.maximum(0,ix - wSmp): ix + wSmp]
            #if the window has passed the length of the data, then exit
            if srcWin[-1] >= len(z):
                break

            # This section of code is to remove the initial zero-region in the SSF function before looking for onset (if such region exists)
            zPnt = np.where(z[srcWin] == 0)

            if zPnt[0].size != 0:
                zPnt = srcWin[zPnt[0]]

                if np.any(zPnt < ix):
                    srcWin = np.r_[zPnt[np.max(np.where(zPnt < ix))]: ix + wSmp]

            # accept the window
            if ( np.max(z[srcWin]) - np.min(z[srcWin]) > zThres):

                # calculate the threshold for next cycle
                SSFAmp = (np.max(z[srcWin]) - np.min(z[srcWin])) * PrcofMaxAMP
                SSFAmpArray[np.remainder(idx, MedianArrayWinSize)] = SSFAmp
                zThres = np.median(SSFAmpArray)
                SSFCrossThresholdArray[np.remainder(idx, MedianArrayWinSize)] = np.mean(z[srcWin])*DetectionThreshold
                z0 = np.median(SSFCrossThresholdArray)
                minSSF = np.min(z[srcWin]) + SSFAmp *AmplitudeRatio
                a = srcWin[0] + np.min(np.where(z[srcWin] >= minSSF))
                onset.append(a)

                # adaptively determine analysis window for next cycle
                bw = blankWin
                subIdx = np.round(np.r_[a + bw: a + 3*bw])
                idx = idx + 1

            else:
            # no beat detected
                subIdx = np.round(subIdx + blankWin)

        return onset

    def makeDefaultSig2MatrixParam(self):

        algoParam = {}

        # maximal HR allowed in BPM
        algoParam['maxHR'] = 200

        # minimal HR allowed in BPM
        algoParam['minHR'] = 40

        # the final length of the pulse will be set at the 80 percentile of the lengths
        algoParam['prctile4BeatLength'] = 80

        # pulse with minimal length should be excluded
        algoParam['prctile4MinimalBeatLength'] = 10

        return algoParam

    def zpIIR(self, sig, p, rp, rs, wn, **kwargs):
        #estimate the time constants

        # Check to see if blowpass specified, otherwise use default
        if 'blowpass' in kwargs:
            blowpass = kwargs.get('blowpass')
        else:
            blowpass = 1

        if blowpass == 1:
            b, a = scipy.signal.ellip(p, rp, rs, wn)

        else:
            # This was "size", but probably should be len
            if len(wn) > 1:
                b, a = scipy.signal.ellip(p, rp, rs, wn, 'stop')
            else:
                b, a = scipy.signal.ellip(p, rp, rs, wn, 'high')

        osig = scipy.signal.filtfilt(b, a, sig)

        return osig

    def NormalizeSig(self, sigMat, number):

        # Subtract mean
        meanValue = np.mean(sigMat)
        sigMatFinal = sigMat - meanValue

        # Divide by standard deviation
        stdValue = np.std(sigMat)
        sigMatFinal = sigMatFinal/stdValue

        return sigMatFinal

    def PolyReSample(self, y, T, newT, p):
        """
        A resampling program for a nonunifromly sample series y
        """

        pModel = np.polyfit(T, y, p)
        newy = np.polyval(pModel, newT)
        newy = newy.T

        #return newy, newT
        return newy

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Importing test data from csv files
    plethData = np.genfromtxt('../samples/10.25.2016_x00-11_ple_converted.csv', delimiter=',')
    QosData = np.genfromtxt('../samples/10.25.2016_x00-11_qos_converted.csv', delimiter=',')
    plethData = plethData[:, 1]
    QosData = QosData[:, 1]

    # Initialize data relevant parameters
    fs = 125
    t0 = fs*10
    delt = 250 # ms
    winL = 7 # seconds

    # Run our code and compare results
    SigCheck = QualityOfSignal()

    qualityFlag = []
    tofT = []
    # Loop through all the data
    t00 = t0
    for i in range(0, 500):
        qualityFlag.append(SigCheck.isPPGGoodQuality(plethData[t0:t0 + winL * fs], fs))
        t0 = np.floor(t0+fs*delt/1000)
        tofT.append(i*delt/1000)

    t11 = t0
    tofS = np.r_[0:(t11-t00)/fs:1/fs]

    maxData = int(np.ndarray.max(plethData[t00:t11]))
    plt.plot(tofS,plethData[t00:t11]/maxData, 'b')
    plt.plot(tofT,qualityFlag, 'ro', markersize=2)
    axes = plt.gca()
    axes.set_ylim([-1.2, 1.2])
    plt.show()
