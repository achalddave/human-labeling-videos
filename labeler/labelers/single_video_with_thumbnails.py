from labeler.labelers.single_file import SingleVideoLabeler
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
        template_args = {
            'num_thumbnails': num_thumbnails,
            'require_first_thumbnail': (
                'true' if require_first_thumbnail else 'false')
        }
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=extensions,
                         output_dir=output_dir,
                         template='label_video_with_thumbnails.html',
                         template_extra_args=template_args,
                         num_items=num_items)
