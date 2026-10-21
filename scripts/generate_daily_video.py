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

from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
# Replace the initial English/romanized drafts with proper Devanagari Hindi before rendering.
HINDI_TOPICS = {
    "YOUTUBE GROWTH": ("यूट्यूब चैनल कैसे बढ़ाएँ", "चैनल ग्रोथ की पूरी हिंदी गाइड", "नमस्कार दोस्तों। आज हम समझेंगे कि YouTube चैनल को बेहतर बनाने के लिए क्या करना चाहिए। केवल रोज वीडियो डालना सफलता की गारंटी नहीं है। सबसे पहले अपने दर्शकों की जरूरत समझिए। हर वीडियो में एक स्पष्ट समस्या का समाधान दीजिए। शुरुआत में बताइए कि दर्शक क्या सीखेंगे, फिर उदाहरणों के साथ सीधे उपयोगी जानकारी पर आइए। शीर्षक और थंबनेल आकर्षक हों, लेकिन वीडियो की वास्तविक सामग्री से मेल खाने चाहिए। वीडियो प्रकाशित होने के बाद क्लिक थ्रू रेट, देखने का औसत समय और दर्शक किस जगह वीडियो छोड़ते हैं, इन संकेतों को समझिए। हर अगले वीडियो में एक सुधार लागू कीजिए। चैनल बढ़ाना लगातार सीखने की प्रक्रिया है; कोई भी तरीका निश्चित सफलता की गारंटी नहीं देता।", ["दर्शकों की जरूरत पहचानें", "शुरुआत में फायदा बताएं", "शीर्षक और थंबनेल स्पष्ट रखें", "दर्शकों का रिटेंशन समझें", "हर वीडियो में सुधार करें"]),
    "BETTER VIDEO IDEAS": ("बेहतर वीडियो आइडिया", "दर्शकों के लिए सही विषय चुनें", "नमस्कार दोस्तों। अच्छे वीडियो आइडिया खोजने के लिए दर्शकों के सवाल पढ़िए, कमेंट में बार बार आने वाली समस्याएँ नोट कीजिए और YouTube सर्च के सुझाव देखिए। बहुत बड़ा सामान्य विषय चुनने के बजाय एक खास समस्या पर वीडियो बनाइए। स्क्रिप्ट से पहले रूपरेखा तैयार करें, जिसमें समस्या, समाधान, उदाहरण और निष्कर्ष हो। दूसरे क्रिएटर से प्रेरणा लें, लेकिन उनकी स्क्रिप्ट की नकल न करें। अपनी भाषा और अनुभव जोड़ें। प्रकाशित होने के बाद देखें कि दर्शकों को कौन सा हिस्सा उपयोगी लगा और अगली वीडियो में क्या बेहतर हो सकता है।", ["दर्शकों के सवाल पढ़ें", "एक खास समस्या चुनें", "रूपरेखा पहले बनाएं", "अपने उदाहरण जोड़ें", "नतीजों से अगला विषय चुनें"]),
    "THUMBNAIL BASICS": ("प्रोफेशनल थंबनेल कैसे बनाएँ", "मोबाइल पर भी साफ दिखने वाला डिजाइन", "नमस्कार दोस्तों। थंबनेल दर्शक को वीडियो का पहला संकेत देता है। एक मुख्य विषय चुनिए, साफ बैकग्राउंड और स्पष्ट कंट्रास्ट रखिए। मोबाइल स्क्रीन पर छोटे अक्षर पढ़ना कठिन होता है, इसलिए कम और बड़े शब्द इस्तेमाल करें। शीर्षक और थंबनेल एक दूसरे की मदद करें और वीडियो का असली विषय बताएं। भ्रामक तस्वीरें या झूठे दावे दर्शकों का भरोसा घटाते हैं। थंबनेल को छोटा करके जांचें कि विषय तुरंत समझ आता है या नहीं। फिर उपलब्ध एनालिटिक्स से सीखें और अगले डिजाइन में सुधार करें।", ["एक मुख्य विषय रखें", "कम और बड़ा टेक्स्ट लिखें", "कंट्रास्ट बढ़ाएं", "शीर्षक से मेल रखें", "भ्रामक दावे न करें"]),
    "AUDIENCE RETENTION": ("दर्शक वीडियो क्यों छोड़ते हैं", "हर मिनट उपयोगी बनाएँ", "नमस्कार दोस्तों। वीडियो की लंबाई से ज्यादा जरूरी है कि हर हिस्सा दर्शक के लिए उपयोगी हो। शुरुआत में लंबा परिचय न रखें। पहले कुछ सेकंड में समस्या बताएं और समझाएं कि आगे क्या सीखने मिलेगा। विषय को छोटे हिस्सों में बांटें, उदाहरण दें और साफ आवाज रखें। एक ही बात बार बार न दोहराएं। एनालिटिक्स में देखें कि दर्शक किस जगह वीडियो छोड़ते हैं। वहां गति धीमी हो सकती है या उदाहरण अस्पष्ट हो सकता है। बदलाव एक समय में एक करें और पर्याप्त डेटा आने दें।", ["लंबा परिचय हटाएं", "शुरू में फायदा बताएं", "उदाहरण और अध्याय जोड़ें", "दोहराव कम करें", "रिटेंशन ग्राफ से सीखें"]),
    "YOUTUBE ANALYTICS": ("YouTube Analytics समझें", "अनुमान नहीं, डेटा से सीखें", "नमस्कार दोस्तों। YouTube Analytics बताता है कि दर्शक आपके वीडियो तक कैसे पहुंचते हैं और उसे किस तरह देखते हैं। केवल व्यूज देखकर पूरी तस्वीर नहीं मिलती। इम्प्रेशन, क्लिक थ्रू रेट, देखने का औसत समय और ट्रैफिक स्रोत साथ में समझें। हर वीडियो की तुलना हर दूसरे वीडियो से न करें, क्योंकि विषय और दर्शक अलग हो सकते हैं। एक बार में एक बदलाव आजमाएं, फिर पर्याप्त डेटा आने दें। थोड़े समय के उतार चढ़ाव पर घबराकर पूरी रणनीति न बदलें। डेटा संकेत देता है, लेकिन दर्शकों की जरूरत और संदर्भ भी महत्वपूर्ण हैं।", ["इम्प्रेशन देखें", "क्लिक थ्रू रेट समझें", "रिटेंशन ग्राफ जांचें", "ट्रैफिक स्रोत पहचानें", "एक समय में एक बदलाव करें"]),
    "CREATOR WORKFLOW": ("वीडियो बनाने का सही तरीका", "रिसर्च से फाइनल वीडियो तक", "नमस्कार दोस्तों। बेहतर वीडियो बनाने के लिए ऐसा वर्कफ़्लो बनाइए जिसे आप लंबे समय तक निभा सकें। पहले विषय तय करें, फिर भरोसेमंद स्रोतों से रिसर्च करें। स्क्रिप्ट लिखें और रिकॉर्डिंग से पहले उसे पढ़कर देखें। आवाज साफ रखें और बैकग्राउंड म्यूजिक इतना धीमा रखें कि बोल स्पष्ट सुनाई दें। एडिटिंग में दोहराव हटाएं, जरूरी जानकारी स्क्रीन पर दिखाएं और हिंदी कैप्शन की वर्तनी जांचें। थंबनेल और शीर्षक वास्तविक विषय से मेल खाने चाहिए। अपलोड से पहले पूरी वीडियो देखें और आवाज, दृश्य तथा तथ्यों की पुष्टि करें।", ["रिसर्च और स्क्रिप्ट", "आवाज साफ रिकॉर्ड करें", "दोहराव हटाएं", "कैप्शन जांचें", "अपलोड से पहले पूरा देखें"]),
    "CONSISTENT CREATION": ("लगातार बेहतर वीडियो बनाएँ", "टिकाऊ कंटेंट रणनीति", "नमस्कार दोस्तों। हर दिन वीडियो डालना जरूरी नहीं है। अपने समय और संसाधनों के अनुसार ऐसा शेड्यूल चुनें जिसे आप गुणवत्ता के साथ निभा सकें। एक मुख्य विषय और उससे जुड़े उप विषय चुनें ताकि दर्शकों को चैनल की पहचान समझ आए। संबंधित वीडियो की श्रृंखला बनाएं और हर सप्ताह देखें कि क्या अच्छा रहा और क्या सुधारना है। व्यूज की तुरंत बढ़ोतरी की उम्मीद न रखें। उपयोगी सामग्री, दर्शकों का भरोसा और लगातार सीखना लंबे समय में मदद कर सकते हैं, लेकिन निश्चित परिणाम की गारंटी नहीं है।", ["टिकाऊ शेड्यूल चुनें", "एक स्पष्ट विषय रखें", "वीडियो श्रृंखला बनाएं", "हर सप्ताह समीक्षा करें", "छोटे सुधार जारी रखें"])
}
if topic["title"] in HINDI_TOPICS:
    topic["title"], topic["subtitle"], topic["voice"], topic["points"] = HINDI_TOPICS[topic["title"]]
