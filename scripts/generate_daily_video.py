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
def draw_topic_visual(draw, heading, accent, glow_color, topic_key):
    """Draw a topic-matched editorial illustration in the right-side image panel."""
    label = (str(heading) + " " + str(topic_key)).lower()
    if "thumbnail" in label or "थंबनेल" in label:
        kind = "thumbnail"
    elif any(word in label for word in ("analytics", "retention", "रिटेंशन", "एनालिटिक्स", "दर्शक वीडियो क्यों")):
        kind = "chart"
    elif any(word in label for word in ("workflow", "creator", "editing", "वीडियो बनाने", "रिकॉर्ड", "कैप्शन")):
        kind = "workflow"
    elif any(word in label for word in ("idea", "आइडिया", "विषय", "सवाल")):
        kind = "idea"
    elif any(word in label for word in ("consistent", "schedule", "शेड्यूल", "लगातार", "साप्ताहिक")):
        kind = "calendar"
    else:
        kind = "dashboard"

    # A dedicated illustrated visual tile, not a repeated abstract ornament.
    draw.rounded_rectangle((785, 178, 1172, 535), radius=28, fill=(13, 22, 43), outline=accent, width=4)
    draw.rounded_rectangle((815, 204, 1142, 247), radius=13, fill=glow_color)
    draw.text((835, 211), "विषय से जुड़ा दृश्य", font=font(font_candidates, 21), fill=(255, 255, 255))

    if kind == "thumbnail":
        # Phone with a video thumbnail preview.
        draw.rounded_rectangle((900, 268, 1070, 500), radius=26, fill=(5, 9, 20), outline=(220, 230, 245), width=5)
        draw.rounded_rectangle((918, 290, 1052, 405), radius=12, fill=(35, 72, 125))
        draw.ellipse((955, 320, 1015, 380), fill=accent)
        draw.polygon([(977, 332), (977, 368), (1005, 350)], fill=(8, 15, 30))
        draw.rounded_rectangle((925, 420, 1045, 433), radius=6, fill=(220, 230, 245))
        draw.rounded_rectangle((925, 444, 1010, 455), radius=5, fill=glow_color)
        draw.rounded_rectangle((958, 478, 1012, 485), radius=4, fill=(150, 165, 190))
    elif kind == "chart":
        # Analytics card with bars and a rising retention line.
        draw.text((825, 270), "दर्शक डेटा", font=font(font_candidates, 24), fill=(245, 248, 255))
        for gx in range(4):
            ygrid = 315 + gx * 45
            draw.line((830, ygrid, 1125, ygrid), fill=(45, 58, 82), width=2)
        bars = [65, 110, 150, 122, 190, 225]
        for j, height in enumerate(bars):
            x = 845 + j * 43
            draw.rounded_rectangle((x, 495-height, x+25, 495), radius=7, fill=accent)
        pts = [(845, 385), (890, 360), (935, 350), (980, 325), (1025, 310), (1070, 285)]
        draw.line(pts, fill=(255, 255, 255), width=5)
        for px, py in pts:
            draw.ellipse((px-6, py-6, px+6, py+6), fill=(255, 255, 255))
    elif kind == "workflow":
        # Video editor monitor, timeline, audio waveform and clip blocks.
        draw.rounded_rectangle((835, 275, 1120, 420), radius=15, fill=(5, 10, 22), outline=(190, 205, 230), width=4)
        draw.rectangle((850, 290, 1105, 395), fill=(28, 58, 96))
        draw.polygon([(955, 320), (955, 370), (1000, 345)], fill=accent)
        draw.line((970, 423, 970, 445), fill=(200, 210, 230), width=8)
        draw.line((920, 447, 1020, 447), fill=(200, 210, 230), width=8)
        for j, width in enumerate((80, 110, 72, 95)):
            x = 835 + j * 72
            draw.rounded_rectangle((x, 466, x+width, 486), radius=6, fill=accent if j % 2 == 0 else glow_color)
        for j, h in enumerate((12, 23, 15, 29, 18, 32, 14, 24, 11, 20)):
            x = 845 + j * 27
            draw.rounded_rectangle((x, 502-h//2, x+9, 502+h//2), radius=4, fill=(210, 225, 245))
    elif kind == "idea":
        # Bright idea bulb with rays and idea notes.
        draw.ellipse((900, 285, 1060, 445), fill=(255, 190, 65), outline=(255, 240, 190), width=5)
        draw.rounded_rectangle((940, 420, 1020, 462), radius=10, fill=(220, 230, 245))
        draw.line((950, 470, 1010, 470), fill=(220, 230, 245), width=8)
        for angle in range(0, 360, 45):
            import math
            rad = math.radians(angle)
            x1, y1 = 980 + 100*math.cos(rad), 365 + 100*math.sin(rad)
            x2, y2 = 980 + 130*math.cos(rad), 365 + 130*math.sin(rad)
            draw.line((x1, y1, x2, y2), fill=accent, width=7)
        draw.rounded_rectangle((825, 300, 900, 350), radius=10, fill=glow_color)
        draw.rounded_rectangle((1060, 385, 1130, 435), radius=10, fill=glow_color)
    elif kind == "calendar":
        # Weekly content calendar with selected posting days.
        draw.rounded_rectangle((835, 270, 1125, 495), radius=18, fill=(7, 13, 28), outline=(210, 220, 240), width=4)
        draw.rounded_rectangle((835, 270, 1125, 320), radius=15, fill=accent)
        for col in range(4):
            for row in range(3):
                x, y = 858 + col*65, 342 + row*48
                draw.rounded_rectangle((x, y, x+42, y+31), radius=7, fill=glow_color if (col+row) % 2 == 0 else (35, 48, 70))
        draw.line((875, 405, 890, 420, 918, 385), fill=(255, 255, 255), width=7)
        draw.line((1005, 453, 1020, 468, 1048, 433), fill=(255, 255, 255), width=7)
    else:
        # Creator dashboard with channel card, view graph and play preview.
        draw.rounded_rectangle((835, 270, 1125, 495), radius=18, fill=(7, 13, 28), outline=(210, 220, 240), width=4)
        draw.ellipse((860, 292, 925, 357), fill=accent)
        draw.polygon([(885, 307), (885, 342), (912, 324)], fill=(8, 15, 30))
        draw.rounded_rectangle((940, 300, 1095, 314), radius=6, fill=(225, 235, 250))
        draw.rounded_rectangle((940, 326, 1045, 337), radius=5, fill=glow_color)
        draw.line((860, 450, 1098, 450), fill=(45, 58, 82), width=3)
        graph = [(865, 425), (910, 410), (950, 420), (995, 375), (1040, 385), (1095, 345)]
        draw.line(graph, fill=accent, width=6)
        for px, py in graph:
            draw.ellipse((px-5, py-5, px+5, py+5), fill=(255, 255, 255))


def draw_slide(index, heading, lines, footer):
    # Editorial layout: teaching text on the left, topic-specific illustration on the right.
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
    d.rounded_rectangle((48, 48, W-48, H-48), radius=30, outline=(*glow_color,), width=3)
    d.rounded_rectangle((82, 86, 370, 130), radius=14, fill=accent)
    d.text((102, 94), f"सीखें  •  भाग {index}", font=font(font_candidates, 22), fill=(8, 12, 28))
    # Keep the heading and bullets on the left so the illustration remains unobstructed.
    compact_title_font = font(font_candidates, 48)
    title_lines = textwrap.wrap(heading, width=20)[:2]
    title_y = 165
    for title_line in title_lines:
        d.text((90, title_y), title_line, font=compact_title_font, fill=(255, 255, 255), stroke_width=1)
        title_y += 58
    y = max(285, title_y + 10)
    for line in lines:
        wrapped = textwrap.wrap(line, width=25)
        for part in wrapped:
            d.rounded_rectangle((90, y+7, 106, y+31), radius=5, fill=accent)
            d.text((130, y), part, font=font(regular_candidates, 27), fill=(238, 242, 252))
            y += 42
        y += 8
    draw_topic_visual(d, heading, accent, glow_color, topic_key)
    d.line((90, H-118, W-90, H-118), fill=(*glow_color,), width=2)
    d.text((90, H-100), footer, font=small_font, fill=(196, 210, 236))
    d.text((W-210, H-100), f"{index:02d} / 08", font=small_font, fill=(255, 210, 105))
    d.rounded_rectangle((90, H-65, W-90, H-57), radius=4, fill=(35, 47, 70))
    d.rounded_rectangle((90, H-65, 90 + int((W-180)*index/8), H-57), radius=4, fill=accent)
    path = OUT / f"slide-{index:02d}.png"
    im.save(path)
    slides.append(path)
)