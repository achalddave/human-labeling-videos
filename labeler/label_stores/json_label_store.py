import json
import random
from pathlib import Path

from labeler.label_stores.base import LabelStore


class JsonLabelStore(LabelStore):
    """Stores labels in a JSON file.

    Structure of JSON file:
    {
        "annotations": {
            [
                "key": str,
                "labels": List[int],
                [extra_fields]: ...
            ], ...
        },
        "labels": List[str],
        ...
    }
    """
    def __init__(self, keys, labels, output_json, extra_fields=[], seed=0):
        """
        Args:
            keys (List[str])
            labels (List[str])
            output_json (str)
            extra_fields (List[str])
            seed (int)
        """
        self.keys = set(keys)
        self.valid_labels = labels
        self.extra_fields = extra_fields
        self.output = Path(output_json)
        self.seed = seed
        if self.output.exists():
            self._load_from_disk()
        else:
            self.current_labels = []

    def _load_from_disk(self):
        with open(self.output, 'r') as f:
            data = json.load(f)
        assert set(data.keys()) == {'annotations', 'labels'}

        assert data['labels'] == self.valid_labels

        for annotation in data['annotations']:
            key = annotation['key']
            assert key in self.keys, (
                f"Could not find key {key} from previously saved labels in "
                f"current list of keys to label.")
            assert all(0 <= int(x) < len(self.valid_labels)
                       for x in annotation['labels'])
            assert set(annotation.keys()) == set(['labels', 'key'] +
                                                 self.extra_fields)

        self.current_labels = data['annotations']

    def _dump_to_disk(self):
        with open(self.output, 'w') as f:
            json.dump(
                {
                    'annotations': self.current_labels,
                    'labels': self.valid_labels
                }, f)

    def get_latest_label(self, key):
        matches = (x for x in reversed(self.current_labels) if x['key'] == key)
        try:
            return next(matches)
        except StopIteration:
            return None

    def update(self, labels):
        """
        Args:
            labels (dict): Map data key to dict containing
                {'labels': List[int], [extra_fields]: ...}
        """
        for key, label_info in labels.items():
            annotation = {'key': key}
            for k, v in label_info.items():
                if k == 'labels' or k in self.extra_fields:
                    annotation[k] = v
                else:
                    print('WARN: Ignoring unknown field: ', k)
            self.current_labels.append(annotation)
        self._dump_to_disk()

    def get_unlabeled(self, num_items):
        unlabeled = sorted(self.keys -
                           set([x['key'] for x in self.current_labels]))
        random.Random(self.seed).shuffle(unlabeled)
        return unlabeled[:num_items]

    def num_completed(self):
        return len({x['key'] for x in self.current_labels})

    def num_total(self):
        return len(self.keys)
