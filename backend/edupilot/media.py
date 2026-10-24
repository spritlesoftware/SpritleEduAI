import os, re, subprocess, tempfile, time
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "videos")
FONTS = {"en": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "ta": "/usr/share/fonts/truetype/noto/NotoSansTamilUI-Regular.ttf"}
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
W, H = 1280, 720


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def render_slide(slide, path, lang="en", n=None, total=None):
    img = Image.new("RGB", (W, H), "#0f172a")
    d = ImageDraw.Draw(img)
    f = lambda size, p=None: ImageFont.truetype(p or FONTS.get(lang, FONTS["en"]), size)
    d.rectangle([0, 0, W, 8], fill="#6366f1")
    y = 50
    for line in _wrap(d, slide["title"], f(46), W - 120)[:2]:
        d.text((60, y), line, font=f(46), fill="#e0e7ff"); y += 60
    y += 15
    for b in slide.get("bullets", [])[:5]:
        lines = _wrap(d, b, f(30), W - 160)
        d.text((60, y), "•", font=f(30), fill="#818cf8")
        for line in lines[:2]:
            d.text((100, y), line, font=f(30), fill="#f1f5f9"); y += 40
        y += 12
    if slide.get("code"):
        code = slide["code"].splitlines()[:8]
        top = max(y + 10, H - 40 - 30 * len(code) - 30)
        d.rounded_rectangle([60, top, W - 60, H - 40], radius=12, fill="#020617")
        for i, line in enumerate(code):
            d.text((80, top + 15 + i * 30), line[:90], font=ImageFont.truetype(MONO, 22), fill="#86efac")
    if n:
        d.text((W - 140, H - 30), f"{n}/{total}", font=f(18), fill="#64748b")
    img.save(path)


def _dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))


def _ts(t):
    return f"{int(t//3600):02}:{int(t%3600//60):02}:{t%60:06.3f}"


def build_video(lesson, name, lang="en", clip=None):
    """Return (mp4_path, vtt_path). `clip` optionally an mp4 prepended as intro. Cached by name."""
    os.makedirs(OUT, exist_ok=True)
    mp4, vtt = (os.path.join(OUT, f"{name}.{e}") for e in ("mp4", "vtt"))
    if os.path.exists(mp4) and os.path.exists(vtt):
        return mp4, vtt
    slides = lesson["slides"]
    with tempfile.TemporaryDirectory() as tmp:
        segs, cues, t = [], ["WEBVTT\n"], 0.0
        if clip:
            norm = os.path.join(tmp, "clip.mp4")
            subprocess.run(["ffmpeg", "-y", "-i", clip, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
                            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-shortest", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "25", norm],
                           check=True, capture_output=True)
            segs.append(norm); t += _dur(norm)
        for i, s in enumerate(slides, 1):
            png, mp3, seg = (os.path.join(tmp, f"{i}.{e}") for e in ("png", "mp3", "mp4"))
            render_slide(s, png, lang, i, len(slides))
            gTTS(s["narration"], lang=lang).save(mp3)
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", png, "-i", mp3, "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
                            "-ar", "24000", "-ac", "1", "-pix_fmt", "yuv420p", "-r", "25", "-shortest", seg], check=True, capture_output=True)
            dur = _dur(seg)
            sents = [x for x in re.split(r"(?<=[.!?।])\s+", s["narration"]) if x] or [s["narration"]]
            total = sum(map(len, sents)); at = t
            for x in sents:  # captions timed proportionally to sentence length
                span = dur * len(x) / total
                cues.append(f"{_ts(at)} --> {_ts(at+span)}\n{x}\n"); at += span
            t += dur; segs.append(seg)
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in segs))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", mp4], check=True, capture_output=True)
        open(vtt, "w").write("\n".join(cues))
    return mp4, vtt


def speak(text, lang="en"):
    """Read-aloud / tutor reply audio (mp3 bytes)."""
    import io
    b = io.BytesIO(); gTTS(text[:4000], lang=lang).write_to_fp(b); return b.getvalue()


def generate_clip(prompt, dest):
    """Optional Gemini video clip. Needs GEMINI_VIDEO_MODEL set to a currently available model (check quotas)."""
    from .ai import client
    model = os.environ.get("GEMINI_VIDEO_MODEL")
    if not model:
        raise RuntimeError("Set GEMINI_VIDEO_MODEL in .env to a currently available Gemini video model.")
    c = client()
    op = c.models.generate_videos(model=model, prompt=prompt)
    while not op.done:
        time.sleep(10); op = c.operations.get(op)
    v = op.response.generated_videos[0]
    c.files.download(file=v.video); v.video.save(dest)
    return dest
