from __future__ import division

from random import Random
from collections import defaultdict
from math import floor, ceil

from intervaltree import Interval, IntervalTree
from .data_loader import DataLoader, FrameSample
from .thumos_util import parsing
from .thumos_util.video_tools.util import annotation
from .thumos_util.video_tools.util.annotation import Annotation


class MultiThumosDataLoader(DataLoader):
    def __init__(self, frames_dir, frames_per_second, annotations_json,
                 video_frames_info, class_list_path, ignore_negative_videos=True):
        # TODO (URGENT): Update to handle frames per second.
        self.frames_dir = frames_dir
        self._frames_per_second = frames_per_second
        self.label_map = parsing.load_class_mapping(class_list_path)
        self.random = Random()

        self.annotations = annotation.load_annotations_json(annotations_json)

        def convert_annotation(x):
            """Transform annotations to be in the right frame rate."""
            return Annotation(
                x.filename, ceil(x.start_seconds * self._frames_per_second),
                floor(x.end_seconds * self._frames_per_second), x.start_seconds,
                x.end_seconds, self._frames_per_second, x.category)

        for filename in list(self.annotations.keys()):
            self.annotations[filename] = [
                convert_annotation(x)
                for x in self.annotations[filename]
                if x.category in set(self.label_map.values())
            ]
            if ignore_negative_videos and not self.annotations[filename]:
                del self.annotations[filename]

        # Transform frame info to be in the right frame rate.
        self.video_frame_info = parsing.parse_frame_info_file(
            video_frames_info)
        for filename in list(self.video_frame_info.keys()):
            fps, num_frames = self.video_frame_info[filename]
            if filename not in self.annotations:
                del self.video_frame_info[filename]
            else:
                self.video_frame_info[filename] = (
                    self._frames_per_second,
                    int(floor(num_frames / fps * self._frames_per_second)))

        self.background_intervals = {}
        for filename, file_annotations in self.annotations.items():
            num_frames = self.video_frame_info[filename][1]
            background = IntervalTree([Interval(0, num_frames)])
            for a in file_annotations:
                background.chop(a.start_frame, a.end_frame + 1)
            self.background_intervals[filename] = background

    def _frame_dir_name(self, video, frame):
        return ('%s/%s/' % (self.frames_dir, video), 'frame%04d.png' % frame)

    def labels(self):
        return self.label_map

    def frames_per_second(self):
        return self._frames_per_second

    def sample_balanced(self,
                        num_samples_per_label,
                        num_background_samples,
                        seed=None,
                        pre_context=0,
                        post_context=0):
        if seed is not None:
            self.random.seed(seed)
        # TODO: Only do this once when the class is created. Only filter for
        # context validity in sample.
        label_to_annotations = defaultdict(list)
        for filename, file_annotations in self.annotations.items():
            num_frames = self.video_frame_info[filename][1]
            for a in file_annotations:
                if (a.start_frame + post_context >= num_frames or
                        a.end_frame - pre_context < 0):
                    # Ignore annotations that don't have enough room for
                    # context.
                    continue
                if a.category in self.label_map.values():
                    label_to_annotations[a.category].append(a)
        frame_samples = []
        for label, annotations in sorted(label_to_annotations.items()):
            sampled_segments = self.random.sample(annotations,
                                                  num_samples_per_label)
            sampled_frames = [
                self.random.randrange(x.start_frame, x.end_frame + 1)
                for x in sampled_segments
            ]
            for sampled_segment, sampled_frame in zip(sampled_segments,
                                                      sampled_frames):
                filename = sampled_segment.filename
                labels = sorted(list(self._frame_labels(filename,
                                                        sampled_frame)))
                pre_context_frames = [sampled_frame - pre_context + i
                                      for i in range(pre_context)]
                post_context_frames = [sampled_frame + i + 1
                                       for i in range(post_context)]
                frame_samples.append(
                    FrameSample(filename, sampled_frame, pre_context_frames,
                                post_context_frames, labels))
        # Sample background frames. Chop off the interval [0, pre_context), and
        # [num_frames - post_context, num_frames].
        background_intervals = []
        for filename, intervals in self.background_intervals.items():
            num_frames = self.video_frame_info[filename][1]
            tree = intervals.copy()
            tree.chop(0, pre_context)
            tree.chop(num_frames - post_context, num_frames)
            background_intervals.extend([(filename, interval)
                                         for interval in tree])
        sampled_backgrounds = self.random.sample(background_intervals,
                                                 num_background_samples)
        sampled_background_frames = [
            (filename, self.random.randrange(interval.begin, interval.end))
            for filename, interval in sampled_backgrounds
        ]
        for filename, frame in sampled_background_frames:
            pre_context_frames = [frame - pre_context + i
                                  for i in range(pre_context)]
            post_context_frames = [frame - post_context + i
                                   for i in range(post_context)]
            frame_samples.append(FrameSample(filename,
                                             frame,
                                             pre_context_frames,
                                             post_context_frames,
                                             labels=[]))
        self.random.shuffle(frame_samples)
        return frame_samples

    def sample_random(self,
                      num_samples,
                      min_samples_per_label=0,
                      seed=None,
                      pre_context=0,
                      post_context=0):
        if seed is not None:
            self.random.seed(seed)
        all_frames = []
        for filename, (_, num_frames) in self.video_frame_info.items():
            all_frames.extend([(filename, i)
                               for i in range(pre_context, num_frames -
                                              post_context)])
        samples_per_label = {label: 0 for _, label in self.label_map.items()}

        already_sampled = set()
        def sampled_enough():
            min_sampled = len(already_sampled) >= num_samples
            labels_sampled = all([x >= min_samples_per_label
                                  for x in samples_per_label.values()])
            print(min(samples_per_label.values()))
            return min_sampled and labels_sampled

        frame_samples = []
        while not sampled_enough():
            sample_index = self.random.randrange(len(all_frames))
            while sample_index in already_sampled:
                sample_index = self.random.randrange(len(all_frames))
            already_sampled.add(sample_index)

            video, frame = all_frames[sample_index]
            labels = self._frame_labels(video, frame)
            for label in labels:
                samples_per_label[label] += 1
            pre_context_frames = [frame - pre_context + i
                                    for i in range(pre_context)]
            post_context_frames = [frame + i + 1 for i in range(post_context)]
            frame_samples.append(
                FrameSample(video, frame, pre_context_frames,
                            post_context_frames, labels))
        print('Sampled', len(frame_samples))
        self.random.shuffle(frame_samples)
        return frame_samples

    def _frame_labels(self, filename, frame):
        return set(annotation.category
                   for annotation in self.annotations[filename]
                   if annotation.start_frame <= frame <= annotation.end_frame)
