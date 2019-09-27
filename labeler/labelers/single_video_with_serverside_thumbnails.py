import collections
import csv
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Optional

import flask
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image

from labeler.labelers.single_image import SingleFileLabeler
from labeler.label_stores.json_label_store import JsonLabelStore
from labeler.utils.fs import VIDEO_EXTENSIONS
from labeler.utils import video as video_utils


class SingleVideoWithThumbnailsLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 num_thumbnails=10,
                 thumb_duration=0,  # Set to 0 to generate image thumbnails
                 extensions=VIDEO_EXTENSIONS):
        super().__init__(root, extensions, labels_csv, output_dir)
        self.num_thumbnails = num_thumbnails
        self.thumb_duration = thumb_duration
        self.thumbnail_dir = self.output_dir / 'thumbnails'
        self.thumbnail_dir.mkdir(exist_ok=True, parents=True)
        # ffmpeg starts failing if you have too many parallel instances of it
        # running (through moviepy).
        self._thumbnail_semaphore = threading.Semaphore(8)

    def public_directories(self):
        dirs = {
            'thumb': str(self.thumbnail_dir)
        }
        dirs.update(super().public_directories())
        return dirs

    def thumbnail_to_url(self, key):
        relative = str(Path(key).relative_to(self.thumbnail_dir))
        return f'/file/thumb/{relative}'

    def get_thumbnail(self, video, index):
        with self._thumbnail_semaphore:
            return self._get_thumbnail_unsafe(video, index)

    def _get_thumbnail_unsafe(self, video, index):
        video = self.url_to_key(video)
        relative = video.relative_to(self.root)
        thumbnail_dir = self.thumbnail_dir / relative
        thumbnail_dir.mkdir(exist_ok=True, parents=True)

        assert video.exists(), f'{video} does not exist.'
        clip = VideoFileClip(str(video))
        num_frames = video_utils.num_frames(video)
        num_thumbnails = min(self.num_thumbnails, num_frames)

        thumbnail_frames = [
            round(i * num_frames / (num_thumbnails + 2))
            for i in range(num_thumbnails + 2)
        ]
        # Remove first and last frame.
        thumbnail_frames = thumbnail_frames[1:-1]
        frame = thumbnail_frames[index]

        duration = self.thumb_duration
        thumb_type = "mp4" if duration > 0 else "jpg"
        output_thumbnail = thumbnail_dir / (f'frame-{frame:04d}_{duration}s.' +
                                            thumb_type)
        if not output_thumbnail.exists():
            t = frame / clip.fps
            if duration > 0:
                subclip = clip.subclip(t - duration / 2, t + duration / 2)
                subclip.write_videofile(str(output_thumbnail), audio=False)
            else:
                Image.fromarray(clip.get_frame(t)).save(output_thumbnail)
        print(f'Finished generating thumbnail for {video} @ {index}')
        return self.thumbnail_to_url(output_thumbnail)

    def api(self, api_request):
        try:
            request, params = api_request.split('/', 1)
        except ValueError:
            flask.abort(404)

        if request == 'thumbnail':
            thumbnail_index = int(params.split('/')[-1])
            video = '/'.join(params.split('/')[:-1])
            return flask.redirect(self.get_thumbnail(video, thumbnail_index))
        else:
            flask.abort(404)

    def key_to_thumb_urls(self, key):
        video = self.key_to_url(key)
        return [
            f'/api/thumbnail/{video}/{i}' for i in range(self.num_thumbnails)
        ]

    def index(self):
        video_keys = self.label_store.get_unlabeled(self.num_items)
        total_videos = self.label_store.num_total()
        num_complete = self.label_store.num_completed()
        percent_complete = 100 * num_complete / max(total_videos, 1e-9)
        videos_to_label = [(key, self.key_to_url(key),
                            self.key_to_thumb_urls(key),
                            self.label_store.get_initial_label(key))
                           for key in video_keys]
        return flask.render_template(
            'label_video_with_serverside_thumbnails.html',
            num_left=total_videos - num_complete,
            num_total=total_videos,
            percent_complete='%.2f' % percent_complete,
            to_label=videos_to_label,
            image_thumbnails=self.thumb_duration == 0,
            labels=self.labels_by_row())
