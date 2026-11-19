import os, re, json, math, subprocess, tempfile
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Free Shorts Maker", page_icon="🎬", layout="wide")
st.title("🎬 Free YouTube Long-to-Short Maker")
st.caption("Turn one long video into vertical Shorts and Reels — processed locally on your computer.")

def have_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2500:])
    return p

def transcribe(path, model_name):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(path, vad_filter=True, word_timestamps=False)
    return [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()} for s in segments]

def choose_segments(segments, duration, clip_len, count):
    # Rank transcript windows using speech density, engaging language and sentence changes.
    if not segments:
        return []
    words = ["why", "secret", "never", "truth", "shocking", "mistake", "best", "worst",
             "imagine", "because", "actually", "finally", "danger", "amazing", "how"]
    candidates = []
    step = max(5, clip_len // 3)
    for start in range(0, max(1, int(duration-clip_len)+1), step):
        end = min(duration, start + clip_len)
        inside = [s for s in segments if s["end"] > start and s["start"] < end]
        text = " ".join(s["text"] for s in inside)
        wc = len(re.findall(r"\b\w+\b", text))
        density = wc / max(1, end-start)
        hits = sum(len(re.findall(r"\b"+w+r"\b", text.lower())) for w in words)
        complete = sum(1 for s in inside if s["text"].rstrip().endswith((".", "?", "!")))
        score = density * 2 + hits * 0.9 + complete * 0.25
        # Prefer clips with enough spoken content; penalize near-silent windows.
        if wc >= 8:
            candidates.append((score, start, end, text))
    candidates.sort(reverse=True)
    selected = []
    for item in candidates:
        _, a, b, _ = item
        if all(abs(a-x[1]) > clip_len*0.65 for x in selected):
            selected.append(item)
        if len(selected) >= count:
            break
    return sorted(selected, key=lambda x: x[1])

def make_clip(src, dst, start, end, subtitle_path=None):
    duration = end-start
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if subtitle_path:
        escaped = subtitle_path.replace("\\", "/").replace(":", r"\:")
        vf += f",subtitles='{escaped}':force_style='FontName=Arial,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=120'"
    cmd = ["ffmpeg","-y","-ss",str(start),"-i",src,"-t",str(duration),"-vf",vf,
           "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k",
           "-movflags","+faststart",dst]
    run(cmd)

def srt_time(t):
    ms = int(round(t*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(segments, start, end, path):
    lines=[]; n=1
    for seg in segments:
        a=max(0,seg["start"]-start); b=min(end-start,seg["end"]-start)
        if b>a and seg["text"]:
            lines += [str(n), f"{srt_time(a)} --> {srt_time(b)}", seg["text"], ""]
            n+=1
    Path(path).write_text("\n".join(lines), encoding="utf-8")

st.markdown("""
**What it does:** transcribes your video with a free local Whisper model, scores speech-rich moments and engaging phrases, then exports vertical 9:16 MP4 clips with optional burned-in captions. It does not upload your video to a cloud service.
""")
if not have_ffmpeg():
    st.error("FFmpeg was not found. Install FFmpeg, restart this app, and try again. See README for instructions.")
    st.stop()

uploaded = st.file_uploader("Upload a long video", type=["mp4","mov","mkv","webm","avi"])
c1,c2,c3 = st.columns(3)
with c1: clip_len = st.slider("Clip length (seconds)", 15, 90, 45, 5)
with c2: clip_count = st.slider("Number of Shorts", 1, 10, 5)
with c3: model_name = st.selectbox("Whisper model", ["tiny","base","small"], index=1,
                                  help="tiny is fastest; small is more accurate but slower.")
captions = st.toggle("Burn subtitles into each Short", value=True)
st.caption("First run downloads the selected Whisper model (free, open-source). Processing speed depends on your computer.")
if uploaded and st.button("✨ Find moments and create Shorts", type="primary", use_container_width=True):
    work = tempfile.mkdtemp(prefix="shorts_")
    src = os.path.join(work, uploaded.name)
    with open(src, "wb") as f: f.write(uploaded.getbuffer())
    try:
        info = json.loads(run(["ffprobe","-v","quiet","-print_format","json","-show_format",src]).stdout)
        duration = float(info["format"]["duration"])
        if duration < 15: st.error("Please upload a video at least 15 seconds long."); st.stop()
        st.info(f"Video duration: {duration/60:.1f} minutes. Transcribing audio…")
        audio = os.path.join(work,"audio.wav")
        run(["ffmpeg","-y","-i",src,"-vn","-ac","1","-ar","16000",audio])
        segments = transcribe(audio, model_name)
        picks = choose_segments(segments, duration, min(clip_len, int(duration)), clip_count)
        if not picks:
            st.warning("No clear speech windows were found. Try another video or a longer clip duration.")
            st.stop()
        outdir = os.path.join(work,"shorts"); os.makedirs(outdir)
        progress = st.progress(0)
        for i, (_, start, end, transcript) in enumerate(picks, 1):
            srt = os.path.join(work, f"clip{i}.srt")
            if captions: write_srt(segments, start, end, srt)
            dest = os.path.join(outdir, f"short_{i:02}.mp4")
            make_clip(src, dest, start, end, srt if captions else None)
            progress.progress(i/len(picks))
        zip_path = os.path.join(work,"youtube_shorts_reels.zip")
        import zipfile
        with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
            for name in os.listdir(outdir): z.write(os.path.join(outdir,name),name)
        st.success(f"Created {len(picks)} vertical clips.")
        for i, (_, start, end, transcript) in enumerate(picks, 1):
            st.write(f"**Short {i}** · {int(start//60):02}:{int(start%60):02} – {int(end//60):02}:{int(end%60):02}")
            st.caption(transcript[:450] + ("…" if len(transcript)>450 else ""))
            with open(os.path.join(outdir,f"short_{i:02}.mp4"),"rb") as f:
                st.download_button(f"Download Short {i}", f, file_name=f"short_{i:02}.mp4", mime="video/mp4", key=f"dl{i}")
        with open(zip_path,"rb") as f:
            st.download_button("⬇️ Download all Shorts (ZIP)", f, file_name="youtube_shorts_reels.zip",
                               mime="application/zip", type="primary", use_container_width=True)
        st.caption("Tip: Review each clip before publishing. Automatic scoring finds speech-rich, keyword-heavy moments; it cannot guarantee virality.")
    except Exception as e:
        st.error("Could not process this video.")
        st.code(str(e))
