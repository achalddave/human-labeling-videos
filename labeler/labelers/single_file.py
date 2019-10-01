import collections
import csv
import shutil
from pathlib import Path
from typing import NamedTuple, Optional

from flask import abort, render_template

from labeler.labelers.base import Labeler
from labeler.label_stores.json_label_store import JsonLabelStore
from labeler.utils.fs import get_files, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


class LabelSpec(NamedTuple):
    idx: int
    name: str
    description_short: str
    description_long: str
    keyboard: str
    ui_row: int
    color: Optional[str] = None
    extra: Optional[dict] = None


class SingleFileLabeler(Labeler):
    def __init__(self,
                 root,
                 extensions,
                 labels_csv,
                 output_dir,
                 template=None,
                 template_extra_args={},
                 num_items=10,
                 review_labels=None):
        keys = [
            str(x.relative_to(root))
            for x in get_files(Path(root), extensions)
        ]
        self.init_with_keys(root, keys, labels_csv, output_dir, num_items,
                            review_labels)
        self.template = template
        self.template_extra_args = template_extra_args

    def init_with_keys(self,
                       root,
                       keys,
                       labels_csv,
                       output_dir,
                       num_items=10,
                       review_labels=None):
        self.root = Path(root)
        self.labels = SingleFileLabeler.load_label_spec(labels_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.label_store = JsonLabelStore(
            keys=map(str, keys),
            extra_fields=['notes'],
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

    def public_directories(self):
        return {
            'file': self.root
        }

    def key_to_url(self, key):
        key_path = Path(key)
        if key_path.is_absolute():
            relative = str(key_path.relative_to(self.root))
        else:
            relative = str(key_path)
        return f'/file/file/{relative}'

    def url_to_key(self, url):
        relative = url.split('/file/file/')[1]
        return self.root / relative

    def parse_form(self, form):
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
        return label_infos

    def submit(self, form):
        self.label_store.update(self.parse_form(form))

    def labels_by_row(self):
        labels_by_row = collections.defaultdict(list)
        for label in self.labels:
            labels_by_row[label.ui_row].append(label)
        return [
            labels_by_row[row] for row in sorted(labels_by_row.keys())
        ]

    @staticmethod
    def load_label_spec(csv_path):
        labels = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append(
                    LabelSpec(name=row.pop('name'),
                              keyboard=row.pop('keyboard'),
                              idx=int(row.pop('index')),
                              description_short=row.pop('description_short'),
                              description_long=row.pop('description_long'),
                              ui_row=row.pop('row', 0),
                              color=row.pop('color'),
                              extra=row))
        return labels

    def update_template_args(self, template_kwargs):
        return template_kwargs

    def index(self):
        if self.template is None:
            abort(404)

        keys = self.label_store.get_unlabeled(self.num_items)
        total = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = '%.2f' % (100 * num_complete / total)

        to_label = [(key, self.key_to_url(key),
                     self.label_store.get_initial_label(key)) for key in keys]
        template_kwargs = {
            'num_left': total - num_complete,
            'num_total': total,
            'percent_complete': percent_complete,
            'to_label': to_label,
            'labels': self.labels_by_row(),
        }
        template_kwargs = self.update_template_args(template_kwargs)
        return render_template(self.template,
                               **template_kwargs,
                               **self.template_extra_args)


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
                         template='label_single_image.html',
                         review_labels=review_labels)


class SingleVideoLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 num_items=10,
                 extensions=VIDEO_EXTENSIONS):
        super().__init__(root,
                         extensions,
                         labels_csv,
                         output_dir,
                         template='label_single_video.html',
                         num_items=num_items)
