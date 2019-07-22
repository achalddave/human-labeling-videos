"""Image labeler interface."""
import collections
import configparser
import csv
import json
import os
import sys
import random
from pathlib import Path

import flask
from flask import Flask, render_template, redirect, request

sys.path.insert(0, '..')
from utils import imagenet_vid

app = Flask(__name__)
if 'FLASK_CONFIG' not in os.environ:
    raise ValueError('Please specify FLASK_CONFIG in environment.')
app.config.from_pyfile(os.environ['FLASK_CONFIG'])

# Fields in labels_list.csv, the CSV describing possible labels.
LABELS_LIST_FIELDS = [
    'index', 'keyboard', 'name', 'description_short', 'description_long', 'color'
]
LabelInfo = collections.namedtuple('LabelInfo',
                                   ['image', 'anchor', 'labels', 'notes'])

cfg = app.config


def load_labels(path):
    """Load image labels from a JSON file."""
    with open(path, 'r') as f:
        # Map image_key to dict containing 'labels', 'notes'
        data = json.load(f)
    return [
        LabelInfo(
            image=label['image'],
            anchor=label['anchor'],
            notes=label['notes'],
            labels=label['labels']) for label in data
    ]


IMAGES_ROOT = Path(cfg['IMAGENET_ROOT'] + '/Data/VID').expanduser().resolve()
ANNOTATIONS_ROOT = Path(cfg['IMAGENET_ROOT'] +
                        '/Annotations/VID').expanduser().resolve()
IMAGES_LIST_FILE = Path(cfg['IMAGES_LIST'])
OUTPUT_DIR = Path(cfg['OUTPUT_RESULTS_DIR'])
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
LABELS_OUT = OUTPUT_DIR / 'labels.json'
LABELS_LIST_OUT = OUTPUT_DIR / 'labels_list.csv'
CONFIG_OUT = OUTPUT_DIR / Path(os.environ['FLASK_CONFIG']).name

REVIEW_LABELS_PATH = cfg.get('REVIEW_LABELS', None)
if REVIEW_LABELS_PATH is None:
    REVIEW_LABELS = {}
    random.seed(cfg['SEED'])
    with open(IMAGES_LIST_FILE, 'r') as f:
        anchor_set_mapping = json.load(f)
        # List of (frame path, anchor frame path) relative to IMAGES_ROOT
        IMAGES = []
        for anchor, pmk_set in anchor_set_mapping.items():
            for to_label in pmk_set:
                to_label_absolute = IMAGES_ROOT / to_label
                anchor_absolute = IMAGES_ROOT / anchor
                assert to_label_absolute.exists(), (
                    f"Couldn't find image at {to_label_absolute.resolve()}")
                assert anchor_absolute.exists(), (
                    f"Couldn't find image at {anchor_absolute.resolve()}")
                IMAGES.append((to_label, anchor))
else:
    random.seed(cfg['SEED'])
    _raw_review_labels = load_labels(REVIEW_LABELS_PATH)
    REVIEW_LABELS = {(x.image, x.anchor): x
                     for x in _raw_review_labels}
    difference = len(_raw_review_labels) - len(REVIEW_LABELS)
    if difference:
        # The dictionary comprehension above will naturally keep the last label
        # in the _raw_review_labels list, and the list is ordered from oldest
        # to most recent label.
        print(f'Found {difference} duplicates in {REVIEW_LABELS_PATH}; '
              f'using newest label for each image.')
    IMAGES = list(REVIEW_LABELS.keys())
random.shuffle(IMAGES)



with open("../../metadata/imagenet_vid_class_index.json", "r+") as f:
    WNID_TO_HUMAN = {x[0]: x[1] for x in json.load(f).values()}


def read_config(path):
    """From flask `from_pyfile` function."""
    import types
    d = types.ModuleType('config')
    d.__file__ = path
    try:
        with open(path, mode='rb') as config_file:
            exec(compile(config_file.read(), path, 'exec'), d.__dict__)
    except IOError as e:
        e.strerror = 'Unable to load configuration file (%s)' % e.strerror
        raise
    output = {}
    for k in dir(d):
        if k.startswith('__'):
            continue
        output[k] = getattr(d, k)
    return output


if not CONFIG_OUT.exists():
    from shutil import copyfile
    copyfile(os.environ['FLASK_CONFIG'], CONFIG_OUT)
else:
    provided_cfg = read_config(os.environ['FLASK_CONFIG'])
    saved_cfg = read_config(CONFIG_OUT)
    if provided_cfg != saved_cfg:
        raise ValueError('Saved config did not match provided config.\n'
                         f'Saved: {saved_cfg}\n'
                         f'Provided: {provided_cfg}')

if REVIEW_LABELS_PATH is None:
    IMAGES_LIST_OUT = OUTPUT_DIR / Path(cfg['IMAGES_LIST']).name
    if not IMAGES_LIST_OUT.exists():
        from shutil import copyfile
        copyfile(cfg['IMAGES_LIST'], IMAGES_LIST_OUT)
    else:
        with open(IMAGES_LIST_OUT, 'r') as f:
            saved_images_list = json.load(f)
        with open(IMAGES_LIST_FILE, 'r') as f:
            provided_images_list = json.load(f)
        if provided_images_list != saved_images_list:
            raise ValueError('Saved images list did not match provided list')
