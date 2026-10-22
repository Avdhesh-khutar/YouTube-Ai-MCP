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
topic_key = topic["title"]  # Keep the stable English key for matching thumbnail/metadata variants.
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
small_font = font(font_candidates, 22)

slides = []
def draw_slide(index, heading, lines, footer):
    # Layered editorial frame with scene-specific geometry and strong visual hierarchy.
    palette = [
        ((7, 12, 28), (20, 88, 150), (255, 185, 45)),
        ((10, 12, 32), (95, 32, 112), (255, 190, 70)),
        ((6, 20, 30), (20, 112, 116), (95, 205, 255)),
        ((18, 10, 28), (125, 45, 58), (255, 184, 80)),
    ]
    base, glow_color, accent = palette[(index - 1) % len(palette)]
    im = Image.new("RGB", (W, H), base)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W*0.45, -220 + (index % 3)*35, W*1.18, 490), fill=(*glow_color, 115))
    gd.ellipse((-310, H*0.48, W*0.50, H*1.28), fill=(accent[0], accent[1]//3, accent[2]//3, 50))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(im)
    # Oversized editorial shapes make each scene feel distinct instead of a plain text card.
    d.polygon([(850, 110), (1190, 110), (1190, 430), (1030, 520)], fill=(*glow_color, ))
    d.ellipse((875, 170, 1135, 430), outline=accent, width=8)
    d.arc((900, 195, 1110, 405), start=25*index, end=300+25*index, fill=(255,255,255), width=5)
    for bar_i, bar_h in enumerate([75, 125, 95, 170, 145]):
        x = 790 + bar_i*65
        d.rounded_rectangle((x, 540-bar_h, x+34, 540), radius=9, fill=accent)
    d.rounded_rectangle((48, 48, W-48, H-48), radius=30, outline=(*glow_color,), width=3)
    d.rounded_rectangle((82, 86, 370, 130), radius=14, fill=accent)
    d.text((102, 94), f"सीखें  •  भाग {index}", font=font(font_candidates, 22), fill=(8, 12, 28))
    d.text((90, 165), heading, font=title_font, fill=(255, 255, 255), stroke_width=1)
    y = 275
    for line in lines:
        wrapped = textwrap.wrap(line, width=34)
        for part in wrapped:
            d.rounded_rectangle((90, y+5, 106, y+43), radius=5, fill=accent)
            d.text((132, y), part, font=body_font, fill=(238, 242, 252))
            y += 55
        y += 12
    d.line((90, H-118, W-90, H-118), fill=(*glow_color,), width=2)
    d.text((90, H-100), footer, font=small_font, fill=(196, 210, 236))
    d.text((W-210, H-100), f"{index:02d} / 08", font=small_font, fill=(255, 210, 105))
    # Small progress rail
    d.rounded_rectangle((90, H-65, W-90, H-57), radius=4, fill=(35, 47, 70))
    d.rounded_rectangle((90, H-65, 90 + int((W-180)*index/8), H-57), radius=4, fill=accent)
    path = OUT / f"slide-{index:02d}.png"
    im.save(path)
    slides.append(path)

draw_slide(1, topic["title"], [topic["subtitle"], "हिंदी में पूरी जानकारी"], "हिंदी में सीखें और लागू करें")
for i, point in enumerate(topic["points"], start=2):
    draw_slide(i, f"चरण {i-1}", [point, "इसे स्पष्ट रखें और उपयोगी बनाएं"], "सही सीख और लगातार अभ्यास")
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

# Prefer a natural Hindi neural voice (Microsoft Edge TTS, no API key).
# If the runner cannot reach the service, fall back to offline speech.
audio_parts = []
narration_provider = "Microsoft Edge Hindi neural voice"
for i, phrase in enumerate(voice_texts, start=1):
    audio = OUT / f"voice-{i:02d}.mp3"
    edge_ok = False
    try:
        subprocess.run(
            ["edge-tts", "--voice", "hi-IN-MadhurNeural", "--rate=-8%",
             "--text", phrase, "--write-media", str(audio)],
            check=True, capture_output=True, text=True, timeout=90
        )
        if audio.exists() and audio.stat().st_size > 1000:
            edge_ok = True
            print(f"Generated natural Hindi narration segment {i}/{len(voice_texts)}")
    except Exception as error:
        print(f"Neural Hindi voice unavailable for segment {i}; using offline fallback ({type(error).__name__}).")
    if not edge_ok:
        narration_provider = "offline eSpeak fallback"
        audio = OUT / f"voice-{i:02d}.wav"
        subprocess.run(
            ["espeak-ng", "-v", "hi", "-s", "132", "-p", "42", "-w", str(audio), phrase],
            check=True
        )
    audio_parts.append(audio)

print("Narration provider: " + narration_provider)

# Create a simple SRT caption file aligned to each narration scene.
def srt_timestamp(seconds):
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

caption_blocks = []
cursor = 0.0
caption_index = 1

def caption_chunks(text, max_line_chars=32):
    """Wrap narration into two-line cues without discarding any words."""
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_line_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]

for index, audio in enumerate(audio_parts, start=1):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        check=True, capture_output=True, text=True
    )
    duration = max(3.0, float(probe.stdout.strip()) + 0.4)
    chunks = caption_chunks(voice_texts[index - 1])
    total_chars = max(1, sum(len(chunk.replace("\n", "")) for chunk in chunks))
    elapsed = 0.0
    for chunk in chunks:
        cue_weight = max(1, len(chunk.replace("\n", "")))
        cue_duration = duration * cue_weight / total_chars
        # Timing is estimated by text length, not speech recognition alignment.
        caption_blocks.append(
            f"{caption_index}\n{srt_timestamp(cursor + elapsed)} --> "
            f"{srt_timestamp(cursor + elapsed + cue_duration)}\n{chunk}\n"
        )
        caption_index += 1
        elapsed += cue_duration
    cursor += duration
