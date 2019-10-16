"""Label boxes in a video with class labels."""

import collections
import itertools
import json
import math
import shutil
from pathlib import Path

import numpy as np

from .single_file import SingleFileLabeler
from ..label_stores.grouped_label_store import GroupedLabelStore
from ..utils.fs import VIDEO_EXTENSIONS


class VideoBoxClassification(SingleFileLabeler):
    def __init__(self,
                 root,
                 boxes_json,
                 labels_csv,
                 output_dir,
                 num_items=10,
                 extensions=VIDEO_EXTENSIONS):
        """
        Args:
            boxes_json (str, Path): JSON file of the form
                {
                    <video_key>: {
                        <box_key>: {
                            'boxes': { <step>: [x0, y0, w, h], ... },
                            'color': <css-color>  // optional
                        }, ...
                    }, ...
                }
        """
        if isinstance(boxes_json, dict):
            self.boxes = boxes_json
        else:
            with open(boxes_json, 'r') as f:
                self.boxes = json.load(f)

        super().__init__(root,
                         extensions,
                         labels_csv,
                         output_dir,
                         template='video_box_classification.html',
                         num_items=num_items)

    def init_with_keys(self,
                       root,
                       keys,
                       labels_csv,
                       output_dir,
                       num_items=10,
                       review_labels=None):
        grouped_keys = {
            k: set(self.boxes[k].keys())
            for k in keys if k in self.boxes
        }

        self.root = Path(root)
        self.labels = SingleFileLabeler.load_label_spec(labels_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.label_store = GroupedLabelStore(
            grouped_keys=grouped_keys,
            extra_fields=['notes', 'other_labels'],
            labels=[x.name for x in self.labels],
            output_json=self.output_dir / 'labels.json',
            initial_labels=review_labels,
            initial_keys_only=review_labels is not None)

        self.num_items = num_items

        output_labels_csv = self.output_dir / Path(labels_csv).name
        if output_labels_csv.exists():
            old_spec = SingleFileLabeler.load_label_spec(output_labels_csv)
            assert old_spec == self.labels, (
                f'Labels from previous run at {output_labels_csv} do not '
                f'match labels provided at {labels_csv}')
        else:
            shutil.copy2(labels_csv, self.output_dir)

    def update_template_args(self, template_kwargs):
        template_kwargs = template_kwargs.copy()
        template_kwargs['video_boxes'] = {}
        for escaped_key, _, _ in template_kwargs['to_label']:
            key = self.unescape_key(escaped_key)
            template_kwargs['video_boxes'][escaped_key] = {
                self.escape_key(k): v
                for k, v in self.boxes[key].items()
            }
        template_kwargs['video_steps'] = {}
        return template_kwargs

    def parse_form(self, form):
        # request.form is a dictionary that maps from '<file>__<label_id>' to
        # 'on' if the user labeled this file as containing label id.
        label_infos = collections.defaultdict(lambda: {
            'notes': None,
            'labels': {},
            'other_labels': {}
        })
        vocabulary = {
            x: i
            for i, x in enumerate(self.label_store.valid_labels)
        }
        for key, value in form.items():
            video_key, info_key = key.rsplit('__', 2)
            video_key = self.unescape_key(video_key)
            if info_key == 'notes':
                label_infos[video_key]['notes'] = value
            else:
                box_key = self.unescape_key(info_key)
                assert box_key not in label_infos[video_key]['labels']
                assert box_key not in label_infos[video_key]['other_labels']
                label_infos[video_key]['labels'][box_key] = []
                label_infos[video_key]['other_labels'][box_key] = []

                all_labels = value.split(',')
                labels = []  # Labels from expected vocabulary
                other_labels = []
                for label in all_labels:
                    if label in vocabulary:
                        labels.append(vocabulary[label])
                    else:
                        other_labels.append(label)
                label_infos[video_key]['labels'][box_key] = labels
                label_infos[video_key]['other_labels'][box_key] = other_labels
        return label_infos


class CocoVideoBoxClassification(VideoBoxClassification):
    """Like VideoBoxClassification, but with COCO-style annotations input."""
    def __init__(self,
                 root,
                 coco_json,
                 vocabulary_json,
                 labels_csv,
                 output_dir,
                 add_other_category=True,
                 annotation_fps=1,
                 num_items=10,
                 extensions=VIDEO_EXTENSIONS):
        with open(coco_json, 'r') as f:
            data = json.load(f)
        with open(vocabulary_json, 'r') as f:
            self.vocabulary = json.load(f)['categories']
        for c in self.vocabulary:
            c['text'] = c['name']

        """
        COCO format:
        {
            'images': [{
                'id': int,
                'file_name': str,
                'frame_index': int,
                'video': str,
                ...
            }, ...],
            'annotations': [{
                'bbox': [x0, y0, w, h],
                'track_id': int,
                'image_id': int,
                ...
            }, ...]
        }
        Boxes format:
            {
                <video_key>: {
                    <box_key>: {
                        'boxes': { <step>: [x0, y0, w, h], ... },
                        'color': <css-color>  // optional
                    }, ...
                }, ...
            }
        """
        images = {}
        for image in data['images']:
            images[image['id']] = (image['video'], image['file_name'],
                                   image['frame_index'])

        root = Path(root)
        video_colors = collections.defaultdict(lambda: itertools.cycle(
            colormap(rgb=True)))
        boxes = {}

        video_info = {}
        for annotation in data['annotations']:
            video, frame_name, frame_index = images[annotation['image_id']]
            if not (root / video).exists():
                # Add extension if necessary
                try:
                    ext = next(x for x in VIDEO_EXTENSIONS
                               if (root / f'{video}{x}').exists())
                except StopIteration:
                    raise ValueError(f'Could not find video {video} in {root}')
                video = f'{video}{ext}'
            if video not in video_info:
                video_info[video] = get_video_info(str(root / video))
            track_id = str(annotation['track_id'])
            box = annotation['bbox']
            if video not in boxes:
                boxes[video] = {}
            if track_id not in boxes[video]:
                boxes[video][track_id] = {
                    'boxes': {},
                    'color': next(video_colors[video])
                }
            step_index = int(
                round(frame_index / video_info[video]['fps'] * annotation_fps))
            boxes[video][track_id]['boxes'][str(step_index)] = box

        self.video_steps = {}
        for video, info in video_info.items():
            frames_between_steps = int(round(info['fps'])) * annotation_fps
            step_to_time = {}
            step_frames = list(
                range(0, math.ceil(info['duration'] * info['fps']),
                      frames_between_steps))
            for step, frame in enumerate(step_frames):
                step_to_time[step] = frame / info['fps']
            if 'I0' in video:
                print('Duration', info['duration'], 'fps', info['fps'],
                      'step frames', step_frames, 'len', len(step_frames))
            self.video_steps[video] = step_to_time
        super().__init__(root, boxes, labels_csv, output_dir, num_items,
                         extensions)

    def update_template_args(self, template_kwargs):
        template_kwargs = template_kwargs.copy()
        template_kwargs['vocabulary'] = self.vocabulary
        template_kwargs = super().update_template_args(template_kwargs)
        template_kwargs['video_steps'] = self.video_steps
        return template_kwargs


def get_video_info(video):
    from moviepy.video.io.ffmpeg_reader import ffmpeg_parse_infos
    info = ffmpeg_parse_infos(video)
    return {
        'duration': info['duration'],
        'fps': info['video_fps'],
        'size': info['video_size']
    }


def colormap(rgb=False):
    color_list = np.array(
        [
            0.000, 0.447, 0.741,
            0.850, 0.325, 0.098,
            0.929, 0.694, 0.125,
            0.494, 0.184, 0.556,
            0.466, 0.674, 0.188,
            0.301, 0.745, 0.933,
            0.635, 0.078, 0.184,
            0.300, 0.300, 0.300,
            0.600, 0.600, 0.600,
            1.000, 0.000, 0.000,
            1.000, 0.500, 0.000,
            0.749, 0.749, 0.000,
            0.000, 1.000, 0.000,
            0.000, 0.000, 1.000,
            0.667, 0.000, 1.000,
            0.333, 0.333, 0.000,
            0.333, 0.667, 0.000,
            0.333, 1.000, 0.000,
            0.667, 0.333, 0.000,
            0.667, 0.667, 0.000,
            0.667, 1.000, 0.000,
            1.000, 0.333, 0.000,
            1.000, 0.667, 0.000,
            1.000, 1.000, 0.000,
            0.000, 0.333, 0.500,
            0.000, 0.667, 0.500,
            0.000, 1.000, 0.500,
            0.333, 0.000, 0.500,
            0.333, 0.333, 0.500,
            0.333, 0.667, 0.500,
            0.333, 1.000, 0.500,
            0.667, 0.000, 0.500,
            0.667, 0.333, 0.500,
            0.667, 0.667, 0.500,
            0.667, 1.000, 0.500,
            1.000, 0.000, 0.500,
            1.000, 0.333, 0.500,
            1.000, 0.667, 0.500,
            1.000, 1.000, 0.500,
            0.000, 0.333, 1.000,
            0.000, 0.667, 1.000,
            0.000, 1.000, 1.000,
            0.333, 0.000, 1.000,
            0.333, 0.333, 1.000,
            0.333, 0.667, 1.000,
            0.333, 1.000, 1.000,
            0.667, 0.000, 1.000,
            0.667, 0.333, 1.000,
            0.667, 0.667, 1.000,
            0.667, 1.000, 1.000,
            1.000, 0.000, 1.000,
            1.000, 0.333, 1.000,
            1.000, 0.667, 1.000,
            0.167, 0.000, 0.000,
            0.333, 0.000, 0.000,
            0.500, 0.000, 0.000,
            0.667, 0.000, 0.000,
            0.833, 0.000, 0.000,
            1.000, 0.000, 0.000,
            0.000, 0.167, 0.000,
            0.000, 0.333, 0.000,
            0.000, 0.500, 0.000,
            0.000, 0.667, 0.000,
            0.000, 0.833, 0.000,
            0.000, 1.000, 0.000,
            0.000, 0.000, 0.167,
            0.000, 0.000, 0.333,
            0.000, 0.000, 0.500,
            0.000, 0.000, 0.667,
            0.000, 0.000, 0.833,
            0.000, 0.000, 1.000,
            0.000, 0.000, 0.000,
            0.143, 0.143, 0.143,
            0.286, 0.286, 0.286,
            0.429, 0.429, 0.429,
            0.571, 0.571, 0.571,
            0.714, 0.714, 0.714,
            0.857, 0.857, 0.857,
            1.000, 1.000, 1.000
        ]
    ).astype(np.float32)
    color_list = color_list.reshape((-1, 3)) * 255
    if not rgb:
        color_list = color_list[:, ::-1]
    color_list = [
        "#{0:02x}{1:02x}{2:02x}".format(r, g, b)
        for r, g, b in color_list.astype(int)
    ]
    print(color_list[:10])
    return color_list