else:
    REVIEW_LABELS_OUT = OUTPUT_DIR / Path(REVIEW_LABELS_PATH).name
    assert REVIEW_LABELS_OUT != LABELS_OUT
    if not REVIEW_LABELS_OUT.exists():
        from shutil import copyfile
        copyfile(REVIEW_LABELS_PATH, REVIEW_LABELS_OUT)
    else:
        with open(REVIEW_LABELS_OUT, 'r') as f:
            saved_review_list = json.load(f)
        with open(REVIEW_LABELS_PATH, 'r') as f:
            provided_review_list = json.load(f)
        if provided_review_list != saved_review_list:
            raise ValueError('Saved review list did not match provided list')


def object_area(obj):
    return (obj.box.x_max - obj.box.x_min) * (obj.box.y_max - obj.box.y_min)


def load_groundtruth(image_path):
    label_subpath = image_path.replace('.JPEG', '.xml')
    label_path = ANNOTATIONS_ROOT / label_subpath
    with label_path.open(mode="r") as f:
        label_data = f.read()
    label = imagenet_vid.parse_label(label_data)

    objects = sorted(label.objects, key=object_area, reverse=True)
    return list(set(WNID_TO_HUMAN[obj.wordnet_id] for obj in objects))


def get_label_key(label):
    """
    Args:
        label (LabelInfo)
    """
    return f"{label.image},{label.anchor}"


def load_labels_list(path):
    """Load list of potential labels from a CSV."""
    labels = {}
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        missing_keys = set(LABELS_LIST_FIELDS) - set(reader.fieldnames)
        unexpected_keys = set(LABELS_LIST_FIELDS) - set(reader.fieldnames)
        if missing_keys:
            raise ValueError(
                'Missing keys %s in label path %s' % (missing_keys, path))
        if unexpected_keys:
            raise ValueError(
                'Unexpected keys %s in label path %s' % (missing_keys, path))
        for row in reader:
            assert int(row['index']) not in labels, (
                'Index %s repeated in %s' % (row['index'], path))
            labels[int(row['index'])] = row
    labels_list = [None for _ in range(len(labels))]
    for i in range(len(labels)):
        if i not in labels:
            raise ValueError(
                'Labels %s do not have consecutive indices.' % labels)
        labels_list[i] = labels[i]
    return labels_list


# List containing labels with keys LABELS_LIST_FIELDS
LABELS_LIST = load_labels_list(cfg['LABELS_LIST_CSV'])
# Create a special label that allows marking all pm-k frames for this anchor
# with a 'bad' label.
BAD_ANCHOR_LABEL = [
    i for i, x in enumerate(LABELS_LIST) if x['name'] == 'bad-anchor'
][0]
BAD_ANCHORS = set()


def write_labels(labels, path):
    """
    Args:
        labels (list[LabelInfo])
        path (str)
    """
    labels = [{
        'image': l.image,
        'anchor': l.anchor,
        'notes': l.notes,
        'labels': l.labels
    } for l in labels]
    with open(path, 'w') as f:
        json.dump(labels, f, indent=True)


def write_labels_list(labels_list, path):
    with open(path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=LABELS_LIST_FIELDS)
        writer.writeheader()
        for label_info in labels_list:
            writer.writerow(label_info)


# HACK: Propagate anchor bad labels. During review mode, we only propagate the
# 'bad-anchor' label to frames that were marked for review. This means that
# if new frames were added for review after an anchor was marked as bad, they
# will show up in the review process again! Here, we propagate to the current
# set of "to-review" frames.
if REVIEW_LABELS_PATH is not None and LABELS_OUT.exists():
    labels = load_labels(LABELS_OUT)
    labels_map = {}  # Map (image, anchor) to labels
    # Map anchor to set of pm-k frames
    bad_anchors_pmk = collections.defaultdict(set)
    for label in labels:
        labels_map[(label.image, label.anchor)] = label
        if BAD_ANCHOR_LABEL in label.labels:
            bad_anchors_pmk[label.anchor].add(label.image)

    propagate_labels = []
    for pmk, anchor in IMAGES:
        if (pmk, anchor) in labels_map:
            # Already labeled in review, skip this frame.
            # Ensure that if the anchor is bad, the pm-k also has the
            # bad anchor label. This should have been ensured by the
            # label server (when an anchor is marked as bad, all pm-k
            # frames should have anchor bad marked.)
            assert anchor not in bad_anchors_pmk or (
                pmk in bad_anchors_pmk[anchor])
            continue
        elif anchor in bad_anchors_pmk:
            # Not labeled in review, but anchor was marked as bad!
            propagate_labels.append(
                LabelInfo(image=pmk,
                          anchor=anchor,
                          labels=[BAD_ANCHOR_LABEL]))
    if propagate_labels:
        if not ('ALLOW_PROPAGATE' in os.environ
                and os.environ['ALLOW_PROPAGATE']):
            raise ValueError(
                f'Found {len(propagate_labels)} to propagate, but '
                f'will not propagate as ALLOW_PROPAGATE is not set in '
                f'environment.')
        labels = labels + propagate_labels
        write_labels(labels, LABELS_OUT)
        print(f'Propagated bad anchor to {len(propagate_labels)} frames.')


