# Free YouTube Long-to-Short Maker

A local, free starter app for creating vertical Shorts/Reels from long videos.

## Features
- Upload MP4, MOV, MKV, WEBM or AVI
- Local speech transcription with open-source Faster-Whisper
- Automatic highlight-window scoring (speech density + engaging phrase cues)
- 9:16 vertical crop at 1080x1920
- Optional burned-in subtitles
- Download clips individually or as one ZIP
- Runs locally; your video is not uploaded to a third-party processing server

## Requirements
- Python 3.10+
- FFmpeg + FFprobe installed and available on PATH
- Recommended: 8 GB RAM or more. CPU works; first run downloads a Whisper model.

### Install FFmpeg
- Windows: install FFmpeg from https://ffmpeg.org/download.html and add its `bin` folder to PATH.
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`

## Run
1. Extract this ZIP.
2. Open a terminal in this folder.
3. Windows: double-click `run_windows.bat`.
4. macOS/Linux: run `chmod +x run_mac_linux.sh && ./run_mac_linux.sh`.
5. Open the local Streamlit address shown in the terminal (usually http://localhost:8501).

## Notes
- The first run downloads the selected Whisper model; this is free but requires internet once.
- `tiny` is fastest, `base` is a good starting point, `small` is generally more accurate and slower.
- Automatic selection is a heuristic, not a guarantee of virality. Review clips before publishing.
- The vertical crop is center-cropped. If the speaker is off-center, use a reframing editor afterward.
- YouTube and Instagram upload/publishing is not automated; this tool creates downloadable MP4s.


## Deploy as a public web app (Streamlit Community Cloud)
1. Create a **new public GitHub repository** and upload `app.py`, `requirements.txt`, and `packages.txt` to its root.
2. Visit https://share.streamlit.io/ and sign in with GitHub.
3. Select **Create app**, choose your repository, branch (`main`), and main file path (`app.py`).
4. Select **Deploy**. Streamlit will install the Python packages and the FFmpeg system package from `packages.txt`.
5. When deployment finishes, Streamlit gives you a public `*.streamlit.app` URL.

Note: Streamlit's free hosting has resource and execution limits. Long videos may exceed those limits; for larger files, run the app locally or use a server with more memory/CPU.
