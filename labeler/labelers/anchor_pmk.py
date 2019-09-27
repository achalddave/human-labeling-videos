"""Label anchor frame and pm-k frame."""

import collections
import json
from pathlib import Path

from flask import render_template

from .single_image_with_captions import SingleImageWithCaptionsLabeler


class AnchorPmkLabeler(SingleImageWithCaptionsLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 pair_caption_json,
                 num_items=10,
                 review_labels=None,
                 anchor_bad_name='bad-anchor'):
        """
        pair_caption_json (Path): Maps "<anchor-path>,<pmk-path>" to image
            caption, where the paths are relative from the root directory.
        """
        with open(pair_caption_json, 'r') as f:
            pair_captions = json.load(f)
            self.pair_captions = {
                tuple(k.split(',')): v
                for k, v in pair_captions.items()
            }

        self.keys_by_anchor = collections.defaultdict(list)
        keys = []
        for anchor, pmk in self.pair_captions.keys():
            key = self.create_key(anchor, pmk)
            keys.append(key)
            self.keys_by_anchor[anchor].append(key)
        self.init_with_keys(root,
                            keys,
                            labels_csv,
                            output_dir,
                            num_items,
                            review_labels=review_labels)
        self.propagate_labels = {
            x.idx
            for x in self.labels if int(x.extra.get('propagate_anchors', '0'))
        }
        self.anchor_bad_label = next(x.idx for x in self.labels
                                     if x.name == anchor_bad_name)

    def create_key(self, anchor_path, pmk_path):
        return f'{anchor_path},{pmk_path}'

    def parse_key(self, key):
        return tuple(key.split(','))

    def index(self):
        anchor_pmk_keys = self.label_store.get_unlabeled(self.num_items)
        total_images = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        captions = {
            key: self.pair_captions[self.parse_key(key)]
            for key in anchor_pmk_keys
        }
        labels_by_row = self.labels_by_row()

        # Hack: Sort categories row
        category_row_idx = next(i for i, row in enumerate(labels_by_row)
                                if any(x.name == 'person' for x in row))
        category_row = labels_by_row[category_row_idx]
        row1 = [category_row[0]] + sorted(category_row[1:],
                                          key=lambda x: x.name)
        labels_by_row[category_row_idx] = row1

        pairs_to_label = []
        for key in anchor_pmk_keys:
            anchor, pmk = self.parse_key(key)
            anchor_url = self.key_to_url(anchor)
            pmk_url = self.key_to_url(pmk)
            pairs_to_label.append(
                (key, anchor_url, pmk_url,
                 self.label_store.get_initial_label(key), captions[key]))

        return render_template('label_anchor_pmk_with_captions.html',
                               num_left=total_images - num_complete,
                               num_total=total_images,
                               percent_complete='%.2f' %
                               (100 * num_complete / total_images),
                               pairs_to_label=pairs_to_label,
                               labels=labels_by_row)

    def submit(self, form):
        label_infos = self.parse_form(form)
        # Map anchor to dict {'add': add_labels, 'remove': remove_labels},
        # indicating which labels to add and remove for each anchor.
        to_propagate = {}
        for key, value in label_infos.items():
            anchor, pmk = self.parse_key(key)
            labels = set(value['labels'])

            # If a previous row in this page called this anchor bad, add
            # anchor bad to this pmk pair as well.
            if (anchor in to_propagate
                    and self.anchor_bad_label in to_propagate[anchor]):
                labels.add(self.anchor_bad_label)

            to_propagate[anchor] = {
                'add': self.propagate_labels & labels,
                'remove': self.propagate_labels - labels
            }

        self.label_store.update(self.parse_form(form))

        print(f"Propagating labels:\n{to_propagate}")
        final_updates = {}
        initial_updates = {}
        for anchor, updates in to_propagate.items():
            # Propagate to all pm-k frames for given anchor.
            keys = self.keys_by_anchor[anchor]
            for anchor_pmk_key in keys:
                annotation = self.label_store.get_label(anchor_pmk_key)
                # Update the final annotation if the pair is already annotated,
                # or we are propagating anchor bad. Otherwise, update the
                # initial annotation.
                if (self.anchor_bad_label in updates['add']
                        and annotation is None):
                    annotation = {
                        'labels': [],
                        'notes': 'Propagated anchor bad.'
                    }

                if annotation is not None:
                    annotation['labels'] = sorted(
                        set(annotation['labels']) | updates['add'] -
                        updates['remove'])
                    final_updates[anchor_pmk_key] = annotation
                else:
                    initial_updates[anchor_pmk_key] = {
                        'labels': sorted(updates['add']),
                        'notes': ''
                    }
        if final_updates:
            print('final', final_updates)
            self.label_store.update(final_updates)
        if initial_updates:
            print('initial', final_updates)
            self.label_store.update_initial_labels(initial_updates)
