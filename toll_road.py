#!/usr/bin/python
import sys
from optparse import OptionParser

from flask import Flask
from flask import request
from flask import render_template

from model.analyzer import Analyzer

from model.collector import Collector

__author__ = 'sekely'

app = Flask(__name__)

_ar = Analyzer()
_cr = Collector()


def get_parser():
    parser = OptionParser()
    parser.add_option('-a', '--address', dest='host', default='127.0.0.1', help='server hostname')
    parser.add_option('-p', '--port', dest='port', default=5000, help='server port')
    return parser.parse_args()


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

@app.route('/analyzer/plot/<command>')
def plot(command):
    cmd = getattr(_ar, 'do_%s' % command.replace('-', '_'))
    cmd(columns_data=True, **request.args)
    return render_template('chart.html', command=command)

if __name__ == '__main__':
    print "starting toll road server"
    options, _ = get_parser()
    try:
        app.run(host=options.host, port=options.port)
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
