import argparse
from pathlib import Path

from script_utils.common import common_setup

from labeler.filter_labels import load_labels


def main():
    # Use first line of file docstring as description if it exists.
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n')[0] if __doc__ else '',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('labels_json', nargs='+')
    parser.add_argument('output_txt', type=Path)

    args = parser.parse_args()
    args.output_txt.parent.mkdir(exist_ok=True, parents=True)
    common_setup(
        args.output_txt.name + '_' + Path(__file__).name,
        args.output_txt.parent, args)
    labels, _ = load_labels(args.labels_json)

    keys = sorted(labels.keys())
    with open(args.output_txt, 'w') as f:
        f.write('\n'.join(keys) + '\n')


if __name__ == "__main__":
    main()
