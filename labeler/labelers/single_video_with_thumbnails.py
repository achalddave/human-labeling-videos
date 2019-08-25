from flask import render_template

from labeler.labelers.single_video import SingleVideoLabeler
from labeler.utils.fs import VIDEO_EXTENSIONS


class SingleVideoWithThumbnailsLabeler(SingleVideoLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 num_thumbnails=5,
                 require_first_thumbnail=False,
                 extensions=VIDEO_EXTENSIONS,
                 num_items=10):
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=extensions,
                         output_dir=output_dir,
                         num_items=num_items)
        self.require_first_thumbnail = require_first_thumbnail
        self.num_thumbnails = num_thumbnails

    def index(self):
        video_keys = self.label_store.get_unlabeled(self.num_items)
        total_videos = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = 100 * num_complete / max(total_videos, 1e-9)
        return render_template(
            'label_video_with_thumbnails.html',
            num_left_videos=total_videos - num_complete,
            num_total_videos=total_videos,
            num_thumbnails=self.num_thumbnails,
            percent_complete='%.2f' % percent_complete,
            videos_to_label=[(key, self.key_to_url(key), None)
                             for key in video_keys],
            require_first_thumbnail=('true' if self.require_first_thumbnail
                                     else 'false'),
            labels=[x for x in self.labels])
