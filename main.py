import requests
import feedparser
import json
import random
import os
import re
from PIL import Image
from io import BytesIO
from googletrans import Translator

# =====================================
# FACEBOOK PAGE
# =====================================

PAGE_ID = "1020689164470492"
PAGE_ACCESS_TOKEN = "EAIFMs5yoDt0BRQ28GkPLAU4zLsHtxl8z0wN1tcFY8oDby981kL5ARgHRyDppMzcksfudWW41HV7ZBHx92TkIKBhUDNtQGUKaP8Fl6KO5n96w7MkPlrz2fn9EMDlMG70cZAZByfcOtTQOMxElfUqo1fd47E2blqRv55vnRYgo541wYxUQIQ6xkruHZCFZBsRb9HszSLqOlGareBvJB8kbg7lnx"

# =====================================
# FILES
# =====================================

POSTED_FILE = "posted.json"
IMAGE_FILE = "post.jpg"

# =====================================
# TRANSLATOR
# =====================================

translator = Translator()

# =====================================
# RSS FEEDS
# =====================================

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml"
]

# =====================================
# SETUP
# =====================================

if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w") as f:
        json.dump([], f)

try:
    with open(POSTED_FILE, "r") as f:
        posted = json.load(f)
except:
    posted = []

print("🌍 Sinhala World News Bot Started")

# =====================================
# CLEAN HTML
# =====================================

def clean_html(text):

    if not text:
        return ""

    text = re.sub("<.*?>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")

    return text.strip()

# =====================================
# FETCH NEWS
# =====================================

articles = []

for feed in RSS_FEEDS:

    try:

        data = feedparser.parse(feed)

        for entry in data.entries[:15]:

            if hasattr(entry, "link"):

                if entry.link not in posted:
                    articles.append(entry)

    except Exception as e:
        print("Feed Error:", e)

if not articles:
    print("❌ No new news")
    exit()

news = random.choice(articles)

# =====================================
# ARTICLE DATA
# =====================================

title = clean_html(news.title)

summary = ""

if hasattr(news, "summary"):
    summary = clean_html(news.summary)

if not summary:
    summary = title

link = news.link

# =====================================
# TRANSLATE TO SINHALA
# =====================================

try:

    sinhala_title = translator.translate(title, dest="si").text
    sinhala_summary = translator.translate(summary, dest="si").text

except Exception as e:

    print("Translation Error:", e)

    sinhala_title = title
    sinhala_summary = summary

# =====================================
# SINHALA CONTENT
# =====================================

post_text = f"""
🌍 ලෝක පුවත් සිංහලෙන්

🔥 ප්‍රධාන පුවත:
{sinhala_title}

📰 සිදුවීම:
{sinhala_summary}

📌 වැදගත් වන්නේ ඇයි?
මෙම පුවත ලෝකයේ බොහෝ දෙනාගේ අවධානය දිනාගෙන ඇති අතර ඉදිරි දිනවලදී වැඩි බලපෑම් ඇති කළ හැකිය.

🌐 වැඩි විස්තර:
{link}

#ලෝකපුවත් #සිංහල #WorldNews #BreakingNews
"""

# =====================================
# IMAGE
# =====================================

print("🖼 Downloading image...")

image_url = f"https://picsum.photos/800/600?random={random.randint(1,999999)}"

try:

    img_data = requests.get(image_url, timeout=15).content

    img = Image.open(BytesIO(img_data))
    img = img.convert("RGB")

    img.save(IMAGE_FILE, "JPEG", quality=95)

    image_ready = True

except Exception as e:

    print("Image Error:", e)
    image_ready = False

# =====================================
# POST TO FACEBOOK
# =====================================

print("🚀 Posting Sinhala news...")

try:

    if image_ready:

        url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/photos"

        with open(IMAGE_FILE, "rb") as img_file:

            files = {
                "source": img_file
            }

            data = {
                "caption": post_text,
                "access_token": PAGE_ACCESS_TOKEN
            }

            res = requests.post(url, files=files, data=data)

    else:

        url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/feed"

        data = {
            "message": post_text,
            "access_token": PAGE_ACCESS_TOKEN
        }

        res = requests.post(url, data=data)

    print(res.text)

    if res.status_code == 200 and "id" in res.text:

        print("✅ POST SUCCESS")

        posted.append(link)

        with open(POSTED_FILE, "w") as f:
            json.dump(posted, f)

    else:

        print("❌ POST FAILED")

except Exception as e:

    print("❌ ERROR:", e)