font_candidates = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
regular_candidates = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
def font(candidates, size):
    for item in candidates:
        if Path(item).exists():
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()

title_font = font(font_candidates, 64)
body_font = font(regular_candidates, 34)
small_font = font(regular_candidates, 22)

slides = []
def draw_slide(index, heading, lines, footer):
    # Cinematic layered background with subtle glows, vignette, and framing.
    im = Image.new("RGB", (W, H), (7, 12, 28))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W*0.42, -220, W*1.15, 480), fill=(18, 78, 150, 90))
    gd.ellipse((-280, H*0.45, W*0.52, H*1.3), fill=(130, 48, 120, 45))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 48, W-48, H-48), radius=30, outline=(57, 85, 150), width=3)
    d.text((90, 80), "CREATOR LAB  •  HINDI MASTERCLASS", font=small_font, fill=(117, 190, 255))
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
    d.text((W-210, H-100), f"{index:02d} / 08", font=small_font, fill=(117, 190, 255))
    path = OUT / f"slide-{index:02d}.png"
    im.save(path)
    slides.append(path)

draw_slide(1, topic["title"], [topic["subtitle"], "हिंदी में पूरी जानकारी"], "हिंदी क्रिएटर मास्टरक्लास • सीखें और लागू करें")
for i, point in enumerate(topic["points"], start=2):
    draw_slide(i, f"चरण {i-1}", [point, "Keep it clear • Make it useful • Improve each upload"], "सही सीख • लगातार अभ्यास • बेहतर वीडियो")
