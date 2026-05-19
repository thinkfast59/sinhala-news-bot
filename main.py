import os
import re
import json
import time
import random
import hashlib
import subprocess
from io import BytesIO
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, AudioFileClip


# =========================================
# SETTINGS
# =========================================

PAGE_NAME = "ලෝක පුවත්"

OUTPUT_DIR = "output"
ASSET_DIR = "assets"
STATE_DIR = "state"

USED_FILE = os.path.join(STATE_DIR, "used.json")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

RUN_FOREVER = True
RUN_EVERY_MINUTES = 60

translator = GoogleTranslator(source='auto', target='si')


# =========================================
# RSS FEEDS
# =========================================

RSS_FEEDS = [

    # Sri Lanka
    "https://www.adaderana.lk/rss.php",
    "https://www.hirunews.lk/rss/english.xml",

    # World
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.skynews.com/feeds/rss/world.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]


# =========================================
# HELPERS
# =========================================

def clean_text(text):
    text = BeautifulSoup(text or "", "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def shorten(text, max_chars):
    text = clean_text(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def safe_filename(text):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text)[:80]


def load_used():
    if os.path.exists(USED_FILE):
        try:
            with open(USED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    return []


def save_used(data):
    os.makedirs(STATE_DIR, exist_ok=True)

    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(data[-2000:], f, ensure_ascii=False, indent=2)


# =========================================
# TRANSLATION
# =========================================

def translate_to_sinhala(text):

    try:
        translated = translator.translate(text)

        translated = translated.replace("ශ්\u200dරී", "ශ්‍රී")

        return translated

    except Exception as e:
        print("Translation error:", e)
        return text


# =========================================
# FONT
# =========================================

def get_font(size, bold=False):

    fonts = [

        "/usr/share/fonts/truetype/noto/NotoSansSinhala-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in fonts:
        try:
            return ImageFont.truetype(path, size)
        except:
            pass

    return ImageFont.load_default()


# =========================================
# IMAGE
# =========================================

def cover_resize(img, size):

    target_w, target_h = size

    scale = max(
        target_w / img.width,
        target_h / img.height
    )

    new_size = (
        int(img.width * scale),
        int(img.height * scale)
    )

    img = img.resize(new_size)

    left = (img.width - target_w) // 2
    top = (img.height - target_h) // 2

    return img.crop((
        left,
        top,
        left + target_w,
        top + target_h
    ))


def download_image(url, output_path):

    try:

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return False

        img = Image.open(BytesIO(r.content)).convert("RGB")

        img.save(output_path)

        return True

    except Exception as e:

        print("Image error:", e)
        return False


# =========================================
# NEWS
# =========================================

def get_news():

    used = set(load_used())

    feeds = RSS_FEEDS[:]
    random.shuffle(feeds)

    for feed_url in feeds:

        try:

            feed = feedparser.parse(feed_url)

            entries = list(feed.entries[:20])

            random.shuffle(entries)

            for entry in entries:

                title = clean_text(entry.get("title", ""))

                summary = clean_text(
                    entry.get("summary", "") or
                    entry.get("description", "")
                )

                link = entry.get("link", "")

                if not title:
                    continue

                news_id = hashlib.md5(link.encode()).hexdigest()

                if news_id in used:
                    continue

                image_url = None

                if "media_content" in entry:
                    media = entry.media_content[0]
                    image_url = media.get("url")

                return {
                    "id": news_id,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "image_url": image_url
                }

        except Exception as e:

            print("Feed error:", e)

    return None


# =========================================
# SINHALA SCRIPT
# =========================================

def make_script(news):

    title_si = translate_to_sinhala(
        shorten(news["title"], 180)
    )

    summary_si = translate_to_sinhala(
        shorten(news["summary"], 600)
    )

    script = (
        f"මෙය නවතම ලෝක පුවත් යාවත්කාලීනයකි. "
        f"{title_si}. "
        f"{summary_si}. "
        f"තවත් පුවත් සඳහා අප සමඟ රැඳී සිටින්න."
    )

    return script


# =========================================
# SINHALA TTS
# =========================================

def create_voice(script, output_path):

    temp_txt = "tts.txt"

    with open(temp_txt, "w", encoding="utf-8") as f:
        f.write(script)

    command = [
        "edge-tts",
        "--voice",
        "si-LK-SameeraNeural",
        "--file",
        output_path,
        "--text",
        script
    ]

    subprocess.run(command)


# =========================================
# VIDEO IMAGE
# =========================================

def create_news_image(news, image_path):

    if os.path.exists(image_path):

        img = Image.open(image_path).convert("RGB")

    else:

        img = Image.new(
            "RGB",
            (VIDEO_WIDTH, VIDEO_HEIGHT),
            (15, 20, 35)
        )

    img = cover_resize(
        img,
        (VIDEO_WIDTH, VIDEO_HEIGHT)
    )

    overlay = Image.new(
        "RGBA",
        img.size,
        (0, 0, 0, 110)
    )

    img = Image.alpha_composite(
        img.convert("RGBA"),
        overlay
    ).convert("RGB")

    draw = ImageDraw.Draw(img)

    title = translate_to_sinhala(
        shorten(news["title"], 120)
    )

    font = get_font(55, True)

    wrapped = text_wrap(
        title,
        font,
        900
    )

    y = 1200

    for line in wrapped:

        draw.text(
            (80, y),
            line,
            font=font,
            fill="white"
        )

        y += 80

    logo_font = get_font(60, True)

    draw.text(
        (70, 80),
        PAGE_NAME,
        font=logo_font,
        fill=(255, 60, 60)
    )

    out_path = "frame.jpg"

    img.save(out_path)

    return out_path


def text_wrap(text, font, max_width):

    lines = []
    words = text.split()

    current = ""

    dummy = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy)

    for word in words:

        test = current + " " + word

        width = draw.textbbox(
            (0, 0),
            test,
            font=font
        )[2]

        if width <= max_width:

            current = test

        else:

            lines.append(current.strip())
            current = word

    if current:
        lines.append(current.strip())

    return lines


# =========================================
# VIDEO
# =========================================

def create_video(image_path, audio_path, output_path):

    audio = AudioFileClip(audio_path)

    duration = audio.duration

    video = (
        ImageClip(image_path)
        .set_duration(duration)
        .set_audio(audio)
    )

    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    audio.close()
    video.close()


# =========================================
# TELEGRAM
# =========================================

def post_to_telegram(video_path, caption):

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendVideo"
    )

    with open(video_path, "rb") as f:

        files = {
            "video": f
        }

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption[:1024],
            "supports_streaming": "true"
        }

        r = requests.post(
            url,
            data=data,
            files=files,
            timeout=600
        )

    print(r.text)


