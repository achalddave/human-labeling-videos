from .single_image import SingleImageLabeler
from .single_video import SingleVideoLabeler

labeler_dict = {
    'SingleImageLabeler': SingleImageLabeler,
    'SingleVideoLabeler': SingleVideoLabeler
}