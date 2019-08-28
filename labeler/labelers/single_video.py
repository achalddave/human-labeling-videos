import collections
import csv
from pathlib import Path
from typing import NamedTuple, Optional

from flask import render_template

from labeler.labelers.single_image import SingleFileLabeler
from labeler.label_stores.json_label_store import JsonLabelStore
from labeler.utils.fs import VIDEO_EXTENSIONS


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
                         num_items=num_items)

    def index(self):
        video_keys = self.label_store.get_unlabeled(self.num_items)
        total_videos = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = 100 * num_complete / max(total_videos, 1e-9)
        videos_to_label = [(key, self.key_to_url(key),
                            self.review_annotation(key)) for key in video_keys]
        return render_template('label_single_video.html',
                               num_left_videos=total_videos - num_complete,
                               num_total_videos=total_videos,
                               percent_complete='%.2f' % percent_complete,
                               videos_to_label=videos_to_label,
                               labels=self.labels_by_row())
