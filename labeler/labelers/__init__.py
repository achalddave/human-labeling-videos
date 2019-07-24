from .single_image import SingleImageLabeler
from .single_video import SingleVideoLabeler
from .single_video_with_thumbnails import SingleVideoWithThumbnailsLabeler

labeler_dict = {
    'SingleImageLabeler': SingleImageLabeler,
    'SingleVideoLabeler': SingleVideoLabeler,
    'SingleVideoWithThumbnailsLabeler': SingleVideoWithThumbnailsLabeler
}