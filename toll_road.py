#!/usr/bin/python
import datetime
import csv
import sys
import os
import json

import requests
from BeautifulSoup import BeautifulSoup

from pytools.asynx import scheduled, threaded

import pandas as pd
import matplotlib.pylab as plt
import statsmodels.api as sm

from flask import Flask
from flask import request

__author__ = 'sekely'

requests.packages.urllib3.disable_warnings()
DEFAULT_CSV = '/tmp/toll_road.csv'
DEST = '32.051070, 34.785303'
ORIGIN = '32.000955, 34.845297'

app = Flask(__name__)


class ServerStopped(Exception):
    pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Collector(object):
    __metaclass__ = Singleton
    headers = ['timestamp', 'price', 'traffic']
    started = False

    _csv = None
    csv_file = property(lambda self: self._csv)
    api_key = None

    @csv_file.setter
    def csv_file(self, csv_file):
        if not os.path.isfile(csv_file):
            self._csv = csv_file
            with open(self.csv_file, 'w') as f:
                writer = csv.DictWriter(f, self.headers)
                writer.writeheader()

    def save_to_csv(self, data=None):
        if not data:
            data = {'timestamp': str(datetime.datetime.now()),
                    'key': None,
                    'values': None}
        with open(self.csv_file, 'a') as f:
            writer = csv.DictWriter(f, self.headers)
            writer.writerow(data)

    def get_price(self):
        r = requests.get('https://www.fastlane.co.il/mobile.aspx')
        parsed_html = BeautifulSoup(r.content)
        price = parsed_html.find('span', attrs={'id': 'lblPrice'}).text
        return int(price)

    def get_traffic(self):
        payload = {
            'key': self.api_key,
            'departure_time': 'now',
            'origins': ORIGIN,
            'destinations': DEST
        }
        base_url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        r = requests.get(base_url, params=payload)
        resp = json.loads(r.text)
        value = resp['rows'][0]['elements'][0]['duration_in_traffic']['value']
        return int(value)

    @threaded(block=False)
    @scheduled(60)
    def start_sampling(self):
        if not self.started:
            raise ServerStopped()
        ts = str(datetime.datetime.now())
        price = self.get_price()
        if self.api_key:
            traffic = self.get_traffic()
        else:
            traffic = None
        data = {'timestamp': ts,
                'price': price,
                'traffic': traffic}
        self.save_to_csv(data)

    def do_start(self, *args, **kwargs):
        self.started = True
        self.start_sampling()
        return 'collector started\n'

    def do_stop(self, *args, **kwargs):
        self.started = False
        return 'stopping collector\n'

    def do_config(self, *args, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val[0])
        return 'finished collector config\n'


    def do_describe(self, *args, **kwargs):
        ret = {'csv_file': self.csv_file,
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x]}
        return json.dumps(ret)


class Analyzer(object):
    csv_file = None

    def extract_data(self, drop_na=False):
        dateparse = lambda dates: pd.datetime.strptime(dates, '%Y-%m-%d %H:%M:%S.%f')
        df = pd.read_csv(self.csv_file, parse_dates='timestamp', index_col='timestamp', date_parser=dateparse)
        df['traffic'] = df['traffic'].apply(lambda x: x / 60.)
        self.df = df.resample('T').mean()
        if drop_na:
            self.df.dropna(inline=True)
        else:
            self.df.interpolate(inplace=True)

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

    def do_summary(self, *args, **kwargs):
        return self.df.describe().to_json()

    def do_filter(self, *args, **kwargs):
        return self.filter(**kwargs).to_json(date_format='iso')

    def do_rolling_mean(self, *args, **kwargs):
        return self.rolling_mean(**kwargs).to_json(date_format='iso')

    def do_refresh(self, *args, **kwargs):
        self.extract_data()
        return "analyzer refreshed\n"

    def do_config(self, *args, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val[0])
        return 'finished analyzer config\n'

    def do_describe(self, *args, **kwargs):
        ret = {'csv_file': self.csv_file,
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x]}
        return json.dumps(ret)


_ar = Analyzer()
_cr = Collector()


@app.route('/collector/<command>')
def collector(command):
    command = command.replace('-', '_')
    cmd = getattr(_cr, 'do_%s' % command)
    return cmd(**request.args)


@app.route('/analyzer/<command>')
def analyzer(command):
    command = command.replace('-', '_')
    cmd = getattr(_ar, 'do_%s' % command)
    return cmd(**request.args)

if __name__ == '__main__':
    print "starting toll road server"
    try:
        app.run()
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