# =========================================
# CAPTION
# =========================================

def make_caption(news):

    title = translate_to_sinhala(
        shorten(news["title"], 200)
    )

    hashtags = [
        "#ලෝකපුවත්",
        "#ශ්‍රීලංකාව",
        "#BreakingNews",
        "#WorldNews",
        "#SinhalaNews"
    ]

    return (
        f"{title}\n\n"
        "නවතම ලෝක පුවත් වීඩියෝව දැන් නරඹන්න.\n\n"
        + " ".join(hashtags)
    )


# =========================================
# MAIN
# =========================================

def run_once():

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ASSET_DIR, exist_ok=True)

    news = get_news()

    if not news:

        print("No news found")
        return

    print(news["title"])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    image_path = os.path.join(
        ASSET_DIR,
        f"{stamp}.jpg"
    )

    voice_path = os.path.join(
        ASSET_DIR,
        f"{stamp}.mp3"
    )

    video_path = os.path.join(
        OUTPUT_DIR,
        f"{stamp}.mp4"
    )

    if news.get("image_url"):

        download_image(
            news["image_url"],
            image_path
        )

    script = make_script(news)

    print(script)

    create_voice(
        script,
        voice_path
    )

    frame = create_news_image(
        news,
        image_path
    )

    create_video(
        frame,
        voice_path,
        video_path
    )

    caption = make_caption(news)

    post_to_telegram(
        video_path,
        caption
    )

    used = load_used()
    used.append(news["id"])

    save_used(used)

    print("DONE")


# =========================================
# LOOP
# =========================================

def main():

    if RUN_FOREVER:

        while True:

            try:

                run_once()

            except Exception as e:

                print(e)

            time.sleep(
                RUN_EVERY_MINUTES * 60
            )

    else:

        run_once()


if __name__ == "__main__":
    main()
