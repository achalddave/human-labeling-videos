"""Label boxes in a video with class labels."""

from .single_file import SingleFileLabeler
from labeler.utils.fs import VIDEO_EXTENSIONS


class VideoBoxClassification(SingleFileLabeler):
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
                         template='video_box_classification.html',
                         num_items=num_items)
