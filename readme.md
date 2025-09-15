# No-Encode Video Joiner

![Logo](app-logo.png)

A simple PyQt6 desktop application to join/concatenate video files **without re-encoding** using FFmpeg.

## Features

- **Drag and drop** video files to add them to the list.
- **Reorder** videos before joining.
- **Preview** the FFmpeg command before running.
- **Settings** dialog to manually specify `ffmpeg.exe` and `ffprobe.exe` paths.
- **Delete old files** after successful join (optional).
- **No re-encoding**: Fast joining, no quality loss

## Requirements

- Python 3.8+
- [PyQt6](https://pypi.org/project/PyQt6/)
- [FFmpeg](https://ffmpeg.org/) and [ffprobe](https://ffmpeg.org/ffprobe.html) installed and accessible in your system PATH, or specify their paths in the settings.

## Installation

1. **Install dependencies:**
   ```
   pip install PyQt6
   ```

2. **Download FFmpeg:**
   - [Windows builds](https://www.gyan.dev/ffmpeg/builds/)
   - [Linux/Mac](https://ffmpeg.org/download.html)

3. **Clone this repository:**
   ```
   git clone https://github.com/Jason-nzd/no-encode-video-joiner.git
   cd no-encode-video-joiner
   ```

## Usage

1. **Run the app:**
   ```
   python app.py
   ```

2. **Drag and drop** your video files into the window.

3. **Reorder** them as needed.

4. Click **Join Videos**.

5. Optionally, click the **gear icon** to open settings and manually set FFmpeg paths.

## Notes

- Videos **must** have the same codec, dimensions, fps, etc. for joining without re-encoding.
- Output file will be saved in the same folder as the first video, with `-combined` appended to the filename.
