# -*- coding: utf-8 -*-

from __future__ import division, print_function
from __future__ import absolute_import, unicode_literals

from PhloxAR.base import *
import scipy.signal as signal
import scipy.optimize as optimize
import numpy as npy
import copy, operator


class LineScan(list):
    """
    A line scan is an one dimensional signal pulled from the intensity
    of a series of a pixels in ang image. LineScan allows you to do a
    series of operations just like on an image class object. You can
    also treat the line scan as a python list object. A LineScan object
    is automatically generated by calling ImageClass.get_line_scan on an
    image. You can also roll your own by declaring a LineScan object
    and passing the constructor a 1xN list of values.
    """
    point_loc = None
    image = None

    def __init__(self, args, **kwargs):
        if isinstance(args, npy.ndarray):
            args = args.tolist()
        super(LineScan, self).__init__(args)

        self.image = None
        self.pt1 = None
        self.pt2 = None
        self.row = None
        self.col = None
        self.channel = -1

        for key in kwargs:
            if key in self.__dict__:
                self.__dict__[key] = kwargs[key]

        if self.point_loc is None:
            self.point_loc = zip(range(0, len(self)), range(0, len(self)))

    def _update(self, obj):
        """
        Update LineScan instance object.
        :param obj: LineScan instance.
        :return: None.
        """
        self.image = obj.image
        self.pt1 = obj.pt1
        self.pt2 = obj.pt2
        self.row = obj.row
        self.col = obj.col
        self.channel = obj.channel
        self.point_loc = obj.point_loc

    def __getitem__(self, key):
        """
        :param key: index or slice.
        :return: a LineScan sliced.
        """
        item = super(LineScan, self).__getitem__(key)
        if isinstance(key, slice):
            return LineScan(item)
        else:
            return item

    def __sub__(self, other):
        if len(self) == len(other):
            ret_val = LineScan(map(operator.sub, self, other))
        else:
            print("Size mismatch.")
            return None
        ret_val._update(self)
        return ret_val

    def __add__(self, other):
        if len(self) == len(other):
            ret_val = LineScan(map(operator.add, self, other))
        else:
            print("Size mismatch.")
            return None

        ret_val._update(self)
        return ret_val

    def __mul__(self, other):
        if len(self) == len(other):
            ret_val = LineScan(map(operator.mul, self, other))
        else:
            print("Size mismatch.")
            return None

        ret_val._update(self)
        return ret_val

    def __div__(self, other):
        if len(self) == len(other):
            try:
                ret_val = LineScan(map(operator.div, self, other))
            except ZeroDivisionError:
                print("Second LineScan contains zeros.")
                return None
        else:
            print("Size mismatch.")
            return None

        ret_val._update(self)

    def smooth(self, degree=3):
        """
        Perform a Gaussian simple smoothing operation on the signal.
        :param degree: degree of the fitting function. Higher degree means
                        more smoothing.
        :return: a smoothed LineScan object.
        Notes:
        Cribbed from
        http://www.swharden.com/blog/2008-11-17-linear-data-smoothing-in-python/
        """
        window = degree * 2 - 1
        weight = npy.array([1.0] * window)
        weight_gauss = []

        for i in range(window):
            i = i - degree + 1
            frac = i / float(window)
            gauss = 1 / npy.exp((4 * frac) ** 2)
            weight_gauss.append(gauss)

        weight = npy.array(weight_gauss) * weight
        smoothed = [0.0] * (len(self) - window)

        for i in range(len(smoothed)):
            smoothed[i] = sum(npy.array(self[i:i+window])*weight) / sum(weight)

        front = self[0:degree - 1]
        front += smoothed
        front += self[-1 * degree:]
        ret_val = LineScan(front, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)
        return ret_val

    def normalize(self):
        """
        Normalize the signal so the maximum value is scaled to one.
        :return: a normalized ScanLine object.
        """
        tmp = npy.array(self, dtype='float32')
        tmp /= npy.max(tmp)
        ret_val = LineScan(list(tmp[:]), image=self.image,
                           point_loc=self.point_loc, pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)
        return ret_val

    def scale(self, val_range=(0, 1)):
        """
        Scale the signal  so the max and min values are all scaled to the values
        in val_range. This is handy if you want to compare the shape of tow
        signals that are scaled to different ranges.
        :param val_range: a tuple that provides the range of output signal.
        :return: a scaled LineScan object.
        """
        tmp = npy.array(self, dtype='float32')
        vmax = npy.max(tmp)
        vmin = npy.min(tmp)
        a = npy.min(val_range)
        b = npy.max(val_range)
        tmp = (((b - a) / (vmax - vmin)) * (tmp - vmin)) + a
        ret_val = LineScan(list(tmp[:]), image=self.image,
                           point_loc=self.point_loc, pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def minima(self):
        """
        Global minima in the line scan.
        :return: a list of tuples of the format: (LineScanIndex, MinimaValue,
                  (image_position_x, image_position_y))
        """
        minvalue = npy.min(self)
        idxs = npy.where(npy.array(self) == minvalue)[0]
        minvalue = npy.ones((1, len(idxs))) * minvalue
        minvalue = minvalue[0]
        pts = npy.array(self.point_loc)
        pts = pts[idxs]
        pts = [(p[0], p[1]) for p in pts]
        return zip(idxs, minvalue, pts)

    def maxima(self):
        """
        Global maxima in the line scan.
        :return: a list of tuples of the format: (LineScanIndex, MaximaValue,
                  (image_position_x, image_position_y))
        """
        maxvalue = npy.max(self)
        idxs = npy.where(npy.array(self) == maxvalue)[0]
        maxvalue = npy.ones((1, len(idxs))) * maxvalue
        maxvalue = maxvalue[0]
        pts = npy.array(self.point_loc)
        pts = pts[idxs]
        pts = [(p[0], p[1]) for p in pts]

        return zip(idxs, maxvalue, pts)

    def derivative(self):
        """
        Finds the discrete derivative of the signal. The discrete derivative
        is simply the difference between each successive samples. A good use of
        this function is edge detection.
        :return: a LineScan object.
        """
        tmp = npy.array(self, dtype='float32')
        d = [0]
        d += list(tmp[1:] - tmp[0:-1])
        ret_val = LineScan(d, image=self, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)
        return ret_val

    def local_minima(self):
        """
        Local minima are defined as points that are less than their neighbors
        to the left and to the right.
        :return: a list of tuples of the format: (LineScanIndex, MaximaValue,
                  (image_position_x, image_position_y))
        """
        tmp = npy.array(self)
        idx = npy.r_[True, tmp[1:] < tmp[:-1]] & npy.r_[tmp[:-1] < tmp[1:], True]
        i = npy.where(idx is True)[0]
        values = tmp[i]
        pts = npy.array(self.point_loc)
        pts = pts[i]
        pts = [(p[0], p[1]) for p in pts]

        return zip(i, values, pts)

    def local_maxmima(self):
        """
        Local minima are defined as points that are less than their neighbors
        to the left and to the right.
        :return: a list of tuples of the format: (LineScanIndex, MaximaValue,
                  (image_position_x, image_position_y))
        """
        tmp = npy.array(self)
        idx = npy.r_[True, tmp[1:] > tmp[:-1]] & npy.r_[tmp[:-1] > tmp[1:], True]
        i = npy.where(idx is True)[0]
        values = tmp[i]
        pts = npy.array(self.point_loc)
        pts = pts[i]
        pts = [(p[0], p[1]) for p in pts]

        return zip(i, values, pts)

    def resample(self, n=100):
        """
        Re-sample the signal to fit into n samples. This method is handy
        if you would like to resize multiple signals so that they fit
        together nice. Note that using n < len(LineScan) can cause data loss.
        :param n: number of samples to reshape to.
        :return: a LineScan object of length n.
        """
        sig = signal.resample(self, n)
        pts = npy.array(self.point_loc)
        x = linspace(pts[0, 0], pts[-1, 0], n)
        y = linspace(pts[0, 1], pts[-1, 1], n)
        pts = zip(x, y)
        ret_val = LineScan(list(sig), image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def fit2model(self, func, p0=None):
        """
        Fit the data to the provided model. This can be any
        arbitrary 2D signal.
        :param func: a function of the form func(x_values, p0, p1, ... pn)
                      where p is parameter for the model.
        :param p0: a list of the initial guess for the model parameters.
        :return: a LineScan object where the fitted model data replaces
                  the actual data.
        """
        yvals = npy.array(self, dtype='float32')
        xvals = range(0, len(yvals), 1)
        popt, pcov = optimize.curve_fit(func, xvals, yvals, p0=p0)
        yvals = func(xvals, *popt)
        ret_val = LineScan(list(yvals), image=self.image,
                           point_loc=self.point_loc, pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)
        return ret_val

    def get_model_params(self, func, p0=None):
        """
        Fit a model to the data and then return.
        :param func: a function of the form func(x_values, p0, p1, ... pn)
                      where p is parameter for the model.
        :param p0: a list of the initial guess for the model parameters.
        :return: The model parameters as a list.
        """
        yvals = npy.array(self, dtype='float32')
        xvals = range(0, len(yvals), 1)
        popt, pcov = optimize.curve_fit(func, xvals, yvals, p0=p0)

        return popt

    def convolve(self, kernel):
        """
        Convolve the line scan with a one dimensional kernel stored as
        a list. Allows you to create an arbitrary filter for the signal.
        :param kernel: an Nx1 list or np.array that defines the kernel.
        :return: a LineScan feature with the kernel applied. We crop
                  the fiddly bits at the end and the begging of the kernel
                  so everything lines up nicely.
        """
        out = npy.convolve(self, npy.array(kernel, dtype='float32'), 'same')
        ret_val = LineScan(out, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2, channel=self.channel)
        return ret_val

    def fft(self):
        """
        Perform a Fast Fourier Transform on the line scan and return
        the FFT output and the frequency of each value.
        :return: the FFT as a numpy array of irrational numbers and a one
                  dimensional list of frequency values.
        """
        sig = npy.array(self, dtype='float32')
        fft = npy.fft.fft(sig)
        freq = npy.fft.fftfreq(len(sig))

        return fft, freq

    def ifft(self, fft):
        """
        Perform a inverse Fast Fourier Transform on the provided irrationally
        valued signal and return the results as a LineScan.
        :param fft: a one dimensional numpy array of irrational values upon
                     which we will perform the IFFT.
        :return: a LineScan object of the reconstructed signal.
        """
        sig = npy.fft.ifft(fft)
        ret_val = LineScan(sig.real)
        ret_val.image = self.image
        ret_val.point_loc = self.point_loc
        return ret_val

    def lut(val=-1):
        """
        Create an empty look up table(LUT)
        :param val: If default value is what the lut is initially filled with
        if val == 0
            the array is all zeros.
        if val > 0
            the array is set to default value. Clipped to 255.
        if val < 0
            the array is set to the range [0,255]
        if val is a tuple of two values:
            we set stretch the range of 0 to 255 to match the range provided.
        :return: a LUT.
        """
        lut = None
        if isinstance(val, list) or isinstance(val, tuple):
            start = npy.clip(val[0], 0, 255)
            stop = npy.clip(val[1], 0, 255)
            lut = npy.around(npy.linsapce(start, stop, 256), 0)
            lut = npy.array(lut, dtype='uint8')
            lut = lut.tolist()
        elif val == 0:
            lut = npy.zeros([1, 256]).tolist()[0]
        elif val > 0:
            val = npy.clip(val, 1, 255)
            lut = npy.ones([1, 256]) * val
            lut = npy.array(lut, dtype='uint8')
            lut = lut.tolist()
        elif val < 0:
            lut = npy.linspace(0, 256, 256)
            lut = npy.array(lut, dtype='uint8')
            lut = lut.tolist()

        return lut

    def fill_lut(self, lut, idxs, value=255):
        """
        Fill up an existing LUT at the indexes specified by idxs
        with the value specified by value. This is useful for picking
        out specific values.
        :param lut: an existing LUT (just a list of 255 values).
        :param idxs: the indexes of the LUT to fill with the value.
                      This can also be a sample swatch of an image.
        :param value: the value to set the LUT[idx] to.
        :return: an updated LUT.
        """
        if idxs.__class__.__name__ == 'Image':
            npg = idxs.getGrayNumpy()
            npg = npg.reshape([npg.shape[0] * npg.shape[1]])
            idxs = npg.tolist()
        val = npy.clip(value, 0, 255)

        for idx in idxs:
            if 0 <= idx < len(lut):
                lut[idx] = val
        return lut

    def threshold(self, threshold=128, invert=False):
        """
        Do a 1-D threshold operation. Values about the threshold will
        be set to 255, values below the threshold will be set to 0.
        If invert is true we do the opposite.
        :param threshold: the cutoff value for threshold.
        :param invert: if invert is False, above the threshold are set
                        to 255, if invert is True, set to 0.
        :return: the thresholded LineScan operation.
        """
        out = []
        high = 255
        low = 0
        if invert:
            high = 0
            low = 255

        for p in self:
            if p < threshold:
                out.append(low)
            else:
                out.append(high)

        ret_val = LineScan(out, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, ptw=self.pt2)
        ret_val._update(self)

        return ret_val

    def invert(self, max=255):
        """
        Do an 8bit invert of the signal. What was black is now white.
        :param max: the maximum value of a pixel in the image, usually 255.
        :return: the inverted LineScan object.
        """
        out = []

        for p in self:
            out.append(255-p)

        ret_val = LineScan(out, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, ptw=self.pt2)
        ret_val._update(self)

        return ret_val

    def mean(self):
        """
        Computes the statistical mean of the signal.
        :return: the mean of the LineScan object.
        """
        return sum(self) / len(self)

    def variance(self):
        """
        Computes the variance of the signal.
        :return: the variance of the LineScan object.
        """
        mean = sum(self) / len(self)
        summation = 0

        for num in self:
            summation += (num - mean)**2

        return summation / len(self)

    def deviation(self):
        """
        Computes the standard deviation of the signal.
        :return: the standard deviation of the LineScan object.
        """
        mean = sum(self) / len(self)
        summation = 0

        for num in self:
            summation += (num - mean)**2

        return npy.sqrt(summation / len(self))

    def median(self, size=5):
        """
        Do a sliding median filter with a window size equal to size.
        :param size: the size of the median filter.
        :return: the LineScan after being passed through the median filter.
                  the last index where the value occurs or None if none is found.
        """
        if size % 2 == 0:
            size += 1

        skip = int(npy.floor(size / 2))
        out = self[0:skip]
        vsz = len(self)

        for i in range(skip, vsz-skip):
            val = npy.median(self[i-skip:i+skip])
            out.append(val)

        for p in self[-1*skip:]:
            out.append(p)

        ret_val = LineScan(out, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def find_first_index_equal(self, value=255):
        """
        Find the index of the first element of the LineScan that has a
        value equal to value. If nothing found, None is returned.
        :param value: the value to look for.
        :return: the first index where the value occurs or None if not found.
        """
        vals = npy.where(npy.array(self) == value)[0]
        ret_val = None

        if len(vals) > 0:
            ret_val = vals[0]

        return ret_val

    def find_last_index_equal(self, value=255):
        """
        Find the index of the last element of the LineScan. If nothing found,
        None is returned.
        :param value: the value to look for.
        :return: the last index where the value occurs or None if not found.
        """
        vals = npy.where(npy.array(self) == value)[0]
        ret_val = None

        if len(vals) > 0:
            ret_val = vals[-1]

        return ret_val

    def find_first_index_greater(self, value=255):
        """
        Find the index of the first element of the LineScan that has a
        value equal to value. If nothing found, None is returned.
        :param value: the value to look for.
        :return: the first index where the value occurs or None if not found.
        """
        vals = npy.where(npy.array(self) >= value)[0]
        ret_val = None

        if len(vals) > 0:
            ret_val = vals[0]

        return ret_val

    def apply_lut(self, lut):
        """
        Apply a lut to the signal.
        :param lut: an array of length 256, the array elements are the
                     values that are replaced via the lut.
        :return: a LineScan object with the lut applied to the values.
        """
        out = []

        for p in self:
            out.append(lut[p])

        ret_val = LineScan(out, image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def median_filter(self, kernel_size=5):
        """
        Apply median filter on the data.
        :param kernel_size: size of the filter (should be odd int) - int
        :return: a LineScan object with the median filter applied
                  to the values.
        """
        try:
            from signal import medfilt
        except ImportError:
            warnings.warn("Scipy version >= 0.11 required.")
            return None

        if kernel_size % 2 == 0:
            kernel_size -= 1
            print("Kernel Size should be odd.")

        medfilt_array = medfilt(npy.asarray(self[:]), kernel_size)
        ret_val = LineScan(medfilt_array.astype('uint8').tolist(),
                           image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def detrend(self):
        """
        Detrend the data
        :return: a LineScan object with detrend data.
        """
        try:
            from signal import detrend as scidetrend
        except ImportError:
            warnings.warn("Scipy version >= 0.11 required.")
            return None
        detrend_arr = scidetrend(npy.asarray(self[:]))
        ret_val = LineScan(detrend_arr.astype('uint8').tolist(),
                           image=self.image, point_loc=self.point_loc,
                           pt1=self.pt1, pt2=self.pt2)
        ret_val._update(self)

        return ret_val

    def running_average(self, diameter=3, kernel='uniform'):
        """
        Finds the running average by either using a uniform kernel or
        using a gaussian kernel. The gaussian kernels calculated from
        the standard normal distribution formula.
        :param diameter: size of the window (should be odd int) - int
        :param kernel: 'uniform' (default) / 'gaussian' - used to decide
                      the kernel - string.
        :return: a LineScan object with the kernel of the provided
                  algorithm applied.
        """
        k = list()
        if diameter % 2 == 0:
            warnings.warn("Diameter mush be an odd integer.")
            return None
        if kernel == 'uniform':
            k = list(1 / float(diameter) * npy.ones(diameter))
        elif kernel == 'gaussian':
            r = diameter / 2
            for i in range(-int(r), int(r) + 1):
                k.append(npy.exp(-i**2 / (2*(r/3)**2)) / (npy.sqrt(2*npy.pi) * (r/3)))
        ret_val = LineScan(map(int, self.convolve(k)))
        ret_val._update(self)

        return ret_val

    def find_peaks(self, window=30, delta=3):
        """
        Find the peaks in a LineScan.
        :param window: the size of the window in which the peak should have
                        the highest value to be considered as a peak. By
                        default this is 15 as it gives appropriate results.
                        The lower this value the more the peaks are returned.
        :param delta: the minimum difference between the peak and all elements
                       in the window
        :return: a list of (peak position, peak value) tuples.
        """
        maximum = -npy.Inf
        width = int(window / 2)
        peaks = []

        for i, val in enumerate(self):
            if val > maximum:
                maximum = val
                max_pos = i
            # checking whether peak satisfies window and delta conditions
            if max(self[max(0, i-width):i+width]) + delta < maximum:
                peaks.append((max_pos, maximum))
                maximum = -npy.Inf

        return peaks

    def find_valleys(self, window=30, delta=3):
        """
        Finds the valleys in a LineScan.
        :param window: the size of the window in which the valley should
                        have the highest value to be considered as a valley.
                        By default this is 15 as it gives appropriate results.
                        The lower this value the more the valleys are returned
        :param delta: the minimum difference between the valley and all
                       elements in the window
        :return: a list of (valley position, peak value) tuples.
        """
        minimum = -npy.Inf
        width = int(window / 2)
        valleys = []

        for i, val in enumerate(self):
            if val < minimum:
                minimum = val
                min_pos = i
            # checking whether peak satisfies window and delta conditions
            if min(self[max(0, i - width):i + width]) - delta < minimum:
                valleys.append((min_pos, minimum))
                minimum = -npy.Inf

        return valleys

    def fit_spline(self, degree=2):
        """
        Generates a spline curve fitting over the points in LineScan with
        order of precision given by the parameter degree.
        :param degree: the precision of the generated spline.
        :return: the spline as a LineScan fitting over the initial values of
                  LineScan
        Notes:
        Implementation taken from http://www.scipy.org/Cookbook/Interpolation
        """
        if degree > 4:
            degree = 4  # No significant improvement with respect to time usage
        if degree < 1:
            warnings.warn("LineScan.fit_spline - degree needs to be >= 1.")
            return None

        ret_val = None
        y = npy.array(self)
        x = npy.arange(0, len(y), 1)
        dx = 1
        newx = npy.arange(0, len(y)-1, pow(0.1, degree))
        cj = signal.cspline1d(y)
        cj = signal.cspline1d_eval(cj, newx, dx=dx, x0=x[0])

        return ret_val
