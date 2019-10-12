"""Label boxes in a video with class labels."""

import collections
import json
import shutil
from pathlib import Path

from .single_file import SingleFileLabeler
from ..utils.fs import VIDEO_EXTENSIONS
from ..label_stores.grouped_label_store import GroupedLabelStore


class VideoBoxClassification(SingleFileLabeler):
    def __init__(self,
                 root,
                 boxes_json,
                 labels_csv,
                 output_dir,
                 num_items=10,
                 extensions=VIDEO_EXTENSIONS):
        """
        Args:
            boxes_json (str, Path): JSON file of the form
                {
                    <video_key>: {
                        <box_key>: {
                            'boxes': { <step>: [x0, y0, w, h], ... },
                            'color': <css-color>  // optional
                        }, ...
                    }, ...
                }
        """
        with open(boxes_json, 'r') as f:
            self.boxes = json.load(f)

        super().__init__(root,
                         extensions,
                         labels_csv,
                         output_dir,
                         template='video_box_classification.html',
                         num_items=num_items)

    def init_with_keys(self,
                       root,
                       keys,
                       labels_csv,
                       output_dir,
                       num_items=10,
                       review_labels=None):
        grouped_keys = {k: set(self.boxes.get(k, {}).keys()) for k in keys}

        self.root = Path(root)
        self.labels = SingleFileLabeler.load_label_spec(labels_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.label_store = GroupedLabelStore(
            grouped_keys=grouped_keys,
            extra_fields=['notes', 'other_labels'],
            labels=[x.name for x in self.labels],
            output_json=self.output_dir / 'labels.json',
            initial_labels=review_labels,
            initial_keys_only=review_labels is not None)

        self.num_items = num_items

        output_labels_csv = self.output_dir / Path(labels_csv).name
        if output_labels_csv.exists():
            old_spec = SingleFileLabeler.load_label_spec(output_labels_csv)
            assert old_spec == self.labels, (
                f'Labels from previous run at {output_labels_csv} do not '
                f'match labels provided at {labels_csv}')
        else:
            shutil.copy2(labels_csv, self.output_dir)

    def update_template_args(self, template_kwargs):
        template_kwargs = template_kwargs.copy()
        template_kwargs['video_boxes'] = {}
        for escaped_key, _, _ in template_kwargs['to_label']:
            key = self.unescape_key(escaped_key)
            template_kwargs['video_boxes'][escaped_key] = {
                self.escape_key(k): v
                for k, v in self.boxes[key].items()
            }
        return template_kwargs

    def parse_form(self, form):
        # request.form is a dictionary that maps from '<file>__<label_id>' to
        # 'on' if the user labeled this file as containing label id.
        label_infos = collections.defaultdict(lambda: {
            'notes': None,
            'labels': {},
            'other_labels': {}
        })
        vocabulary = {
            x: i
            for i, x in enumerate(self.label_store.valid_labels)
        }
        for key, value in form.items():
            print(key, value)
            video_key, info_key = key.rsplit('__', 2)
            video_key = self.unescape_key(video_key)
            if info_key == 'notes':
                label_infos[video_key]['notes'] = value
            else:
                box_key = self.unescape_key(info_key)
                assert box_key not in label_infos[video_key]['labels']
                assert box_key not in label_infos[video_key]['other_labels']
                label_infos[video_key]['labels'][box_key] = []
                label_infos[video_key]['other_labels'][box_key] = []

                all_labels = value.split(',')
                labels = []  # Labels from expected vocabulary
                other_labels = []
                for label in all_labels:
                    if label in vocabulary:
                        labels.append(vocabulary[label])
                    else:
                        other_labels.append(label)
                label_infos[video_key]['labels'][box_key] = labels
                label_infos[video_key]['other_labels'][box_key] = other_labels
        return label_infos
