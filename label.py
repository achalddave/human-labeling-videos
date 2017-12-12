from __future__ import division

import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from os import path

import flask
from flask import Flask, render_template, request

import data_loaders

app = Flask(__name__)
app.config.from_pyfile(os.environ['FLASK_CONFIG'])
data_loader = data_loaders.get_data_loader(app.config['DATA_LOADER'])(
    **app.config['DATA_LOADER_CONFIG'])

TEMPLATES = ['single_frame', 'online_partial', 'online', 'context', 'context_partial']

@app.route('/')
def index():
    return render_template('index.html', templates=TEMPLATES)

@app.route('/<template>')
def labeler(template):
    samples = data_loader.sample(**app.config['DATA_LOADER_SAMPLE_ARGS'])
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
    return render_template('labeler.html', form=form_template, template=template)


@app.route('/submit_<template>', methods=['POST'])
def submit(template):
    # Since we use the same seed, we will get the same samples as when the form
    # for labeling was generated.
    samples = data_loader.sample(**app.config['DATA_LOADER_SAMPLE_ARGS'])
    labels = data_loader.labels()
    responses = defaultdict(lambda: [''], request.form)
    output = []
    for sample in samples:
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
    output_file = '%s/%s-%s-%s-seed-%s' % (
        app.config['RESULTS_DIR'], app.config['EXPERIMENT_PREFIX'], template,
        datetime.now().strftime('%Y-%m-%d-%H-%M-%S'), app.config['SEED'])
    with open(output_file, 'w') as f:
        json.dump(output, f)
    return render_template('form_response.html', output_file=output_file)


@app.route('/view_results/<results_file>')
def results(results_file):
    with open('%s/%s' % (app.config['RESULTS_DIR'], results_file)) as f:
        results = json.load(f)

    label_names = data_loader.labels()
    correctly_predicted = Counter()
    total_predicted = Counter()
    total_true = Counter()
    results_view = []
    for labeled_frame in results:
        true_labels = set(label_names[x] for x in labeled_frame['groundtruth'])
        predicted_labels = set(label_names[x]
                               for x in labeled_frame['predictions'])

        true_positive = list(true_labels & predicted_labels)
        false_positive = list(predicted_labels - true_labels)
        false_negative = list(true_labels - predicted_labels)
        results_view.append({
            'path': '/video/%s/%s' % (labeled_frame['filename'], labeled_frame[
                'frame']),
            'true_positive': true_positive,
            'false_positive': false_positive,
            'false_negative': false_negative
        })

        for label in true_labels:
            correctly_predicted[label] += label in predicted_labels
            total_true[label] += 1
        for label in predicted_labels:
            total_predicted[label] += 1

    precisions = []
    recalls = []
    for label in sorted(label_names.values()):
        precisions.append(100 * correctly_predicted[label] / total_predicted[
            label] if total_predicted[label] != 0 else 0)
        recalls.append(100 * correctly_predicted[label] / total_true[label])
    accuracy = 100 * sum(correctly_predicted.values()) / sum(total_true.values(
    ))
    mean_precision = sum(precisions) / len(precisions)
    mean_recall = sum(recalls) / len(recalls)
    return render_template(
        'results.html',
        precision_recalls=zip(
            sorted(label_names.values()), precisions, recalls),
        precision=mean_precision,
        recall=mean_recall,
        results=results_view,
        accuracy=accuracy)


@app.route('/video/<video_name>/<frame_number>')
def frame(video_name, frame_number):
    frame_dir, frame_filename = data_loader._frame_dir_name(video_name,
                                                            int(frame_number))
    return flask.send_from_directory(frame_dir, frame_filename)

if __name__ == '__main__':
    app.run()