(OUT / "captions.srt").write_text("\n".join(caption_blocks), encoding="utf-8")


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
        "-t", f"{duration:.2f}", "-vf", f"zoompan=z='min(zoom+0.0008,1.06)':d=1:s=1280x720:fps=25,fade=t=in:st=0:d=0.45,fade=t=out:st={max(0.1, duration-0.45):.2f}:d=0.45,format=yuv420p",
        "-filter_complex", f"[2:a]volume=0.07[bg];[1:a]volume=1.0[voice];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2,afade=t=in:st=0:d=0.25,afade=t=out:st={max(0.1, duration-0.35):.2f}:d=0.35,alimiter=limit=0.92[a]",
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

# Build a dedicated high-contrast thumbnail instead of reusing a mostly empty slide.
thumb = Image.new("RGB", (1280, 720), (5, 10, 25))
td = ImageDraw.Draw(thumb)
td.ellipse((700, -180, 1430, 600), fill=(20, 65, 125))
td.ellipse((-260, 420, 520, 1120), fill=(75, 20, 70))
td.rectangle((0, 0, 26, 720), fill=(255, 185, 45))
td.rounded_rectangle((64, 54, 520, 118), radius=18, fill=(255, 185, 45))
td.text((90, 67), "HINDI VIDEO GUIDE", font=font(["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"], 26), fill=(10, 17, 35))
headline_font = font(font_candidates, 76)
thumbnail_titles = {
    "AUDIENCE RETENTION": ("दर्शक वीडियो", "क्यों छोड़ते हैं?"),
    "BETTER VIDEO IDEAS": ("दमदार वीडियो", "आइडिया कैसे चुनें?"),
    "THUMBNAIL BASICS": ("प्रोफेशनल", "थंबनेल कैसे बनाएँ?"),
    "CONSISTENT CREATION": ("YouTube पर", "लगातार कैसे बढ़ें?"),
    "YOUTUBE ANALYTICS": ("YouTube Analytics", "आसान हिंदी में"),
    "CREATOR WORKFLOW": ("वीडियो बनाने का", "प्रोफेशनल तरीका"),
    "YOUTUBE GROWTH": ("YouTube चैनल", "कैसे बढ़ाएँ?"),
}
thumb_title = "\n".join(thumbnail_titles.get(topic_key, ("YouTube वीडियो", "बेहतर कैसे बनाएँ?")))
for line_no, line in enumerate(thumb_title.split("\n")):
    td.text((70, 190 + line_no*100), line, font=headline_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(5, 10, 25))
