import copy
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
    def __init__(self,
                 keys,
                 labels,
                 output_json=None,
                 extra_fields=[],
                 initial_labels=None,
                 seed=0):
        """
        Args:
            keys (List[str])
            labels (List[str])
            output_json (str)
            extra_fields (List[str])
            initial_labels (Path): JSON output by, e.g., a previous labeling
                session.
            seed (int)
        """
        self.keys = set(keys)
        self.valid_labels = labels
        self.extra_fields = extra_fields
        self.output = Path(output_json) if output_json is not None else None
        self.seed = seed

        if self.output is not None and self.output.exists():
            self._load_from_disk(self.output)
        else:
            self.current_labels = []

        # Initial labels maintains an "initial" label for each sample that is
        # presented to the user when annotating. The user can either keep this
        # label, or update it.
        #
        # We create an initial labels store only if `initial_labels` is
        # specified, or when `set_initial_label` is called, to avoid creating
        # infinite recursive initial label stores.
        if initial_labels is not None:
            self.setup_initial_labels(initial_labels)
        else:
            self.initial_labels = None

    def setup_initial_labels(self, labels_path=None):
        if self.output is not None:
            output_json = self.output.with_name(self.output.stem +
                                                "_initial.json")
        self.initial_labels = JsonLabelStore(self.keys,
                                             self.valid_labels,
                                             output_json=output_json,
                                             extra_fields=self.extra_fields,
                                             seed=self.seed)
        if labels_path is not None:
            self.initial_labels._load_from_disk(labels_path)
            if output_json.exists():
                self.initial_labels._load_from_disk(output_json)

    def _load_from_disk(self, output):
        with open(output, 'r') as f:
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
        if self.output is None:
            return

        with open(self.output, 'w') as f:
            json.dump(
                {
                    'annotations': self.current_labels,
                    'labels': self.valid_labels
                }, f)

    def get_label(self, key):
        matches = (x for x in reversed(self.current_labels) if x['key'] == key)
        try:
            return copy.deepcopy(next(matches))
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

    def get_initial_label(self, key):
        if self.initial_labels is not None:
            return self.initial_labels.get_label(key)
        else:
            return None

    def update_initial_labels(self, labels):
        """
        Args:
            labels (dict): Map data key to dict containing
                {'labels': List[int], [extra_fields]: ...}
        """
        if self.initial_labels is None:
            print('Setting up initial labels')
            self.setup_initial_labels()
        return self.initial_labels.update(labels)

    def labeled_keys(self):
        return {x['key'] for x in self.current_labels}

    def get_unlabeled(self, num_items):
        unlabeled = sorted(self.keys - self.labeled_keys())
        random.Random(self.seed).shuffle(unlabeled)
        return unlabeled[:num_items]

    def num_completed(self):
        return len({x['key'] for x in self.current_labels})

    def num_total(self):
        return len(self.keys)
