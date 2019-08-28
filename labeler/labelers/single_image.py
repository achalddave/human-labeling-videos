import collections
import csv
import shutil
from pathlib import Path
from typing import NamedTuple, Optional

from flask import render_template

from labeler.labelers.base import Labeler
from labeler.label_stores.json_label_store import JsonLabelStore
from labeler.utils.fs import get_files, IMAGE_EXTENSIONS


class LabelSpec(NamedTuple):
    idx: int
    name: str
    description_short: str
    description_long: str
    keyboard: str
    ui_row: int
    color: Optional[str] = None


class SingleFileLabeler(Labeler):
    def __init__(self,
                 root,
                 extensions,
                 labels_csv,
                 output_dir,
                 num_items=10,
                 review_labels=None):
        files = get_files(Path(root), extensions)
        self.init_with_files(root, files, labels_csv, output_dir, num_items,
                             review_labels)

    def init_with_files(self,
                        root,
                        files,
                        labels_csv,
                        output_dir,
                        num_items=10,
                        review_labels=None):
        self.root = Path(root)
        self.files = files
        self.labels = SingleFileLabeler.load_label_spec(labels_csv)
        if review_labels is None:
            self.review_labels = None
        else:
            self.review_labels = JsonLabelStore(
                keys=map(str, self.files),
                extra_fields=['notes'],
                labels=[x.name for x in self.labels],
                output_json=review_labels)
            review_keys = {x['key'] for x in self.review_labels.current_labels}
            self.review_labels.keys = review_keys
            self.files = sorted(review_keys)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.label_store = JsonLabelStore(
            keys=map(str, self.files),
            extra_fields=['notes'],
            labels=[x.name for x in self.labels],
            output_json=self.output_dir / 'labels.json')
        self.num_items = num_items

        output_labels_csv = self.output_dir / Path(labels_csv).name
        if output_labels_csv.exists():
            old_spec = SingleFileLabeler.load_label_spec(output_labels_csv)
            assert old_spec == self.labels, (
                f'Labels from previous run at {output_labels_csv} do not '
                f'match labels provided at {labels_csv}')
        else:
            shutil.copy2(labels_csv, self.output_dir)

    def public_directories(self):
        return {
            'file': self.root
        }

    def key_to_url(self, key):
        relative = str(Path(key).relative_to(self.root))
        return f'/file/file/{relative}'

    def url_to_key(self, url):
        relative = url.split('/file/file/')[1]
        return self.root / relative

    def submit(self, form):
        # request.form is a dictionary that maps from '<file>__<label_id>' to
        # 'on' if the user labeled this file as containing label id.
        label_infos = collections.defaultdict(lambda: {
            'notes': None,
            'labels': []
        })
        for key, value in form.items():
            file_key, info_key = key.rsplit('__', 1)
            if info_key == 'notes':
                label_infos[file_key]['notes'] = value
            else:
                if value != 'on':
                    raise ValueError(
                        'Unknown value %s in response for key %s' %
                        (value, key))
                label_infos[file_key]['labels'].append(int(info_key))
        self.label_store.update(label_infos)

    def labels_by_row(self):
        labels_by_row = collections.defaultdict(list)
        for label in self.labels:
            labels_by_row[label.ui_row].append(label)
        return [
            labels_by_row[row] for row in sorted(labels_by_row.keys())
        ]

    def review_annotation(self, key):
        if self.review_labels is None:
            return None
        else:
            return self.review_labels.get_latest_label(key)

    @staticmethod
    def load_label_spec(csv_path):
        labels = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append(
                    LabelSpec(name=row['name'],
                              keyboard=row['keyboard'],
                              idx=int(row['index']),
                              description_short=row['description_short'],
                              description_long=row['description_long'],
                              ui_row=row.get('row', 0),
                              color=row['color']))
        return labels


class SingleImageLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 extensions=IMAGE_EXTENSIONS,
                 review_labels=None):
        super().__init__(root,
                         extensions,
                         labels_csv,
                         output_dir,
                         review_labels=review_labels)

    def index(self):
        image_keys = self.label_store.get_unlabeled(self.num_items)
        total_images = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = '%.2f' % (100 * num_complete / total_images)

        images_to_label = [(key, self.key_to_url(key),
                            self.review_annotation(key)) for key in image_keys]
        return render_template('label_single_image.html',
                               num_left_images=total_images - num_complete,
                               num_total_images=total_images,
                               percent_complete=percent_complete,
                               images_to_label=images_to_label,
                               labels=self.labels_by_row())
