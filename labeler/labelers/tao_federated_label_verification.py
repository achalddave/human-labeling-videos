import json
import logging
from collections import defaultdict
from pathlib import Path

from flask import abort, render_template

from labeler.labelers.single_file import SingleFileLabeler, LabelSpec
from labeler.label_stores.json_label_store import JsonLabelStore


class TaoFederatedLabelVerifier(SingleFileLabeler):
    def __init__(self,
                 video_root,
                 tao_annotations,
                 video_queries,
                 output_dir,
                 template='label_tao_federated.html',
                 template_extra_args={},
                 num_items=10):
        self.root = video_root
        with open(tao_annotations, 'r') as f:
            tao = json.load(f)

        self.label_specs = []
        labels_by_name = {}
        for c in tao['categories']:
            description = (
                f'Synset: {c["synset"]},\n'
                f'Definition: {c["def"]},\n'
                f'Synonyms: {",".join(c["synonyms"])}')

            def get_name(x):
                return x['name'] if x['name'] != 'baby' else 'person'

            name = get_name(c)
            description_short = name
            if 'merged' in c:
                description_short += ' / ' + (' / '.join(
                    get_name(x) for x in c['merged']))
                description += '\nMerged categories:'
                for merged_cat in c['merged']:
                    description += (
                        f'\n{merged_cat["name"]}\n'
                        f'\tSynset: {merged_cat["synset"]},\n'
                        f'\tDefinition: {merged_cat["def"]},\n'
                        f'\tSynonyms: {",".join(merged_cat["synonyms"])}')
            label_spec = LabelSpec(name=c['synset'],
                                   ui_row=0,
                                   keyboard=None,
                                   idx=c['id'],
                                   description_short=description_short,
                                   description_long=description)
            self.label_specs.append(label_spec)
            labels_by_name[name] = label_spec

        with open(video_queries, 'r') as f:
            self.video_query_names = json.load(f)

        self.keys = []
        # Map key to list of LabelSpec's to query annotator for.
        self.label_query_map = {}
        missing = 0
        for video in tao['videos']:
            if video['name'] not in self.video_query_names:
                missing += 1
                continue
            key = video['name'] + '.mp4'
            self.keys.append(key)
            queries = self.video_query_names[video['name']]
            self.label_query_map[key] = [labels_by_name[x] for x in queries]
        logging.warning(f'{missing} videos had no queries.')

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        labels = [
            f'{x.name}+{y}' for x in self.label_specs
            for y in ('exhaustive', 'present', 'absent')
        ]
        labels = []
        # Map from, e.g., "{label_spec.idx}+exhaustive" to index in labels
        self.label_ids = {}
        for x in self.label_specs:
            for y in ('exhaustive', 'present', 'absent'):
                assert '+' not in x.name
                self.label_ids[f'{x.idx}+{y}'] = len(labels)
                labels.append(f'{x.name}+{y}')
        self.label_store = JsonLabelStore(keys=map(str, self.keys),
                                          extra_fields=['notes'],
                                          labels=labels,
                                          output_json=self.output_dir /
                                          'labels.json',
                                          initial_labels=None,
                                          initial_keys_only=False)

        self.num_items = num_items

        self.template = template
        self.template_extra_args = template_extra_args

    def index(self):
        if self.template is None:
            abort(404)

        keys = self.label_store.get_unlabeled(self.num_items)
        total = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = '%.2f' % (100 * num_complete / total)

        to_label = [(self.escape_key(key), self.key_to_url(key),
                     self.label_query_map[key],
                     self.label_store.get_initial_label(key)) for key in keys]
        template_kwargs = {
            'num_left': total - num_complete,
            'num_total': total,
            'percent_complete': percent_complete,
            'to_label': to_label,
        }
        template_kwargs = self.update_template_args(template_kwargs)
        return render_template(self.template,
                               **template_kwargs,
                               **self.template_extra_args)

    def parse_form(self, form):
        # request.form is a dictionary that maps from '<file>__<label_id>' to
        # 'on' if the user labeled this file as containing label id.
        label_infos = defaultdict(lambda: {
            'notes': None,
            'labels': []
        })
        for key, value in form.items():
            file_key, info_key = key.rsplit('__', 1)
            file_key = self.unescape_key(file_key)
            if info_key == 'notes':
                label_infos[file_key]['notes'] = value
            else:
                if value != 'on':
                    raise ValueError(
                        'Unknown value %s in response for key %s' %
                        (value, key))
                label_infos[file_key]['labels'].append(
                    self.label_ids[info_key])
        return label_infos
