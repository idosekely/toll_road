#!/usr/bin/python
import datetime
import csv
import sys
from optparse import OptionParser
import json

import requests
from BeautifulSoup import BeautifulSoup

from pytools.asynx import scheduled

import pandas as pd
import matplotlib.pylab as plt
import statsmodels.api as sm

__author__ = 'sekely'

requests.packages.urllib3.disable_warnings()
DEFAULT_CSV = '/tmp/toll_road.csv'
DEST = '32.051070, 34.785303'
ORIGIN = '32.000955, 34.845297'


class TollRoad(object):
    headers = ['timestamp', 'price', 'traffic']

    def __init__(self, options):
        self.csv_file = options.filename
        self.api_key = options.api_key
        if not options.append:
            self.create_csv_file()

    def create_csv_file(self):
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

    @scheduled(60)
    def start_sampling(self):
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


class Analyzer(object):
    def __init__(self, f_name):
        self.f_name = f_name

    def extract_data(self, drop_na=False):
        dateparse = lambda dates: pd.datetime.strptime(dates, '%Y-%m-%d %H:%M:%S.%f')
        df = pd.read_csv(self.f_name, parse_dates='timestamp', index_col='timestamp', date_parser=dateparse)
        df['traffic'] = df['traffic'].apply(lambda x: x / 60.)
        self.df = df.resample('T').mean()
        if drop_na:
            self.df.dropna(inline=True)
        else:
            self.df.interpolate(inplace=True)

    def test_stationarity(self, col):
        # Determing rolling statistics
        ts = self.df[col]
        rolmean = ts.rolling(window=12).mean()
        rolstd = ts.rolling(window=12).std()

        # Plot rolling statistics:
        orig = plt.plot(ts, color='blue', label='Original')
        mean = plt.plot(rolmean, color='red', label='Rolling Mean')
        std = plt.plot(rolstd, color='black', label='Rolling Std')
        plt.legend(loc='best')
        plt.title('Rolling Mean & Standard Deviation')
        plt.show(block=False)

        # Perform Dickey-Fuller test:
        print 'Results of Dickey-Fuller Test:'
        dftest = sm.tsa.adfuller(ts.dropna(), autolag='AIC')
        dfoutput = pd.Series(dftest[0:4],
                             index=['Test Statistic', 'p-value', '#Lags Used', 'Number of Observations Used'])
        for key, value in dftest[4].items():
            dfoutput['Critical Value (%s)' % (key,)] = value
        print dfoutput

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

    def summary(self):
        return self.df.describe()


def get_parser():
    parser = OptionParser()
    parser.add_option('-f', '--file', dest='filename', default=DEFAULT_CSV,
                      help='filename to which to save the samples')
    parser.add_option('-g', '--google-api-key', dest='api_key', help='use google api for traffic smapling')
    parser.add_option('-a', '--append', dest='append', help='append to file', action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    option, _ = get_parser()
    print "starting toll road server"
    try:
        tr = TollRoad(option)
        tr.start_sampling()
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
