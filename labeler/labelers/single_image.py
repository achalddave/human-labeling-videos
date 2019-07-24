import collections
import csv
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
    color: Optional[str] = None


class SingleFileLabeler(Labeler):
    def __init__(self, root, extensions, labels_csv, output_dir):
        self.root = Path(root)
        self.files = get_files(self.root, extensions)
        self.labels = self.load_label_spec(labels_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.label_store = JsonLabelStore(
            keys=map(str, self.files),
            extra_fields=['notes'],
            labels=[x.name for x in self.labels],
            output_json=self.output_dir / 'labels.json')
        self.num_items = 10

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
            file_key, info_key = key.split('__')
            if info_key == 'notes':
                label_infos[file_key]['notes'] = value
            else:
                if value != 'on':
                    raise ValueError(
                        'Unknown value %s in response for key %s' %
                        (value, key))
                label_infos[file_key]['labels'].append(int(info_key))
        self.label_store.update(label_infos)

    def load_label_spec(self, csv_path):
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
                              color=row['color']))
        return labels


class SingleImageLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 extensions=IMAGE_EXTENSIONS):
        super.__init__(self, root, extensions, labels_csv, output_dir)

    def index(self):
        image_keys = self.label_store.get_unlabeled(self.num_items)
        total_images = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        return render_template(
            'label_single_image.html',
            num_left_images=total_images - num_complete,
            num_total_images=total_images,
            percent_complete='%.2f' % (100 * num_complete / total_images),
            images_to_label=[(key, self.key_to_url(key), None)
                             for key in image_keys],
            labels=[x for x in self.labels])
