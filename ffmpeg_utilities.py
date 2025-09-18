import os
import subprocess
import tempfile

def get_video_info(filepath):
    # Get duration, title, and codec using ffprobe
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:format_tags=title",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        duration = float(lines[0]) if lines else 0
        title = os.path.basename(filepath)

        # Get codec name
        codec_result = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ], capture_output=True, text=True)
        codec = codec_result.stdout.strip().split('\n')[0] if codec_result.stdout else ""

        return title, duration, codec
    except Exception:
        return os.path.basename(filepath), 0, ""

def get_thumbnail(filepath):
    # Generate thumbnail from the 3rd I-frame using ffmpeg
    thumb_fd, thumb_path = tempfile.mkstemp(suffix=".jpg")
    os.close(thumb_fd)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", filepath,
            "-vf", "select='eq(pict_type\\,I)',select='eq(n\\,2)'",
            "-vsync", "vfr",
            "-frames:v", "1",
            thumb_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return thumb_path
    except Exception:
        return None

def seconds_to_hms(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"