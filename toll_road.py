#!/usr/bin/python
import datetime
import csv
import sys
from optparse import OptionParser
import json

import requests
from BeautifulSoup import BeautifulSoup

from pytools.asynx import scheduled

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


def get_parser():
    parser = OptionParser()
    parser.add_option('-f', '--file', dest='filename', default=DEFAULT_CSV,
                      help='filename to which to save the samples')
    parser.add_option('-g', '--google-api-key', dest='api_key', help='use google api for traffic smapling')
    parser.add_option('-a', '--append', dest='append', help='append to file', action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    try:
        option, _ = get_parser()
        print "starting toll road server"
        tr = TollRoad(option)
        tr.start_sampling()
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
