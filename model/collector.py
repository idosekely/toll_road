import csv
import datetime
import json
import os
from threading import Thread

from BeautifulSoup import BeautifulSoup
import flask
import requests

from pytools.asynx import scheduled
from infra import ServerStopped, Singleton, safe

__author__ = 'sekely'

requests.packages.urllib3.disable_warnings()
DEST = '32.051070, 34.785303'
ORIGIN = '32.000955, 34.845297'

class Collector(object):
    __metaclass__ = Singleton
    headers = ['timestamp', 'price', 'traffic']
    started = False
    last_update = None

    _csv = None
    csv_file = property(lambda self: self._csv)
    api_key = None

    @csv_file.setter
    def csv_file(self, csv_file):
        self._csv = csv_file
        if not os.path.isfile(self._csv):
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
    @safe
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
        self.last_update = datetime.datetime.now()

    def do_start(self, *args, **kwargs):
        if not self.started:
            self.started = True
            t = Thread(target=self.start_sampling)
            t.start()
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
               'started': self.started,
               'last_update': self.last_update,
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x]}
        return flask.jsonify(ret)