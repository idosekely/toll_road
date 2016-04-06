import datetime
import json
import flask
from matplotlib import pylab as plt
import pandas as pd
from statsmodels import api as sm
from infra import parse_arg

__author__ = 'sekely'


class Analyzer(object):
    _csv = None
    csv_file = property(lambda self: self._csv)
    last_update = None
    df = pd.DataFrame()

    @csv_file.setter
    def csv_file(self, val):
        self._csv = val
        self.extract_data()

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

    def filter(self, lamb=1e5):
        cycle, trend = sm.tsa.filters.hpfilter(self.df, lamb=lamb)
        cycle.columns = ['%s-cycle' % col for col in cycle.columns]
        trend.columns = ['%s-trend' % col for col in trend.columns]
        ts = pd.concat([cycle, trend], axis=1)
        return ts

    @staticmethod
    def plot(ts):
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

    def columns_data(self, df):
        def _round(x, precision=2):
            try:
                return round(x, precision)
            except TypeError:
                return x
        df = df.applymap(lambda x: _round(x, 2))
        ret_columns = {'timestamp': [str(t) for t in df.index]}
        for col in df.columns:
            ret_columns[col] = list(df[col])
        return ret_columns

    def do_summary(self, *args, **kwargs):
        return flask.jsonify(self.df.describe().to_dict())

    def do_filter(self, *args, **kwargs):
        columns_data = parse_arg('columns_data', kwargs, default_val=False)
        lamb = parse_arg('lamb', kwargs, float, 1e5)
        orient = parse_arg('orient', kwargs, default_val='columns')
        df = self.filter(lamb).interpolate()
        if columns_data:
            return flask.jsonify(self.columns_data(df))
        j = df.to_json(date_format='iso', orient=orient, double_precision=2, date_unit='s')
        return flask.jsonify(json.loads(j))

    def do_raw_data(self, *args, **kwargs):
        columns_data = parse_arg('columns_data', kwargs, default_val=False)
        orient = parse_arg('orient', kwargs, default_val='columns')
        if columns_data:
            return flask.jsonify(self.columns_data(self.df))
        j = self.df.to_json(date_format='iso', orient=orient, double_precision=2, date_unit='s')
        return flask.jsonify(json.loads(j))

    def do_rolling_mean(self, *args, **kwargs):
        columns_data = parse_arg('columns_data', kwargs, default_val=False)
        window = parse_arg('window', kwargs, int, 10)
        orient = parse_arg('orient', kwargs, default_val='columns')
        df = self.rolling_mean(window=window).interpolate()
        if columns_data:
            return flask.jsonify(self.columns_data(df))
        j = df.to_json(date_format='iso', orient=orient, double_precision=2, date_unit='s')
        return flask.jsonify(json.loads(j))

    def do_refresh(self, *args, **kwargs):
        self.extract_data()
        return "analyzer refreshed\n"

    def do_config(self, *args, **kwargs):
        for key in kwargs.iterkeys():
            val = parse_arg(key, kwargs)
            setattr(self, key, val)
        return 'finished analyzer config\n'

    def do_describe(self, *args, **kwargs):
        ret = {'csv_file': self.csv_file,
               'last_update': self.last_update,
               'samples': len(self.df),
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x]}
        return flask.jsonify(ret)