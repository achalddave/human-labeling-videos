import subprocess


def num_frames(video_path):
    num_frames_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=nb_frames', '-of', 'default=nokey=1:noprint_wrappers=1',
        video_path
    ]
    frames = subprocess.check_output(num_frames_cmd, stderr=subprocess.STDOUT)
    return int(frames.decode().strip())