draw_slide(8, "अब आपकी बारी", ["आज एक बदलाव लागू करें", "ऐसी और हिंदी गाइड के लिए जुड़े रहें"], "लगातार सीखें और सुधार करें")

voice_texts = [
    topic["voice"] + " अब इस विषय को चरण दर चरण समझते हैं। सबसे पहले अपने लक्ष्य को स्पष्ट कीजिए। उसके बाद एक छोटा व्यावहारिक उदाहरण चुनिए और दर्शक को बताइए कि वह इसे कैसे लागू कर सकता है।",
    "पहला चरण। " + topic["points"][0] + "। अपने दर्शकों की जरूरत को समझने के लिए उनके सवाल पढ़िए। सामान्य सलाह देने के बजाय किसी खास स्थिति का उदाहरण दीजिए। इससे दर्शक को विषय समझने और अगला कदम चुनने में मदद मिलेगी।",
    "दूसरा चरण। " + topic["points"][1] + "। वीडियो की शुरुआत में दर्शक को बताइए कि उसे क्या सीखने को मिलेगा। लंबी भूमिका से बचें। जानकारी को छोटे हिस्सों में बांटें और हर हिस्से के बीच स्वाभाविक बदलाव रखें।",
    "तीसरा चरण। " + topic["points"][2] + "। अपनी बात को केवल शब्दों में न छोड़ें। स्क्रीन पर मुख्य बिंदु, सरल उदाहरण और स्पष्ट ग्राफिक्स दिखाएं। दृश्य वही समझाएं जो आवाज में बताया जा रहा है।",
    "चौथा चरण। " + topic["points"][3] + "। परिणाम देखने के लिए समय दें और आंकड़ों को संदर्भ के साथ समझें। एक वीडियो के आधार पर जल्दबाजी में बड़ा फैसला न करें। समान विषय वाले वीडियो से तुलना करना ज्यादा उपयोगी हो सकता है।",
    "पांचवां चरण। " + topic["points"][4] + "। आज की सीख में से एक बदलाव चुनिए और उसे अगली वीडियो में आजमाइए। फिर नोट करें कि क्या बेहतर हुआ और किस हिस्से पर अभी काम करना बाकी है।",
    "अब एक व्यावहारिक चेकलिस्ट देखते हैं। क्या विषय दर्शकों के लिए स्पष्ट है? क्या शुरुआत में वादा समझ आता है? क्या आवाज साफ है? क्या टेक्स्ट मोबाइल पर पढ़ा जा सकता है? क्या थंबनेल वीडियो की वास्तविक सामग्री से मेल खाता है? क्या पूरी वीडियो को शुरू से अंत तक देखा गया है? अपलोड से पहले इन सभी सवालों का जवाब जरूर जांचें।",
    "अंत में याद रखें कि बेहतर YouTube वीडियो बनाने का कोई जादुई शॉर्टकट नहीं है। रिसर्च, स्पष्ट हिंदी narration, उपयोगी उदाहरण, अच्छे दृश्य और नियमित समीक्षा मिलकर गुणवत्ता बेहतर कर सकते हैं। अपनी अगली वीडियो में एक सुधार लागू कीजिए। वीडियो देखने के लिए धन्यवाद। सीखते रहिए और दर्शकों के भरोसे को प्राथमिकता दीजिए।"
]

