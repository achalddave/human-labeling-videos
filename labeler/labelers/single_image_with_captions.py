import json
from pathlib import Path

from flask import render_template

from ..label_stores.json_label_store import JsonLabelStore
from .single_image import SingleImageLabeler


class SingleImageWithCaptionsLabeler(SingleImageLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 image_caption_json,
                 num_items=10,
                 review_labels=None):
        """
        image_caption_json (Path): Maps relative path from root to image
            caption.
        """
        with open(image_caption_json, 'r') as f:
            self.image_captions = json.load(f)

        self.init_with_keys(root,
                            self.image_captions.keys(),
                            labels_csv,
                            output_dir,
                            num_items,
                            review_labels=review_labels)

    def index(self):
        image_keys = self.label_store.get_unlabeled(self.num_items)
        total_images = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        captions = {
            key: self.image_captions[str(Path(key).relative_to(self.root))]
            for key in image_keys
        }
        labels_by_row = self.labels_by_row()
        # Hack: Assume second row is categories, sort by name.
        row1 = labels_by_row[1]
        row1 = [row1[0]] + sorted(row1[1:], key=lambda x: x.name)
        labels_by_row[1] = row1

        images_to_label = [(key, self.key_to_url(key),
                            self.label_store.get_initial_label(key),
                            captions[key]) for key in image_keys]

        return render_template('label_single_image_with_captions.html',
                               num_left=total_images - num_complete,
                               num_total=total_images,
                               percent_complete='%.2f' %
                               (100 * num_complete / total_images),
                               to_label=images_to_label,
                               labels=labels_by_row)
