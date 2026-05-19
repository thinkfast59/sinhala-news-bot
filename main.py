import os, json, random, re, textwrap, requests, feedparser
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POSTED_FILE = "posted.json"
IMAGE_FILE = "tv_news.jpg"
AUDIO_FILE = "voice.mp3"
VIDEO_FILE = "tv_news.mp4"

translator = Translator()

RSS_FEEDS = [
    "https://www.adaderana.lk/rss.php",
    "https://www.newsfirst.lk/feed/",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

def load_posted():
    if not os.path.exists(POSTED_FILE):
        return []
    try:
        return json.load(open(POSTED_FILE, "r", encoding="utf-8"))
    except:
        return []

def save_posted(posted):
    json.dump(posted[-300:], open(POSTED_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def clean(text):
    text = re.sub("<.*?>", "", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return text.strip()

def si(text):
    try:
        return translator.translate(text, dest="si").text
    except:
        return text

def font(size):
    paths = [
        "/usr/share/fonts/truetype/noto/NotoSansSinhala-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifSinhala-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

def get_news():
    posted = load_posted()
    news_list = []

    for feed in RSS_FEEDS:
        try:
            data = feedparser.parse(feed)
            for e in data.entries[:20]:
                link = getattr(e, "link", "")
                title = clean(getattr(e, "title", ""))
                summary = clean(getattr(e, "summary", "")) or title

                if link and title and link not in posted:
                    news_list.append({
                        "title": title,
                        "summary": summary,
                        "link": link
                    })
        except Exception as er:
            print("Feed error:", er)

    return random.choice(news_list) if news_list else None

def make_script(title, summary):
    title_si = si(title)
    summary_si = si(summary)

    script = f"""
ලෝක පුවත් සිංහලෙන්.

අද ප්‍රධාන පුවත මෙයයි.

{title_si}

{summary_si}

මෙම පුවත පිළිබඳ වැඩිදුර තොරතුරු ඉදිරියේදී බලාපොරොත්තු විය හැකිය.
""".strip()

    caption = f"""
ලෝක පුවත් සිංහලෙන්

{title_si}

{summary_si}

#ලෝකපුවත් #සිංහලපුවත් #SriLankaNews #WorldNews
""".strip()

    return title_si, summary_si, script, caption

def make_tv_image(title_si, summary_si):
    img = Image.new("RGB", (1080, 1920), (12, 18, 32))
    draw = ImageDraw.Draw(img)

    red = (190, 0, 0)
    white = (255, 255, 255)
    yellow = (255, 210, 40)

    draw.rectangle((0, 0, 1080, 150), fill=red)
    draw.text((45, 38), "ලෝක පුවත් සිංහලෙන්", font=font(52), fill=white)

    draw.rectangle((45, 210, 1035, 360), fill=(25, 40, 70))
    draw.text((75, 250), "BREAKING NEWS", font=font(58), fill=yellow)

    y = 460
    for line in textwrap.wrap(title_si, width=24)[:5]:
        draw.text((60, y), line, font=font(62), fill=white)
        y += 85

    y += 40
    for line in textwrap.wrap(summary_si, width=32)[:8]:
        draw.text((60, y), line, font=font(38), fill=white)
        y += 58

    draw.rectangle((0, 1780, 1080, 1920), fill=red)
    draw.text((45, 1825), "Sri Lanka • World • Breaking News", font=font(38), fill=white)

    img.save(IMAGE_FILE, "JPEG", quality=95)

def make_video(script):
    tts = gTTS(script[:1200], lang="si")
    tts.save(AUDIO_FILE)

    audio = AudioFileClip(AUDIO_FILE)
    duration = min(max(audio.duration, 18), 60)

    clip = ImageClip(IMAGE_FILE).set_duration(duration).set_audio(audio)
    clip.write_videofile(
        VIDEO_FILE,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    audio.close()
    clip.close()

def send_video(caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(VIDEO_FILE, "rb") as v:
        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "caption": caption[:1024]
            },
            files={"video": v},
            timeout=180
        )
    print(r.text)
    return r.status_code == 200

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing Telegram secrets")
        return

    news = get_news()
    if not news:
        print("No news found")
        return

    title_si, summary_si, script, caption = make_script(news["title"], news["summary"])

    make_tv_image(title_si, summary_si)
    make_video(script)

    if send_video(caption):
        posted = load_posted()
        posted.append(news["link"])
        save_posted(posted)
        print("Video sent successfully")
    else:
        print("Telegram send failed")

if __name__ == "__main__":
    main()
