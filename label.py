import json
import os
from collections import defaultdict
from datetime import datetime
from os import path

import flask
from flask import Flask, render_template, request

import data_loaders

app = Flask(__name__)
app.config.from_pyfile(os.environ['FLASK_CONFIG'])
data_loader = data_loaders.get_data_loader(app.config['DATA_LOADER'])(
    **app.config['DATA_LOADER_CONFIG'])

TEMPLATES = ['single_frame', 'online', 'context']

@app.route('/<template>')
def labeler(template):
    samples = data_loader.sample(
        num_samples_per_label=app.config['NUM_SAMPLES_PER_LABEL'],
        seed=app.config['SEED'],
        pre_context=app.config['PRE_CONTEXT'],
        post_context=app.config['POST_CONTEXT'])
    form_template = ''
    labels = data_loader.labels()
    for sample in samples:
        form_template += render_template(
            template + '.html',
            labels=sorted(labels.items(), key=lambda x: x[1]),
            pre_context=['video/%s/%s' % (sample.filename, frame)
                         for frame in sample.pre_context],
            post_context=['video/%s/%s' % (sample.filename, frame)
                          for frame in sample.post_context],
            frame_path='video/%s/%s' % (sample.filename, sample.frame),
            video=sample.filename,
            frame=sample.frame)
    return render_template('index.html', form=form_template, template=template)


@app.route('/submit_<template>', methods=['POST'])
def submit(template):
    # Since we use the same seed, we will get the same samples as when the form
    # for labeling was generated.
    samples = data_loader.sample(
        num_samples_per_label=app.config['NUM_SAMPLES_PER_LABEL'],
        seed=app.config['SEED'],
        pre_context=app.config['PRE_CONTEXT'],
        post_context=app.config['POST_CONTEXT'])
    labels = data_loader.labels()
    responses = defaultdict(lambda: [''], request.form)
    # label_to_id = {label: label_id for label_id, label in labels.items()}
    output = []
    for sample in samples:
        if sample.frame == 267 and sample.filename == 'video_test_0000549':
            print(sample)
            print({x: y
                   for x, y in responses.items() if x.startswith(sample.filename)
                   })
        predictions = [label_id
                       for label_id in labels
                       if responses['%s-%s-%s' % (
                           sample.filename, sample.frame, label_id)][0] == 'on'
                       ]
        if predictions:
            print(sample, predictions)
        label_name_to_id = {label: label_id
                            for label_id, label in labels.items()}
        output.append({
            'filename': sample.filename,
            'frame': sample.frame,
            'groundtruth': [label_name_to_id[x] for x in sample.labels],
            'predictions': predictions})
    output_file = '%s-%s-%s' % (app.config['EXPERIMENT_PREFIX'], template,
                                datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    with open(output_file, 'w') as f:
        json.dump(output, f)
    return render_template('form_response.html', output_file=output_file)

@app.route('/video/<video_name>/<frame_number>')
def frame(video_name, frame_number):
    frame_dir, frame_filename = data_loader._frame_dir_name(video_name,
                                                            int(frame_number))
    return flask.send_from_directory(frame_dir, frame_filename)

if __name__ == '__main__':
    app.run()
