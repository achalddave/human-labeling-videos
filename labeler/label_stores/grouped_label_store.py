"""JSON label store for grouped ."""

import json
import random
from pathlib import Path

from natsort import natsorted

from .json_label_store import JsonLabelStore


class GroupedLabelStore(JsonLabelStore):
    """Stores grouped labels in a JSON file.

    Structure of JSON file:
    {
        "annotations": [
            {
                "key": str,  # group key
                "labels": { <key>: List[int]), ... },
                [extra_fields]: ...
            }, ...
        ],
        "labels": List[str]
    }
    """
    def __init__(self,
                 grouped_keys,
                 labels,
                 output_json=None,
                 extra_fields=[],
                 initial_labels=None,
                 initial_keys_only=False,
                 seed=0):
        """
        Args:
            grouped_keys (Dict[str, List[str]])
            <rest as in JsonLabelStore>
        """
        self.keys = {k: set(v) for k, v in grouped_keys.items()}
        self.valid_labels = labels
        self.extra_fields = extra_fields
        self.output = Path(output_json) if output_json is not None else None
        self.seed = seed

        if self.output is not None and self.output.exists():
            self._load_from_disk(self.output)
        else:
            # List of dicts of the form:
            #   {'key': str, 'labels': {<key>: List[int]}, <extra fields>}
            self.current_labels = []

        # We create an initial labels store only if `initial_labels` is
        # specified, or when `setup_initial_label` is called, to avoid creating
        # infinite recursive initial label stores.
        if initial_labels is not None:
            self.setup_initial_labels(initial_labels,
                                      initial_keys_only=initial_keys_only)
        else:
            self.initial_labels = None

    def _check_annotation(self, annotation):
        key = annotation['key']
        assert key in self.keys, (
            f"Could not find key {key} from previously saved labels in "
            f"current list of keys to label.")

        labeled_subkeys = set(annotation['labels'].keys())
        expected_subkeys = self.keys[key]
        if labeled_subkeys != expected_subkeys:
            unlabeled = expected_subkeys - labeled_subkeys
            unexpected = labeled_subkeys - expected_subkeys
            if unlabeled:
                raise ValueError(
                    f"For key {key}, subkeys {unlabeled} were expected "
                    f"but not labeled.")
            if unexpected:
                raise ValueError(
                    f"For key {key}, found unexpected subkeys {unexpected}"
                    f" in provided labels.")

        assert all(0 <= int(x) < len(self.valid_labels)
                   for y in annotation['labels'].values() for x in y)
        assert set(annotation.keys()) == set(['labels', 'key'] +
                                             self.extra_fields)

    def _remove_noninitial_keys(self, initial_labels_path):
        with open(initial_labels_path, 'r') as f:
            # TODO(achald): Consider removing keys within groups that are not
            # initially labeled. Currently, we keep all keys for a group which
            # is in the initial label.
            keys = {
                x['key']: self.keys[x['key']]
                for x in json.load(f)['annotations']
            }
        self.initial_labels.keys = keys
        self.keys = keys
        self.initial_labels.current_labels = [
            x for x in self.initial_labels.current_labels if x['key'] in keys
        ]

    def update(self, labels):
        """
        Args:
            labels (dict): Map group key to dict containing
                {'labels': {<key>: List[int], ...}, [extra_fields]: ...}
        """
        for key, label_info in labels.items():
            annotation = {'key': key}
            for k, v in label_info.items():
                annotation[k] = v
            self._check_annotation(annotation)
            self.current_labels.append(annotation)
        self._dump_to_disk()

    def update_initial_labels(self, labels):
        """
        Args:
            labels (dict): Map group key to dict containing
                {'labels': {<key>: List[int], ...}, [extra_fields]: ...}
        """
        return super().update_initial_labels(labels)

    def get_unlabeled(self, num_items, randomized=True):
        unlabeled = natsorted(set(self.keys.keys()) - self.labeled_keys())
        if randomized:
            random.Random(self.seed).shuffle(unlabeled)
        return unlabeled[:num_items]
