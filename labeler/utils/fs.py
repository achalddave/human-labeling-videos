from pathlib import Path


def get_files(root, extensions, recursive=True):
    root = Path(root)
    all_files = root.rglob('*') if recursive else root.glob('*')
    return [
        x for x in all_files if any(x.name.endswith(y) for y in extensions)
    ]


IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif',
                    '.tiff', '.webp')
VIDEO_EXTENSIONS = ('.mp4')