td.rounded_rectangle((72, 430, 635, 500), radius=18, fill=(224, 48, 55))
td.text((100, 445), {"AUDIENCE RETENTION": "दर्शक क्यों रुकें?", "BETTER VIDEO IDEAS": "सही विषय चुनें", "THUMBNAIL BASICS": "डिजाइन को बेहतर करें", "CONSISTENT CREATION": "टिकाऊ शेड्यूल रखें", "YOUTUBE ANALYTICS": "डेटा से सीखें", "CREATOR WORKFLOW": "हर चरण जांचें", "YOUTUBE GROWTH": "आज से सुधार करें"}.get(topic_key, "आज से सुधार करें"), font=font(font_candidates, 34), fill=(255, 255, 255))
td.text((74, 610), "हिंदी में आसान और उपयोगी गाइड", font=font(font_candidates, 28), fill=(215, 226, 245))
# Simple play symbol and retention bars add a visual focal point.
td.ellipse((890, 235, 1130, 475), fill=(255, 185, 45), outline=(255,255,255), width=6)
td.polygon([(978, 292), (978, 418), (1070, 355)], fill=(8, 18, 40))
for j, bar_h in enumerate([95, 150, 110, 205, 165]):
    x = 785 + j*76
    td.rounded_rectangle((x, 565-bar_h, x+42, 565), radius=9, fill=(95, 174, 255))
td.text((1000, 615), "WATCH TIME", font=font(["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"], 22), fill=(180, 205, 240))
# Export a contact sheet of all eight scenes so visual QA can catch repeated/empty cards.
thumb.save(OUT / "thumbnail.png")
thumb.save(OUT / "thumbnail.jpg", quality=94, optimize=True)
contact = Image.new("RGB", (1280, 900), (12, 17, 31))
cd = ImageDraw.Draw(contact)
for k, slide_path in enumerate(slides[:8]):
    shot = Image.open(slide_path).convert("RGB")
    shot.thumbnail((400, 225))
    x = 24 + (k % 3) * 418
    y = 24 + (k // 3) * 285
    contact.paste(shot, (x, y))
    cd.text((x, y + 230), f"दृश्य {k+1}", font=font(font_candidates, 22), fill=(245, 245, 250))
contact.save(OUT / "scene-contact-sheet.jpg", quality=92, optimize=True)
(OUT / "script.txt").write_text("\n\n".join(voice_texts), encoding="utf-8")
(OUT / "metadata.json").write_text(__import__("json").dumps({
    "date": TODAY,
    "title": {
        "AUDIENCE RETENTION": "दर्शक वीडियो क्यों छोड़ते हैं? | 5 YouTube Tips",
        "BETTER VIDEO IDEAS": "दमदार YouTube वीडियो आइडिया कैसे चुनें?",
        "THUMBNAIL BASICS": "प्रोफेशनल YouTube Thumbnail कैसे बनाएँ?",
        "CONSISTENT CREATION": "YouTube पर लगातार कैसे बढ़ें?",
        "YOUTUBE ANALYTICS": "YouTube Analytics आसान हिंदी में",
        "CREATOR WORKFLOW": "YouTube वीडियो बनाने का प्रोफेशनल तरीका",
        "YOUTUBE GROWTH": "YouTube चैनल कैसे बढ़ाएँ? | Hindi Guide",
    }.get(topic_key, topic["title"] + " | Hindi YouTube Guide"),
    "description": topic["subtitle"] + "\n\n" + topic["voice"] + "\n\nवीडियो को बेहतर बनाने के लिए एक-एक सुझाव अगली वीडियो में लागू करें.",
    "tags": ["YouTube Tips Hindi", "YouTube Growth", "Audience Retention", "Hindi Creator", "YouTube Tutorial"],
    "privacyStatus": "private",
    "note": "Offline-rendered motion-card explainer; captions.srt is included. Review pronunciation, visuals, duration, audio, and content before upload."
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Created daily video package for {TODAY}: {topic['title']}")
