"""Filter labels.json based on label criteria."""

import argparse
import collections
import csv
import json
import logging
from pathlib import Path
from pprint import pformat

from script_utils.common import common_setup


def load_labels(input_paths):
    # Map data to list of (input_path, label) tuples.
    labels = collections.defaultdict(list)
    labels_list = None
    for path in input_paths:
        with open(path, 'r') as f:
            annotations = json.load(f)
            for i, row in enumerate(annotations['annotations']):
                labels[row['key']].append((path, row))
            if labels_list is None:
                labels_list = annotations['labels']
            else:
                assert labels_list == annotations['labels']

    for key, key_labels in labels.items():
        if len(key_labels) > 1:
            paths = [x[0] for x in key_labels]
            logging.debug(
                f'{key} labeled multiple times in {paths}; using latest '
                f'label from {paths[-1]}.')
        labels[key] = key_labels[-1][1]
    return labels, labels_list


def filter_labels(labels,
                  labels_list,
                  file_logger=None,
                  must_have=[],
                  must_not_have=[],
                  can_have=[],
                  must_have_one_of=False,
                  unspecified_labels_policy='error',
                  return_nonmatching=False):
    if file_logger is None:
        file_logger = logging.getLogger()

    label_map = {}
    label_names = {}
    for i, label in enumerate(labels_list):
        label_map[label] = i
        label_names[i] = label

    def validate_label(label):
        if label not in label_map:
            raise ValueError('Unknown label %s, valid labels: %s' %
                             (label, label_map.keys()))
        return True

    must_have_labels = set(
        [label_map[x] for x in must_have if validate_label(x)])
    must_not_have_labels = set(
        [label_map[x] for x in must_not_have if validate_label(x)])
    can_have_labels = set(
        [label_map[x] for x in can_have if validate_label(x)])

    unspecified_labels = (
        set(label_map.values()) -
        (must_have_labels | must_not_have_labels | can_have_labels))
    if unspecified_labels:
        if unspecified_labels_policy == 'error':
            raise ValueError('Label(s): %s were not specified in any of '
                             '--{must,must-not,can}-have.' %
                             [label_names[x] for x in unspecified_labels])
        elif unspecified_labels_policy == 'can-have':
            can_have_labels |= unspecified_labels
        elif unspecified_labels_policy == 'must-have':
            must_have_labels |= unspecified_labels
        elif unspecified_labels_policy == 'must-not-have':
            must_not_have_labels |= unspecified_labels
        else:
            raise ValueError('Unknown unspecified_labels_policy %s' %
                             unspecified_labels_policy)

    logging.info('Looking for rows that')
    if must_have_one_of:
        logging.info('MUST HAVE (one of): %s',
                     [label_names[x] for x in must_have_labels])
    else:
        logging.info('MUST HAVE: %s',
                     [label_names[x] for x in must_have_labels])
    logging.info('MUST NOT HAVE: %s',
                 [label_names[x] for x in must_not_have_labels])
    logging.info('CAN HAVE: %s', [label_names[x] for x in can_have_labels])

    valid_rows = []
    invalid_rows = []
    for key, row in labels.items():
        row_labels = set(row['labels'])
        missing_labels = must_have_labels - row_labels
        unwanted_labels = row_labels & must_not_have_labels
        if must_have_one_of:
            if missing_labels == must_have_labels:
                file_logger.info('Label %s missing labels %s' % (pformat(
                    dict(row)), [label_names[x] for x in missing_labels]))
                invalid_rows.append(row)
                continue
        elif missing_labels:
            file_logger.info(
                'Label %s missing labels %s' %
                (pformat(dict(row)), [label_names[x] for x in missing_labels]))
            invalid_rows.append(row)
            continue
        if unwanted_labels:
            file_logger.info(
                'Label %s has unwanted labels %s' %
                (pformat(dict(row)), [label_names[x]
                                      for x in unwanted_labels]))
            invalid_rows.append(row)
            continue
        valid_rows.append(row)
    if return_nonmatching:
        return valid_rows, invalid_rows
    else:
        return valid_rows


def main():
    # Use first line of file docstring as description if it exists.
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n')[0] if __doc__ else '',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--input-labels', nargs='+', required=True)
    parser.add_argument('--output-labels', type=Path, required=True)
    parser.add_argument(
        '--must-have',
        nargs='*',
        default=[],
        help=('Labels that must be present. Note that each label must be '
              'in one of --must-have, --must-not-have, or --can-have.'))
    parser.add_argument(
        '--must-not-have',
        nargs='*',
        default=[],
        help='Labels that must not be present.')
    parser.add_argument(
        '--can-have',
        nargs='*',
        default=[],
        help=('Labels that can be present. While this could be inferred from '
              '--must-have and --must-not-have, explicitly specifying it '
              'forces double-checking and helps catch accidentally forgetting '
              'about a label.'))
    parser.add_argument(
        '--must-have-one-of',
        action='store_true',
        help=('If true, only one (not all) of --must-have labels needs to be '
              'present.'))
    parser.add_argument(
        '--unspecified-labels',
        choices=['error', 'can-have', 'must-have', 'must-not-have'],
        default='error',
        help='What to do about labels not specified in flags.')
    args = parser.parse_args()

    args.output_labels.parent.mkdir(exist_ok=True, parents=True)
    file_logger = common_setup(
        args.output_labels.name + '_' + Path(__file__).name,
        args.output_labels.parent, args)
    logging.info('Args:\n%s', vars(args))

    labels, labels_list = load_labels(args.input_labels)
    valid_rows = filter_labels(labels, labels_list, file_logger,
                               args.must_have, args.must_not_have,
                               args.can_have, args.must_have_one_of,
                               args.unspecified_labels)
    logging.info(
        '%s/%s rows matched criterion' % (len(valid_rows), len(labels)))
    with open(args.output_labels, 'w') as f:
        json.dump({'annotations': valid_rows, 'labels': labels_list}, f)


if __name__ == "__main__":
    main()
