#!/usr/bin/env python3
"""Create a free, offline daily YouTube explainer video starter.

This intentionally renders motion-card slides and offline speech, not AI-generated footage.
It requires ffmpeg, espeak-ng, and Pillow. The workflow publishes the output as an artifact
for review; it does not upload to YouTube automatically.
"""
from datetime import date
from pathlib import Path
import subprocess
import textwrap
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
OUT = Path("dist")
OUT.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()

TOPICS = [
    {
        "title": "YOUTUBE GROWTH",
        "subtitle": "7 practical tips for creators",
        "voice": "YouTube channel ko grow karne ke liye sirf roz video upload karna kaafi nahi hai. Sahi topic chuniye, title aur thumbnail ko clear rakhiye, aur video ke pehle tees second ko useful banaiye.",
        "points": ["Choose one clear audience", "Make title and thumbnail honest", "Hook viewers in the first 30 seconds", "Study audience retention", "Improve one thing every upload"],
    },
    {
        "title": "BETTER VIDEO IDEAS",
        "subtitle": "Plan content viewers need",
        "voice": "Achhe video ideas ke liye audience ke sawal padhiye, apne purane videos ka data dekhiye, aur ek specific problem solve karne wala topic chuniye. Har video mein ek clear promise rakhiye.",
        "points": ["Read audience questions", "Research one specific problem", "Make a clear promise", "Use examples and proof", "Review results after publishing"],
    },
    {
        "title": "THUMBNAIL BASICS",
        "subtitle": "Clear beats complicated",
        "voice": "Thumbnail chhote mobile screen par bhi samajh aana chahiye. Ek main subject, strong contrast aur bahut kam text rakhiye. Title aur thumbnail milkar video ka asli fayda batayein, galat wada na karein.",
        "points": ["One main subject", "Readable on a phone", "Use strong contrast", "Keep text short", "Avoid misleading promises"],
    },
    {
        "title": "AUDIENCE RETENTION",
        "subtitle": "Keep every minute useful",
        "voice": "Audience retention badhane ke liye lamba intro hataiye, pehle hi bataiye ki viewer kya seekhega, aur phir jaldi se value dijiye. Analytics mein dekhiye log kis point par video chhod rahe hain.",
        "points": ["Start with the viewer's problem", "Remove long introductions", "Use concrete examples", "Cut repeated points", "Learn from retention graphs"],
    },
    {
        "title": "CONSISTENT CREATION",
        "subtitle": "Build a schedule you can sustain",
        "voice": "Consistency ka matlab har din upload karna nahi hai. Aisa schedule chuniye jise aap quality ke saath nibha sakein. Related videos ki series banaiye aur har upload se ek lesson seekhiye.",
        "points": ["Choose a realistic schedule", "Batch similar tasks", "Create related video series", "Protect content quality", "Track progress weekly"],
    },
    {
        "title": "YOUTUBE ANALYTICS",
        "subtitle": "Use data, not guesses",
        "voice": "Sirf views dekhkar faisla mat kijiye. Impressions, click through rate, audience retention aur traffic sources ko saath mein samjhiye. Ek baar mein ek change kijiye aur similar videos se comparison kijiye.",
        "points": ["Check impressions", "Compare click-through rate", "Study audience retention", "Review traffic sources", "Change one variable at a time"],
    },
    {
        "title": "CREATOR WORKFLOW",
        "subtitle": "Research, record, improve",
        "voice": "Ek simple workflow banaiye: pehle research, phir outline, phir recording ya voiceover, editing, thumbnail aur final quality check. Har video ko publish karne se pehle audio, captions aur facts verify karein.",
        "points": ["Research before writing", "Outline the story", "Check audio levels", "Proofread captions", "Verify facts before upload"],
    },
]

topic = TOPICS[date.today().toordinal() % len(TOPICS)]
font_candidates = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
regular_candidates = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
def font(candidates, size):
    for item in candidates:
        if Path(item).exists():
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()