# Offline Hindi voice generation, one narration segment per scene.
audio_parts = []
for i, phrase in enumerate(voice_texts, start=1):
    wav = OUT / f"voice-{i:02d}.wav"
    subprocess.run(["espeak-ng", "-v", "hi", "-s", "145", "-w", str(wav), phrase], check=True)
    audio_parts.append(wav)

# Create a gentle synthesized ambient bed locally; no external music asset or paid API required.
music = OUT / "background-music.wav"
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-f", "lavfi", "-i", "sine=frequency=110:duration=600",
    "-f", "lavfi", "-i", "sine=frequency=164.81:duration=600",
    "-f", "lavfi", "-i", "sine=frequency=220:duration=600",
    "-filter_complex", "[0:a]volume=0.10[a0];[1:a]volume=0.055[a1];[2:a]volume=0.025[a2];[a0][a1][a2]amix=inputs=3:normalize=0,lowpass=f=700,afade=t=in:d=2,afade=t=out:st=590:d=10",
    "-t", "600", str(music)
], check=True)

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
        "-loop", "1", "-framerate", "25", "-i", str(slide), "-i", str(audio), "-i", str(music),
        "-t", f"{duration:.2f}", "-vf", f"zoompan=z='min(zoom+0.0008,1.06)':d=1:s=1280x720:fps=25,format=yuv420p",
        "-filter_complex", "[2:a]volume=0.12[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.92[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(segment)
    ], check=True)
    segments.append(segment)

with (OUT / "segments.txt").open("w", encoding="utf-8") as f:
    for p in segments:
        f.write(f"file '{p.resolve()}'\n")
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-f", "concat", "-safe", "0", "-i", str(OUT / "segments.txt"),
    "-c", "copy", "-movflags", "+faststart", str(OUT / "daily-youtube-video.mp4")
], check=True)

(OUT / "script.txt").write_text("\n\n".join(voice_texts), encoding="utf-8")

# Reuse first slide as thumbnail; produce script and metadata.
(OUT / "thumbnail.png").write_bytes(slides[0].read_bytes())
Image.open(OUT / "thumbnail.png").convert("RGB").save(OUT / "thumbnail.jpg", quality=92, optimize=True)
(OUT / "script.txt").write_text(topic["voice"] + "\n\n" + "\n".join(topic["points"]), encoding="utf-8")
(OUT / "metadata.json").write_text(__import__("json").dumps({
    "date": TODAY,
    "title": topic["title"].title() + " | Hindi Creator Masterclass",
    "description": topic["subtitle"] + "\n\nहिंदी में क्रिएटर एजुकेशन। अपनी analytics से सीखें। सफलता की गारंटी नहीं है।",
    "tags": ["YouTubeGrowth", "HindiCreator", "YouTubeAnalytics", "HindiTutorial"],
    "privacyStatus": "private",
    "note": "Offline-rendered animated motion-card explainer with generated narration; review language, duration, audio, and content before upload."
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Created daily video package for {TODAY}: {topic['title']}")
