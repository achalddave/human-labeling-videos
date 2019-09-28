from .anchor_pmk import AnchorPmkLabeler
from .single_file import (SingleImageLabeler, SingleVideoLabeler)
from .single_image_with_captions import SingleImageWithCaptionsLabeler
from .single_video_with_thumbnails import SingleVideoWithThumbnailsLabeler
from .grid_labeler import GridLabeler

labeler_dict = {
    'SingleImageLabeler': SingleImageLabeler,
    'SingleVideoLabeler': SingleVideoLabeler,
    'SingleVideoWithThumbnailsLabeler': SingleVideoWithThumbnailsLabeler,
    'SingleImageWithCaptionsLabeler': SingleImageWithCaptionsLabeler,
    'AnchorPmkLabeler': AnchorPmkLabeler,
    'GridLabeler': GridLabeler
}
