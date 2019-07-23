"""Image labeler interface."""
import os
from pathlib import Path

import flask
from flask import Flask, abort, redirect, request

from labeler.labelers import labeler_dict

app = Flask(__name__)
if 'FLASK_CONFIG' not in os.environ:
    raise ValueError('Please specify FLASK_CONFIG in environment.')
app.config.from_pyfile(os.environ['FLASK_CONFIG'])

cfg = app.config

labeler = labeler_dict[cfg['LABELER_TYPE']](**cfg['LABELER_ARGS'])


@app.route('/')
def index():
    return labeler.index()


@app.route('/submit', methods=['POST'])
def submit():
    output = labeler.submit(request.form)
    if not output:
        output = redirect('/')
    return output


@app.route('/api/<api_request>')
def api(api_request):
    return labeler.api(api_request)


@app.route('/file/<path:path>')
def file(path):
    key, path = path.split('/', 1)
    public_directories = labeler.public_directories()
    if key not in public_directories:
        abort(404)
    full_path = Path(public_directories[key]) / path
    return flask.send_from_directory(full_path.parent, full_path.name)