@app.route('/')
def index():
    already_labeled = set()  # To be populated with images already labeled
    if LABELS_LIST_OUT.exists():
        output_labels_list = load_labels_list(LABELS_LIST_OUT)
        assert output_labels_list == LABELS_LIST, (
            "Labels in output directory (path: %s, labels: %s) "
            "don't match labels from config (path: %s, labels: %s)" %
            (LABELS_LIST_OUT, output_labels_list, cfg['LABELS_LIST_CSV'],
             LABELS_LIST))

        already_labeled = set(
            (x.image, x.anchor) for x in load_labels(LABELS_OUT))
    elif LABELS_OUT.exists():
        raise ValueError('{labels} exists but {labels_list} does not.'.format(
            labels=LABELS_OUT, labels_list=LABELS_LIST_OUT))

    unlabeled_images = [(image, anchor) for image, anchor in IMAGES
                        if (image, anchor) not in already_labeled]
    to_label = []
    for image, anchor in unlabeled_images[:cfg['IMAGES_PER_PAGE']]:
        image_key = f'{image},{anchor}'
        image_labels = ','.join(load_groundtruth(image))
        anchor_labels = ','.join(load_groundtruth(anchor))
        current_label = REVIEW_LABELS.get((image, anchor), None)
        if current_label is not None:
            current_label = ([str(x) for x in current_label.labels],
                             current_label.notes)
        to_label.append((image_key, f'/image/{image}', image_labels,
                         f'/image/{anchor}', anchor_labels, current_label))

    percent_complete = 100 * (1 - len(unlabeled_images) / len(IMAGES))
    return render_template(
        'label_image_anchor.html',
        num_left_images=len(unlabeled_images),
        num_total_images=len(IMAGES),
        percent_complete='%.2f' % percent_complete,
        images_to_label=to_label,
        labels=[(label['index'], label['keyboard'], label['color'],
                 label['description_short'], label['description_long'])
                for i, label in enumerate(LABELS_LIST)])


@app.route('/submit', methods=['POST'])
def submit():
    # request.form is a dictionary that maps from '<image>-<label_id>' to 'on'
    # if the user labeled this image as containing label id.
    label_infos = collections.defaultdict(lambda: {
        'notes': None,
        'labels': []
    })
    for key, value in request.form.items():
        image_anchor_key, info_key = key.split('__')
        if info_key == 'notes':
            label_infos[image_anchor_key]['notes'] = value
        else:
            if value != 'on':
                raise ValueError(
                    'Unknown value %s in response for key %s' % (value, key))
            label_id = int(info_key)
            if label_id < 0 or label_id > len(LABELS_LIST):
                raise ValueError('Unknown label %s for image %s' %
                                 (label_id, image_anchor_key))
            label_infos[image_anchor_key]['labels'].append(label_id)
    labels = [
        LabelInfo(
            image=image_anchor_key.split(',')[0],
            anchor=image_anchor_key.split(',')[1],
            notes=info['notes'],
            labels=info['labels'])
        for image_anchor_key, info in label_infos.items()
    ]

    # Propagate bad label to rest of video.
    new_labels = []
    for label in labels:
        if BAD_ANCHOR_LABEL in label.labels:
            problematic_anchor = label.anchor
            # Mark all frames from this anchor as having a bad anchor.
            to_remove = [
                image for image, anchor in IMAGES
                if anchor == problematic_anchor
            ]
            new_labels.extend([
                LabelInfo(image=image,
                          anchor=problematic_anchor,
                          labels=[BAD_ANCHOR_LABEL])
                for image in to_remove
            ])
    labels = labels + new_labels

    if LABELS_OUT.exists():
        earlier_labels = load_labels(LABELS_OUT)
    else:
        earlier_labels = []

    all_labels = earlier_labels.copy()
    already_labeled = set(get_label_key(x) for x in earlier_labels)
    for label in labels:
        image = get_label_key(label)
        if image in already_labeled:
            print('Relabeled image %s (this should not happen!).'
                  'Appending newest label.' % image)
        all_labels.append(label)
    write_labels(all_labels, LABELS_OUT)
    write_labels_list(LABELS_LIST, LABELS_LIST_OUT)

    # return 'Thanks! Your labels %s have been submitted.' % str(labels)
    return redirect('/')


@app.route('/image/<path:image_subpath>')
def image(image_subpath):
    image_subpath = Path(image_subpath)
    parent_dir = (IMAGES_ROOT / image_subpath.parent).resolve()
    return flask.send_from_directory(parent_dir, image_subpath.name)
