#!/usr/bin/python
import sys
from optparse import OptionParser
from uuid import uuid4

from flask import Flask
from flask import request
from flask import render_template

from model.analyzer import Analyzer
from model.infra import parse_single_arg
from model.collector import Collector

__author__ = 'sekely'

app = Flask(__name__)

_ar = Analyzer()
_cr = Collector()

class Request(object):
    requests = {}

    @classmethod
    def set_request(cls, request, **kwargs):
        uuid = uuid4().hex[:8]
        cls.requests[uuid] = dict(request.args)
        if kwargs:
            cls.requests[uuid].update(kwargs)
        return uuid

    @classmethod
    def get_request(cls, uuid):
        return cls.requests.pop(uuid)


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
    kwargs = dict(request.args)
    uuid = parse_single_arg('request_id', kwargs)
    if uuid:
        kwargs = Request.get_request(uuid)
    command = command.replace('-', '_')
    cmd = getattr(_ar, 'do_%s' % command)
    return cmd(**kwargs)


@app.route('/plot')
def plot():
    command = parse_single_arg('plot', request.args, default_val='raw-data')
    uuid = Request.set_request(request, columns_data=True)
    return render_template('chart.html', command=command, req_id=uuid)

if __name__ == '__main__':
    print "starting toll road server"
    options, _ = get_parser()
    try:
        app.run(host=options.host, port=options.port)
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
