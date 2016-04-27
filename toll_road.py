#!/usr/bin/env python
import sys
import os
from optparse import OptionParser
from uuid import uuid4

from flask import Flask
from flask import request
from flask import render_template
from flask import send_from_directory
from flask import jsonify
from werkzeug import secure_filename

from model.analyzer import Analyzer
from model.infra import parse_single_arg
from model.collector import Collector

__author__ = 'sekely'
ALLOWED_EXTENSIONS = ['txt', 'csv', 'hdf5']

app = Flask(__name__)
app.config.from_object('config.Production')
app.config['ROOT_FOLDER'], _ = os.path.split(app.instance_path)

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


@app.route('/data/<command>', methods=['GET', 'POST'])
def data(command):
    def handle_file():
        f_name = request.args.get('file_name')
        path = app.config['UPLOAD_FOLDER']
        if not f_name:
            path, f_name = os.path.split(_cr.csv_file)
        return path, f_name

    def _set_data_file(path, f_name):
        _file = os.path.join(path, f_name)
        _cr.csv_file = _file
        _ar.csv_file = _file

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

    if request.method == 'GET':
        if command == 'set':
            path, f_name = handle_file()
            _set_data_file(path, f_name)
            return 'data file set to %s\n' % f_name
        elif command == 'download':
            path, f_name = handle_file()
            return send_from_directory(path, f_name, as_attachment=True)
        elif command == 'upload':
            return render_template('upload_file.html')
        elif command == 'list':
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            files = [f for f in files if allowed_file(f)]
            return render_template('file_list.html', file_list=files)

    if request.method == 'POST':
        file = request.files['data_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return "File Saved!\n"


def run():
    csv_path = app.config.get('CSV_PATH')
    _cr.api_key = app.config.get('API_KEY')
    _cr.csv_file = csv_path
    _ar.csv_file = csv_path
    _cr.do_start()
    app.run(host=options.host, port=options.port)

if __name__ == '__main__':
    print "starting toll road server"
    options, _ = get_parser()
    try:
        run()
    except KeyboardInterrupt as e:
        print "shutting down sampling"
        sys.exit(0)
    sys.exit(1)