title_font = font(font_candidates, 64)
sub_font = font(34 if os.getenv("VIDEO_LANGUAGE", "hi") == "hi" else 30, 30)
body_font = font(regular_candidates, 34)
small_font = font(regular_candidates, 22)

slides = []
def draw_slide(index, heading, lines, footer):
    im = Image.new("RGB", (W, H), (12, 19, 38))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 48, W-48, H-48), radius=30, outline=(57, 85, 150), width=3)
    d.text((90, 80), "CREATOR LAB  •  DAILY EXPLAINER", font=small_font, fill=(117, 190, 255))
    d.text((90, 150), heading, font=title_font, fill=(255, 255, 255), stroke_width=1)
    y = 260
    for line in lines:
        wrapped = textwrap.wrap(line, width=46)
        for part in wrapped:
            d.rounded_rectangle((90, y+4, 104, y+42), radius=5, fill=(255, 190, 64))
            d.text((132, y), part, font=body_font, fill=(226, 234, 249))
            y += 55
        y += 14
    d.line((90, H-118, W-90, H-118), fill=(57, 85, 150), width=2)
    d.text((90, H-100), footer, font=small_font, fill=(163, 181, 213))
    d.text((W-210, H-100), f"{index:02d} / 07", font=small_font, fill=(117, 190, 255))
    path = OUT / f"slide-{index:02d}.png"
    im.save(path)
    slides.append(path)

draw_slide(1, topic["title"], [topic["subtitle"], "Practical tips for growing creators"], "Educational explainer • Verify details before publishing")
for i, point in enumerate(topic["points"], start=2):
    draw_slide(i, f"TIP {i-1}", [point, "Keep it clear • Make it useful • Improve each upload"], "YouTube growth is a process, not a guarantee")
draw_slide(7, "YOUR NEXT STEP", ["Choose one tip and apply it today", "Subscribe for more creator education"], "Comment with the next topic you want")

# Offline Hindi voice generation, one narration segment per scene.
audio_parts = []
for i, phrase in enumerate(voice_texts, start=1):
    wav = OUT / f"voice-{i:02d}.wav"
    subprocess.run(["espeak-ng", "-v", "hi", "-s", "145", "-w", str(wav), phrase], check=True)
    audio_parts.append(wav)

# Match each scene's display time to its narration duration.
segments = []
for i, (slide, audio) in enumerate(zip(slides, audio_parts), start=1):
    segment = OUT / f"segment-{i:02d}.mp4"
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        check=True, capture_output=True, text=True,
    )
    duration = max(3.0, float(probe.stdout.strip()) + 0.4)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", "25", "-i", str(slide), "-i", str(audio),
        "-t", f"{duration:.2f}", "-vf", "scale=1280:720,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(segment)
    ], check=True)
    segments.append(segment)

with (OUT / "segments.txt").open("w", encoding="utf-8") as f:
    for p in segments:
        f.write(f"file '{p.resolve()}\\n'\\n")
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-f", "concat", "-safe", "0", "-i", str(OUT / "segments.txt"),
    "-c", "copy", "-movflags", "+faststart", str(OUT / "daily-youtube-video.mp4")
], check=True)

(OUT / "script.txt").write_text("\\n\\n".join(voice_texts), encoding="utf-8")

# Reuse first slide as thumbnail; produce script and metadata.
(OUT / "thumbnail.png").write_bytes(slides[0].read_bytes())
(OUT / "script.txt").write_text(topic["voice"] + "\n\n" + "\n".join(topic["points"]), encoding="utf-8")
(OUT / "metadata.json").write_text(__import__("json").dumps({
    "date": TODAY,
    "title": topic["title"].title() + " | Practical YouTube Growth Tips",
    "description": topic["subtitle"] + "\n\nDaily creator education. Growth is not guaranteed; test strategies with your own analytics.",
    "tags": ["YouTubeGrowth", "CreatorTips", "YouTubeAnalytics"],
    "privacyStatus": "private",
    "note": "Offline-rendered motion-card starter; review audio, duration, and content before upload."
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Created daily video package for {TODAY}: {topic['title']}")
