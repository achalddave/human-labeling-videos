"""Remove labels in one CSV from another CSV."""

import argparse
import csv
import logging
from pathlib import Path

from labeler.utils.log import setup_logging


def main():
    with open(__file__, 'r') as f:
        _source = f.read()

    # Use first line of file docstring as description if it exists.
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n')[0] if __doc__ else '',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--input-labels-csv', required=True)
    parser.add_argument('--to-remove-csv', required=True)
    parser.add_argument('--output-csv', required=True)

    args = parser.parse_args()
    setup_logging(args.output_csv + '.log')
    logging.info('Path to script: %s' % Path(__file__).resolve())
    logging.info('Args:\n%s', vars(args))

    to_remove_videos = set()
    with open(args.to_remove_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            to_remove_videos.add(row['video'])

    output_data = []
    with open(args.input_labels_csv, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['video'] not in to_remove_videos:
                output_data.append(row)

    with open(args.output_csv, 'w') as f:
        fieldnames = ['video', 'labels', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_data:
            writer.writerow(row)

    file_logger = logging.getLogger(args.output_csv + '.log')
    file_logger.info('Source:')
    file_logger.info(_source)


if __name__ == "__main__":
    main()
