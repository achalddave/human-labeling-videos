import collections
import csv
from pathlib import Path
from typing import NamedTuple, Optional

from flask import render_template

from labeler.labelers.single_image import SingleFileLabeler
from labeler.label_stores.json_label_store import JsonLabelStore


class SingleVideoLabeler(SingleFileLabeler):
    VIDEO_EXTENSIONS = ('.mp4',)

    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 extensions=VIDEO_EXTENSIONS):
        super().__init__(root, extensions, labels_csv, output_dir)

    def index(self):
        video_keys = self.label_store.get_unlabeled(self.num_items)
        total_videos = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = 100 * num_complete / max(total_videos, 1e-9)
        return render_template('label_single_video.html',
                               num_left_videos=total_videos - num_complete,
                               num_total_videos=total_videos,
                               percent_complete='%.2f' % percent_complete,
                               videos_to_label=[(key, self.key_to_path(key),
                                                 None) for key in video_keys],
                               labels=[x for x in self.labels])