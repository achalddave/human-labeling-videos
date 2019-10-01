from pathlib import Path

from labeler.labelers.single_file import SingleFileLabeler
from labeler.utils import fs


class GridLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 show_notes=True,
                 num_items=10,
                 cell_width=200,
                 cell_height='auto'):
        template_args = {
            'show_notes': show_notes,
            'ui': {
                'cell_width': cell_width,
                'cell_height': cell_height
            }
        }
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=fs.IMAGE_EXTENSIONS,
                         output_dir=output_dir,
                         template='label_grid_images.html',
                         template_extra_args=template_args,
                         num_items=num_items)


class GridGifLabeler(SingleFileLabeler):
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 video_root=None,
                 show_notes=True,
                 num_items=10,
                 cell_width=200,
                 cell_height='auto'):
        template_args = {
            'show_notes': show_notes,
            'ui': {
                'cell_width': cell_width,
                'cell_height': cell_height
            }
        }
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=('.gif'),
                         output_dir=output_dir,
                         template='label_grid_gifs.html',
                         template_extra_args=template_args,
                         num_items=num_items)
        if video_root is not None:
            video_root = Path(video_root)
            video_paths = {}
            for key in self.label_store.keys:
                video_path = (video_root / key).with_suffix('.mp4')
                assert video_path.exists(), (
                    f'Could not find video for gif {key} at {video_path}')
                video_paths[key] = video_path
            self.video_paths = video_paths
        else:
            self.video_paths = {}
        self.video_root = video_root

    def public_directories(self):
        return {
            'gif': self.root,
            'video': self.video_root
        }

    def key_to_url(self, key):
        key_path = Path(key)
        is_gif = key_path.suffix == '.gif'
        root = self.root if is_gif else self.video_root
        if key_path.is_absolute():
            relative = str(key_path.relative_to(root))
        else:
            relative = str(key_path)
        return f'/file/{"gif" if is_gif else "video"}/{relative}'

    def url_to_key(self, url):
        if url.startswith('/file/gif'):
            relative = url.split('/file/gif/')[1]
            return self.root / relative
        elif url.startswith('/file/video'):
            relative = url.split('/file/video/')[1]
            return self.video_root / relative

    def update_template_args(self, kwargs):
        to_label = kwargs['to_label']
        new_to_label = []
        for data in to_label:
            key, gif_path, labels = data
            video_path = self.video_paths.get(key, None)
            new_to_label.append(
                (key, gif_path, labels, self.key_to_url(video_path)))
        kwargs['to_label'] = new_to_label
        return kwargs


class GridSummaryVideoLabeler(SingleFileLabeler):
    """Labeler showing video summary in grid with full video when clicked."""
    def __init__(self,
                 root,
                 labels_csv,
                 output_dir,
                 full_video_root=None,
                 show_notes=True,
                 num_items=10,
                 cell_width=200,
                 cell_height='auto'):
        template_args = {
            'show_notes': show_notes,
            'ui': {
                'cell_width': cell_width,
                'cell_height': cell_height
            }
        }
        super().__init__(root=root,
                         labels_csv=labels_csv,
                         extensions=('.mp4'),
                         output_dir=output_dir,
                         template='label_grid_summary_video.html',
                         template_extra_args=template_args,
                         num_items=num_items)
        if full_video_root is not None:
            full_video_root = Path(full_video_root)
            video_paths = {}
            for key in self.label_store.keys:
                video_path = (full_video_root / key).with_suffix('.mp4')
                assert video_path.exists(), (
                    f'Could not find video for gif {key} at {video_path}')
                video_paths[key] = video_path
            self.video_paths = video_paths
        else:
            self.video_paths = {}
        self.full_video_root = full_video_root

    def public_directories(self):
        return {
            'short': self.root,
            'full': self.full_video_root
        }

    def key_to_url(self, key, full_video=False):
        key_path = Path(key)
        root = self.full_video_root if full_video else self.root
        if key_path.is_absolute():
            relative = str(key_path.relative_to(root))
        else:
            relative = str(key_path)
        return f'/file/{"full" if full_video else "short"}/{relative}'

    def url_to_key(self, url):
        if url.startswith('/file/short'):
            relative = url.split('/file/short/')[1]
            return self.root / relative
        elif url.startswith('/file/full'):
            relative = url.split('/file/full/')[1]
            return self.full_video_root / relative

    def update_template_args(self, kwargs):
        to_label = kwargs['to_label']
        new_to_label = []
        for data in to_label:
            key, path, labels = data
            video_path = self.video_paths.get(key, None)
            new_to_label.append(
                (key, path, labels, self.key_to_url(video_path,
                                                    full_video=True)))
        kwargs['to_label'] = new_to_label
        return kwargs
