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
from dal import CsvHandler, Data

__author__ = 'sekely'

requests.packages.urllib3.disable_warnings()
DEST = '32.051070, 34.785303'
ORIGIN = '32.000955, 34.845297'

class Collector(object):
    __metaclass__ = Singleton
    headers = ['timestamp', 'price', 'traffic']
    started = False
    last_update = None

    handler = CsvHandler()
    csv_file = property(lambda self: self.handler.data_file)
    api_key = None

    @csv_file.setter
    def csv_file(self, f_name):
        self.handler.data_file = f_name

    def get_price(self):
        r = requests.get('https://www.fastlane.co.il/mobile.aspx', verify=False)
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
        r = requests.get(base_url, params=payload, verify=False)
        resp = json.loads(r.text)
        value = resp['rows'][0]['elements'][0]['duration_in_traffic']['value']
        return int(value)

    @scheduled(60)
    @safe
    def start_sampling(self):
        if not self.started:
            raise ServerStopped()
        data = Data()
        data.price = self.get_price()
        if self.api_key:
            data.traffic = self.get_traffic()
        else:
            data.traffic = None
        self.handler.save_data(data)
        self.last_update = data.timestamp

    def do_start(self, *args, **kwargs):
        if not self.started:
            self.started = True
            t = Thread(target=self.start_sampling)
            t.start()
        return 'collector started\n'

    def _status(self):
        return True if datetime.datetime.now() - self.last_update <= datetime.timedelta(minutes=1) else False

    def do_stop(self, *args, **kwargs):
        self.started = False
        return 'stopping collector\n'

    def do_config(self, *args, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val[0])
        return 'finished collector config\n'

    def do_describe(self, *args, **kwargs):
        ret = {'csv_file': self.handler.data_file,
               'started': self.started,
               'last_update': self.last_update,
               'commands': [x.split('do_')[-1].replace('_', '-') for x in dir(self) if 'do_' in x],
               'status': self._status()}
        return flask.jsonify(ret)
