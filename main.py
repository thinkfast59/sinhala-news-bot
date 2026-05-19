import os, json, random, re, textwrap
import requests, feedparser
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from gtts import gTTS

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POSTED_FILE = "posted.json"
IMAGE_FILE = "post.jpg"
VIDEO_FILE = "news_reel.mp4"
AUDIO_FILE = "voice.mp3"

translator = Translator()

RSS_FEEDS = [
    # Sri Lanka
    "https://www.adaderana.lk/rss.php",
    "https://www.newsfirst.lk/feed/",
    "https://www.dailynews.lk/feed/",

    # World
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]

HASHTAGS = [
    "#ලෝකපුවත්", "#සිංහලපුවත්", "#SriLankaNews",
    "#WorldNews", "#BreakingNews", "#ViralNews"
]

def load_posted():
    if not os.path.exists(POSTED_FILE):
        return []
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_posted(posted):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted[-300:], f, ensure_ascii=False, indent=2)

def clean_html(text):
    if not text:
        return ""
    text = re.sub("<.*?>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return text.strip()

def translate_si(text):
    try:
        return translator.translate(text, dest="si").text
    except:
        return text

def get_news():
    posted = load_posted()
    articles = []

    for feed in RSS_FEEDS:
        try:
            data = feedparser.parse(feed)
            for entry in data.entries[:20]:
                if not hasattr(entry, "link"):
                    continue
                if entry.link in posted:
                    continue

                title = clean_html(getattr(entry, "title", ""))
                summary = clean_html(getattr(entry, "summary", "")) or title

                if title:
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.link,
                        "source": feed
                    })
        except Exception as e:
            print("Feed error:", e)

    if not articles:
        return None

    return random.choice(articles)

def make_post_text(title_si, summary_si, link):
    hooks = [
        "🔥 දැන් ලැබුණු විශේෂ පුවතක්",
        "🌍 ලෝකයම කතා කරන පුවතක්",
        "🇱🇰 අද අවධානයට ලක්වූ පුවතක්",
        "⚡ වේගයෙන් පැතිරෙන පුවතක්",
    ]

    return f"""
{random.choice(hooks)}

📰 {title_si}

{summary_si}

🌐 වැඩි විස්තර:
{link}

{' '.join(random.sample(HASHTAGS, 4))}
""".strip()

def download_image():
    try:
        image_url = f"https://picsum.photos/1080/1920?random={random.randint(1,999999)}"
        img_data = requests.get(image_url, timeout=20).content
        img = Image.open(BytesIO(img_data)).convert("RGB")
        img = img.resize((1080, 1920))
        img.save(IMAGE_FILE, "JPEG", quality=95)
        return True
    except Exception as e:
        print("Image error:", e)
        return False

def get_font(size):
    possible = [
        "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifSinhala-Regular.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
        "arial.ttf"
    ]
    for font in possible:
        try:
            return ImageFont.truetype(font, size)
        except:
            pass
    return ImageFont.load_default()

def create_news_image(title_si):
    if not download_image():
        img = Image.new("RGB", (1080, 1920), (20, 30, 60))
    else:
        img = Image.open(IMAGE_FILE).convert("RGB")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 120))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(img)
    title_font = get_font(58)
    small_font = get_font(38)

    draw.text((60, 120), "ලෝක පුවත් සිංහලෙන්", font=small_font, fill="white")

    wrapped = textwrap.wrap(title_si, width=22)
    y = 650
    for line in wrapped[:6]:
        draw.text((60, y), line, font=title_font, fill="white")
        y += 80

    draw.text((60, 1700), "World News Sinhala", font=small_font, fill="white")

    img.convert("RGB").save(IMAGE_FILE, "JPEG", quality=95)

def create_reel(title_si, summary_si):
    voice_text = f"{title_si}. {summary_si}"
    tts = gTTS(text=voice_text[:900], lang="si")
    tts.save(AUDIO_FILE)

    audio = AudioFileClip(AUDIO_FILE)
    duration = min(max(audio.duration, 12), 45)

    clip = ImageClip(IMAGE_FILE).set_duration(duration).resize((1080, 1920))
    clip = clip.set_audio(audio.subclip(0, min(audio.duration, duration)))
    clip.write_videofile(
        VIDEO_FILE,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

def send_telegram_photo(caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(IMAGE_FILE, "rb") as img:
        res = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption[:1024],
            "parse_mode": "HTML"
        }, files={"photo": img})
    print(res.text)
    return res.status_code == 200

def send_telegram_video(caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(VIDEO_FILE, "rb") as video:
        res = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption[:1024]
        }, files={"video": video})
    print(res.text)
    return res.status_code == 200

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    news = get_news()
    if not news:
        print("No new news")
        return

    title_si = translate_si(news["title"])
    summary_si = translate_si(news["summary"])
    caption = make_post_text(title_si, summary_si, news["link"])

    create_news_image(title_si)

    mode = random.choice(["photo", "video"])

    success = False

    if mode == "video":
        try:
            create_reel(title_si, summary_si)
            success = send_telegram_video(caption)
        except Exception as e:
            print("Video error:", e)
            success = send_telegram_photo(caption)
    else:
        success = send_telegram_photo(caption)

    if success:
        posted = load_posted()
        posted.append(news["link"])
        save_posted(posted)
        print("✅ Telegram post success")
    else:
        print("❌ Telegram post failed")

if __name__ == "__main__":
    main()
