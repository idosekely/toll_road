import datetime
import json
import flask
try:
    from matplotlib import pylab as plt
except ImportError:
    print "error while importing matplotlib"
    plt = None

import pandas as pd
from statsmodels import api as sm
from infra import parse_args, parse_single_arg
import math
from threading import Thread
from pytools.asynx import scheduled
from distutils.util import strtobool

__author__ = 'sekely'


class Analyzer(object):
    _csv = None
    csv_file = property(lambda self: self._csv)
    last_update = None
    df = pd.DataFrame()
    _auto = True
    auto_refresh = property(lambda self: self._auto)

    def __init__(self):
        t = Thread(target=self._auto_refresh)
        t.start()

    def _str_to_bool(self, val):
        try:
            return bool(strtobool(val))
        except ValueError:
            return None

    @csv_file.setter
    def csv_file(self, val):
        self._csv = val
        self.extract_data()

    @auto_refresh.setter
    def auto_refresh(self, val):
        self._auto = self._str_to_bool(val)

    def extract_data(self, drop_na=False):
        if not self.csv_file:
            return
        dateparse = lambda dates: pd.datetime.strptime(dates, '%Y-%m-%d %H:%M:%S.%f')
        df = pd.read_csv(self.csv_file, parse_dates='timestamp', index_col='timestamp', date_parser=dateparse)
        df['traffic'] = df['traffic'].apply(lambda x: x / 60.)
        self.df = df.resample('T').mean()
        if drop_na:
            self.df.dropna(inplace=True)
        else:
            self.df.interpolate(inplace=True)
        self.last_update = datetime.datetime.now()

    def rolling_mean(self, window=10):
        means = self.df.rolling(window=window).mean()
        ewm_means = self.df.ewm(halflife=window).mean()
        means.columns = ['mean-%s' % col for col in means.columns]
        ewm_means.columns = ['ewm-%s' % col for col in ewm_means.columns]
        ts = pd.concat([means, ewm_means], axis=1)
        return ts

    @scheduled(60 * 5)  # update the data frame every 5 minutes
    def _auto_refresh(self):
        if not self.auto_refresh:
            return
        self.extract_data()

    def filter(self, lamb=1e5):
        cycle, trend = sm.tsa.filters.hpfilter(self.df, lamb=lamb)
        trend.columns = ['%s-trend' % col for col in trend.columns]
        # cycle.columns = ['%s-cycle' % col for col in cycle.columns]
        # ts = pd.concat([cycle, trend], axis=1)
        # return ts
        return trend

    @staticmethod
    def plot(ts):
        if not plt:
            print ""
        fig, ax = plt.subplots()
        lined = dict()

        ax.set_title('Click on legend line to toggle line on/off')
        lines = [ax.plot(ts[col], label=col) for col in ts.columns]
        leg = ax.legend(loc='best')

        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5)  # 5 pts tolerance
            lined[legline] = origline[0]

        def onpick(event):
            # on the pick event, find the orig line corresponding to the
            # legend proxy line, and toggle the visibility
            legline = event.artist
            origline = lined[legline]
            vis = not origline.get_visible()
            origline.set_visible(vis)
            # Change the alpha on the line in the legend so we can see what lines
            # have been toggled
            if vis:
                legline.set_alpha(1.0)
            else:
                legline.set_alpha(0.2)
            fig.canvas.draw()

        fig.canvas.mpl_connect('pick_event', onpick)
        plt.show(False)

    def columns_data(self, df, max_samples=2000):
        sample = '%sT' % int(math.ceil(len(df) / float(max_samples)))
        def _round(x, precision=2):
            try:
                return round(x, precision)
            except TypeError:
                return x
        df = df.resample(sample).mean().applymap(lambda x: _round(x, 2))
        df.dropna(inplace=True)
        ret_columns = {'timestamp': [str(t) for t in df.index]}
        for col in df.columns:
            ret_columns[col] = list(df[col])
        return ret_columns

    def do_summary(self, *args, **kwargs):
        return flask.jsonify(self.df.describe().to_dict())

    @parse_args(lamb=[float, 1e5])
    def do_filter(self, *args, **kwargs):
        df = self.filter(kwargs['lamb']).interpolate()
        return self._process_json(df, **kwargs)

    def _time_frame(self, tf):
        _fmt = '%Y%m%d%H%M'
        delta = {
            "last_day": datetime.timedelta(days=1),
            "last_3_days":datetime.timedelta(days=3),
            "last_week":datetime.timedelta(days=7),
            "all": None,
        }
        if delta[tf]:
            now = datetime.datetime.now()
            to_time = now.strftime(_fmt)
            from_time = now - delta[tf]
            from_time = from_time.strftime(_fmt)
        else:
            from_time = None
            to_time = None
        return from_time, to_time

    @parse_args(columns_data=[None, False], orient=[None, 'columns'],
                from_time=[None, None], to_time=[None, None], time_frame=[None, None])
    def _process_json(self, df, **kwargs):
        time_frame = None if not kwargs['time_frame'] else kwargs['time_frame']
        from_time = None if not kwargs['from_time'] else kwargs['from_time']
        to_time = None if not kwargs['to_time'] else kwargs['to_time']
        if time_frame:
            from_time, to_time = self._time_frame(time_frame)
        if from_time or to_time:
            df = df[from_time:to_time]
        if kwargs['columns_data']:
            return flask.jsonify(self.columns_data(df))
        j = df.to_json(date_format='iso', orient=kwargs['orient'], double_precision=2, date_unit='s')
        return flask.jsonify(json.loads(j))

    def do_raw_data(self, *args, **kwargs):
        return self._process_json(self.df, **kwargs)

    @parse_args(window=[int, 10])
    def do_rolling_mean(self, *args, **kwargs):
        df = self.rolling_mean(window=kwargs['window']).interpolate()
        return self._process_json(df, **kwargs)

    def do_refresh(self, *args, **kwargs):
        self.extract_data()
        return "analyzer refreshed\n"

    def do_config(self, *args, **kwargs):
        for key in kwargs.iterkeys():
            val = parse_single_arg(key, kwargs)
            setattr(self, key, val)
        return 'finished analyzer config\n'

    def do_describe(self, *args, **kwargs):
        ret = {'csv_file': self.csv_file,
               'last_update': self.last_update,
               'samples': len(self.df),
               'auto_refresh': self.auto_refresh,
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x]}
        return flask.jsonify(ret)
