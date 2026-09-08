import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import unquote
from pathlib import Path

from model_client import call_model

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_CSV_FILE = PROJECT_ROOT / "data/input/input_channels.csv"
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/all_scraped_output.csv"

def classify_with_local_llm(bio: str, handle: str, platform: str, extra: str = ""):
    prompt = f"""
    Analyze this {platform} creator's profile:
    Handle: {handle}
    Bio: {bio}
    {f"Extra: {extra}" if extra else ""}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Runway, Sora, Midjourney, Pika, Kling, ChatGPT, ComfyUI, Stable Diffusion, FLUX) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of content",
        "Region": "Country or location if detectable, else null",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15)
        return json.loads(response_text)
    except Exception:
        combined = f"{handle} {bio} {extra}".lower()
        tools = [t.title() for t in [
            "runway", "sora", "pika", "midjourney", "kling", "luma", "comfyui",
            "stable diffusion", "chatgpt", "claude", "cursor", "flux", "capcut",
            "elevenlabs", "heygen", "pixverse", "veo", "midjourney"
        ] if t in combined]
        return {
            "Tags": [platform, "AIGC", "Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "sora", "runway", "synthetic", "generative", "diffusion", "midjourney", "kling"]) else "hybrid",
            "Language": "English",
            "Region": "Global",
            "Evidence": "Rule-based keyword fallback"
        }


def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


TARGET_COLUMNS = [
    "ProfileURL", "Name/Handle", "Platform", "FollowerCount", "Email", "Tags",
    "OutreachStatus", "LastScrapedAt", "Region", "Language", "PrimaryAITool",
    "SampleContentURL", "AIGCVerdict", "DiscoveredAt", "Source", "Notes",
    "FeedURL", "ContactSourceURL", "EvidenceJSON"
]


def save_results(updated_rows, output_file):
    final_df = pd.DataFrame(updated_rows)
    for col in TARGET_COLUMNS:
        if col not in final_df.columns:
            final_df[col] = None
    final_df = final_df[TARGET_COLUMNS]
    final_df.to_csv(output_file, index=False)
    print(f"\n[✓] Saved {len(final_df)} records to '{output_file}'.")


# ============================================================
#  YOUTUBE SCRAPER (yt-dlp)
# ============================================================

def scrape_youtube(channel_url: str):
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True, 'extract_flat': True, 'skip_download': True,
            'playlist_items': '1', 'ignoreerrors': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if not info:
                return None
            channel_id = info.get('channel_id') or info.get('id', '')
            channel_name = info.get('channel') or info.get('uploader') or channel_url.split('/')[-1]
            description = info.get('description', '') or ''
            subscribers = info.get('channel_follower_count')
            sub_count = str(subscribers) if subscribers is not None else "N/A"
            video_count = info.get('playlist_count', 'N/A')

            sample_title, sample_url = "", ""
            if 'entries' in info and info['entries'] and info['entries'][0]:
                e = info['entries'][0]
                sample_title = e.get('title', '')
                sample_url = e.get('url') or e.get('webpage_url', '')

            ai_meta = classify_with_local_llm(description, channel_name, "YouTube", sample_title)
            email = extract_email(description)

            evidence = {
                "follower_count": {"source": "yt-dlp", "channelId": channel_id},
                "aigc_verdict": ai_meta.get("AIGCVerdict", "yes"),
                "recent_uploads": {"sample": sample_url, "title": sample_title}
            }

            return {
                "Handle": channel_name,
                "FollowerCount": sub_count,
                "Email": email,
                "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
                "LastScrapedAt": now_iso(),
                "Language": ai_meta.get("Language", "English"),
                "PrimaryAITool": ai_meta.get("PrimaryAITool"),
                "SampleContentURL": sample_url,
                "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
                "Notes": f"YouTube scrape: subs={sub_count}; videos={video_count}",
                "FeedURL": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}" if channel_id else "",
                "ContactSourceURL": f"{channel_url}/about",
                "EvidenceJSON": json.dumps(evidence)
            }
    except Exception as e:
        print(f"[-] YouTube error {channel_url}: {e}")
        return None


# ============================================================
#  VIMEO SCRAPER (yt-dlp + requests)
# ============================================================

def scrape_vimeo(channel_url: str):
    try:
        import yt_dlp
        handle = _extract_vimeo_handle(channel_url)
        ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True, 'playlist_items': '1', 'ignoreerrors': True}

        description, uploader, sample_title, sample_url, video_count = "", handle.replace("@", ""), "", channel_url, 0
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if info:
                uploader = info.get('uploader') or info.get('channel') or uploader
                description = info.get('description') or ""
                entries = info.get('entries', [])
                video_count = len(entries) if entries else info.get('playlist_count', 0)
                if entries and entries[0]:
                    sample_title = entries[0].get('title', '')
                    sample_url = entries[0].get('url') or entries[0].get('webpage_url', channel_url)

        if not description:
            try:
                r = requests.get(channel_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    og = re.search(r'property="og:description"\s+content="([^"]+)"', r.text)
                    if og:
                        description = og.group(1)
            except Exception:
                pass

        ai_meta = classify_with_local_llm(description, handle, "Vimeo", sample_title)
        email = extract_email(description)

        evidence = {"platform": "Vimeo", "handle": handle, "aigc_verdict": ai_meta.get("AIGCVerdict", "hybrid")}

        return {
            "Handle": handle,
            "FollowerCount": f"{video_count} videos" if video_count else "N/A",
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Region": ai_meta.get("Region") or "Global",
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": sample_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "Notes": f"Vimeo scrape: uploader={uploader}; videos={video_count}",
            "FeedURL": f"{channel_url.rstrip('/')}/videos/rss",
            "ContactSourceURL": channel_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Vimeo error {channel_url}: {e}")
        return None


def _extract_vimeo_handle(url):
    m = re.search(r'vimeo\.com/(?:channels/|user/)?([a-zA-Z0-9_\-]+)', url)
    return f"@{m.group(1)}" if m else f"@{url.split('/')[-1]}"


# ============================================================
#  CIVITAI SCRAPER (API)
# ============================================================

def scrape_civitai(profile_url: str):
    try:
        username = _extract_civitai_username(profile_url)
        if not username:
            return None
        api = "https://civitai.com/api/v1"

        r = requests.get(f"{api}/creators?query={username}&limit=1", timeout=15)
        if r.status_code != 200:
            return None
        items = r.json().get("items", [])
        creator = next((i for i in items if i.get("username", "").lower() == username.lower()), items[0] if items else None)
        if not creator:
            return None

        actual = creator.get("username", username)
        model_count = creator.get("modelCount", 0)

        mr = requests.get(f"{api}/models?username={actual}&limit=5", timeout=15)
        bio, model_tags = "", []
        if mr.status_code == 200:
            for m in mr.json().get("items", []):
                if m.get("description"):
                    bio += " " + re.sub('<[^<]+?>', '', m["description"])[:200]
                if m.get("tags"):
                    model_tags.extend(m["tags"])

        unique_tags = list(set(model_tags))[:5]
        summary = ", ".join(unique_tags)

        ai_meta = classify_with_local_llm(bio, actual, "Civitai", summary)
        email = extract_email(bio)

        evidence = {"platform": "Civitai", "username": actual, "model_count": model_count, "top_tags": unique_tags}

        return {
            "Handle": f"@{actual}",
            "FollowerCount": "N/A",
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool", "Stable Diffusion"),
            "SampleContentURL": f"https://civitai.com/user/{actual}",
            "AIGCVerdict": "yes",
            "Notes": f"Civitai API: models={model_count}; tags={summary[:40]}",
            "FeedURL": f"https://civitai.com/user/{actual}/models",
            "ContactSourceURL": f"https://civitai.com/user/{actual}" if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Civitai error {profile_url}: {e}")
        return None


def _extract_civitai_username(url):
    m = re.search(r'civitai\.com/user/([a-zA-Z0-9_\-\.]+)', url)
    if m:
        return m.group(1)
    parts = url.strip("/").split("/")
    return parts[-1] if parts else None


# ============================================================
#  PLAYWRIGHT-BASED SCRAPERS
#  (Threads, TikTok, Instagram, Facebook, LinkedIn, Reddit)
# ============================================================

def scrape_threads(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)
        handle = _extract_threads_handle(profile_url)

        bio = ""
        try:
            bio = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        except Exception:
            pass

        follower_count = "N/A"
        try:
            body = page.inner_text("body")
            m = re.search(r'([\d\.,]+[KkMmBb]?)\s*followers', body, re.IGNORECASE)
            if m:
                follower_count = m.group(1)
        except Exception:
            pass

        external_link = ""
        try:
            for l in page.locator('a[href*="http"]').all():
                href = l.get_attribute("href") or ""
                if not any(d in href for d in ["threads.net", "instagram.com", "facebook.com"]):
                    external_link = href
                    break
        except Exception:
            pass

        ai_meta = classify_with_local_llm(bio, handle or "", "Threads")
        email = extract_email(bio)

        evidence = {"platform": "Threads", "handle": handle, "bio_preview": bio[:100], "external_link": external_link}

        return {
            "Handle": handle,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": external_link or profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Threads scrape: followers={follower_count}; bio_preview={bio[:60]}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Threads error {profile_url}: {e}")
        return None


def _extract_threads_handle(url):
    m = re.search(r'threads\.(?:net|com)/(@[a-zA-Z0-9_\.\-]+)', url)
    return m.group(1) if m else (url.split('/')[-1] if '/' in url else url)


def scrape_tiktok(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2)

        m = re.search(r'tiktok\.com/(@[a-zA-Z0-9_\.\-]+)', profile_url)
        handle = m.group(1) if m else profile_url.split('/')[-1]

        follower_count = "N/A"
        try:
            el = page.locator('[data-e2e="followers-count"]').first
            if el.is_visible():
                follower_count = el.inner_text().strip()
        except Exception:
            pass

        bio = ""
        try:
            el = page.locator('[data-e2e="user-bio"]').first
            if el.is_visible():
                bio = el.inner_text().strip()
        except Exception:
            pass

        external_link = ""
        try:
            el = page.locator('[data-e2e="user-link"]').first
            if el.is_visible():
                external_link = el.inner_text().strip()
        except Exception:
            pass

        ai_meta = classify_with_local_llm(bio, handle, "TikTok")
        email = extract_email(bio)

        evidence = {"platform": "TikTok", "handle": handle, "bio_preview": bio[:100], "external_link": external_link}

        return {
            "Handle": handle,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": external_link or profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"TikTok scrape: followers={follower_count}; bio_link={external_link or 'none'}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] TikTok error {profile_url}: {e}")
        return None


def scrape_instagram(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""

        follower_count = "N/A"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*Followers', og_desc, re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)

        bio = ""
        try:
            bio_el = page.locator('header section').first
            bio = bio_el.inner_text() if bio_el.is_visible() else og_desc
        except Exception:
            bio = og_desc

        hm = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', profile_url)
        handle = f"@{hm.group(1).replace('/', '')}" if hm else profile_url.split('/')[-1]

        ai_meta = classify_with_local_llm(bio, handle, "Instagram")
        email = extract_email(bio)

        evidence = {"platform": "Instagram", "handle": handle, "og_description": og_desc[:120]}

        return {
            "Handle": handle,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Instagram scrape: followers={follower_count}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Instagram error {profile_url}: {e}")
        return None


def scrape_facebook(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        handle = _extract_facebook_handle(profile_url)

        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""

        follower_count = "N/A"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:followers|likes)', og_desc, re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)
        else:
            try:
                body = page.inner_text("body")
                bm = re.search(r'([\d\.,]+[KkMmBb]?)\s*followers', body, re.IGNORECASE)
                if bm:
                    follower_count = bm.group(1)
            except Exception:
                pass

        bio = og_desc
        try:
            intro = page.locator('div[role="main"]').inner_text()
            if intro and len(intro) > len(bio):
                bio = intro[:300]
        except Exception:
            pass

        external_link = ""
        try:
            for l in page.locator('a[href*="http"]').all():
                href = l.get_attribute("href") or ""
                if "l.facebook.com" in href:
                    external_link = _clean_fb_url(href)
                    break
                elif not any(d in href for d in ["facebook.com", "fb.com", "instagram.com"]):
                    external_link = href
                    break
        except Exception:
            pass

        ai_meta = classify_with_local_llm(bio, handle or og_title, "Facebook")
        email = extract_email(bio)

        evidence = {"platform": "Facebook", "handle": handle, "title": og_title, "bio_preview": bio[:100], "external_link": external_link}

        return {
            "Handle": handle or og_title,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": external_link or profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Facebook scrape: followers={follower_count}; bio_preview={bio[:60].strip()}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Facebook error {profile_url}: {e}")
        return None


def _extract_facebook_handle(url):
    m = re.search(r'facebook\.com/([a-zA-Z0-9_\.\-]+)', url)
    if m:
        name = m.group(1)
        if name not in ["profile.php", "pages", "groups", "share"]:
            return f"@{name}"
    return url.split('/')[-1] or url


def _clean_fb_url(url):
    if "l.facebook.com/l.php" in url:
        m = re.search(r'[?&]u=([^&]+)', url)
        if m:
            return unquote(m.group(1))
    return url


def scrape_linkedin(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        handle = _extract_linkedin_handle(profile_url)

        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""

        bio = og_desc
        name = og_title.split("-")[0].strip() if "-" in og_title else (og_title.split("|")[0].strip() or handle)

        try:
            headline = page.locator('.top-card-layout__headline').first
            if headline.is_visible():
                bio = f"{headline.inner_text().strip()} | {og_desc}"
        except Exception:
            pass

        follower_count = "N/A"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:followers|connections)', f"{og_desc} {page.inner_text('body')}", re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)

        region = "Global"
        try:
            loc = page.locator('.top-card-layout__first-subline').first
            if loc.is_visible():
                region = loc.inner_text().strip()
        except Exception:
            pass

        ai_meta = classify_with_local_llm(bio, name, "LinkedIn")
        email = extract_email(bio)

        evidence = {"platform": "LinkedIn", "handle": handle, "name": name, "headline_preview": bio[:120]}

        return {
            "Handle": handle or name,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Region": region if region != "Global" else ai_meta.get("Region", "Global"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "Notes": f"LinkedIn scrape: followers/conn={follower_count}; headline={bio[:60].strip()}",
            "FeedURL": f"{profile_url}/recent-activity/all/",
            "ContactSourceURL": profile_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] LinkedIn error {profile_url}: {e}")
        return None


def _extract_linkedin_handle(url):
    m = re.search(r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_\.\-]+)', url)
    return f"@{m.group(1).replace('/', '')}" if m else (url.split('/')[-1] or url)


def scrape_reddit(page, profile_url: str):
    try:
        username = _extract_reddit_username(profile_url)
        if not username:
            return None

        reddit_url = f"https://www.reddit.com/user/{username}/"
        page.goto(reddit_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2)

        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""

        page_text = page.inner_text("body")
        karma_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:karma|Post Karma|Comment Karma)', page_text, re.IGNORECASE)
        follower_count = f"{karma_match.group(1)} karma" if karma_match else "N/A"

        bio = og_desc
        try:
            desc = page.locator('shreddit-profile-about').first
            if desc.is_visible():
                bio = f"{desc.inner_text().strip()} | {og_desc}"
        except Exception:
            pass

        sample_post = ""
        try:
            fp = page.locator('a[slot="full-post-link"]').first
            if fp.is_visible():
                sample_post = fp.inner_text().strip()
        except Exception:
            pass

        ai_meta = classify_with_local_llm(bio, f"u/{username}", "Reddit", sample_post)
        email = extract_email(bio)

        evidence = {"platform": "Reddit", "handle": f"u/{username}", "karma": follower_count, "bio_preview": bio[:120]}

        return {
            "Handle": f"u/{username}",
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": now_iso(),
            "Region": ai_meta.get("Region") or "Global",
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": reddit_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Reddit scrape: karma={follower_count}; bio={bio[:60].strip()}",
            "FeedURL": f"https://www.reddit.com/user/{username}/submitted.rss",
            "ContactSourceURL": reddit_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Reddit error {profile_url}: {e}")
        return None


def _extract_reddit_username(url):
    if not isinstance(url, str):
        return None
    m = re.search(r'reddit\.com/user/([a-zA-Z0-9_\-]+)', url)
    if m:
        return m.group(1)
    m2 = re.search(r'reddit\.com/u/([a-zA-Z0-9_\-]+)', url)
    if m2:
        return m2.group(1)
    if url.startswith("u/"):
        return url.replace("u/", "")
    return url.strip().split('/')[-1] or None


# ============================================================
#  PLATFORM ROUTER
# ============================================================

PLATFORM_SCRAPERS = {
    "youtube": ("yt-dlp", scrape_youtube),
    "yt": ("yt-dlp", scrape_youtube),
    "vimeo": ("yt-dlp", scrape_vimeo),
    "vm": ("yt-dlp", scrape_vimeo),
    "civitai": ("api", scrape_civitai),
    "threads": ("browser", scrape_threads),
    "thread": ("browser", scrape_threads),
    "tiktok": ("browser", scrape_tiktok),
    "tt": ("browser", scrape_tiktok),
    "instagram": ("browser", scrape_instagram),
    "ig": ("browser", scrape_instagram),
    "facebook": ("browser", scrape_facebook),
    "fb": ("browser", scrape_facebook),
    "linkedin": ("browser", scrape_linkedin),
    "li": ("browser", scrape_linkedin),
    "reddit": ("browser", scrape_reddit),
    "rd": ("browser", scrape_reddit),
}

URL_PATTERNS = {
    "youtube": ["youtube.com", "youtu.be"],
    "vimeo": ["vimeo.com"],
    "civitai": ["civitai.com"],
    "threads": ["threads.net", "threads.com"],
    "tiktok": ["tiktok.com"],
    "instagram": ["instagram.com"],
    "facebook": ["facebook.com", "fb.com"],
    "linkedin": ["linkedin.com"],
    "reddit": ["reddit.com"],
}


def detect_platform(row, platform_col, url_col):
    platform_val = str(row.get(platform_col, "")).strip().lower()
    url_val = str(row.get(url_col, "")).strip().lower()

    if platform_val in PLATFORM_SCRAPERS:
        return platform_val

    for plat, patterns in URL_PATTERNS.items():
        if any(p in url_val for p in patterns):
            return plat

    return None


# ============================================================
#  UNIFIED MAIN
# ============================================================

def main():
    if not os.path.exists(INPUT_CSV_FILE):
        print(f"[!] '{INPUT_CSV_FILE}' not found. Please create it.")
        return

    print(f"[+] Loading {INPUT_CSV_FILE}...")
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [c.strip() for c in df.columns]

    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    # Group rows by platform
    groups = {}
    for idx, row in df.iterrows():
        plat = detect_platform(row, platform_col, url_col)
        if plat:
            groups.setdefault(plat, []).append((idx, row))
        else:
            print(f"[!] Skipping row {idx}: couldn't detect platform for {row.get(url_col, '')}")

    print(f"[+] Platforms found: {', '.join(f'{k}({len(v)})' for k, v in sorted(groups.items()))}\n")

    all_updated = []
    browser_plats = {k for k, v in PLATFORM_SCRAPERS.items() if v[0] == "browser"}
    needs_browser = any(p in browser_plats for p in groups)

    # --- Browser-based scrapers ---
    if needs_browser:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[!] playwright not installed. Run: pip install playwright && playwright install chromium")
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            for plat in sorted(groups.keys()):
                if plat not in browser_plats:
                    continue
                rows = groups[plat]
                scraper_fn = PLATFORM_SCRAPERS[plat][1]
                print(f"\n--- Scraping {plat.upper()} ({len(rows)} profiles) ---")

                for i, (idx, row) in enumerate(rows, 1):
                    url = str(row[url_col]).strip()
                    print(f"[{i}/{len(rows)}] {plat}: {url}")

                    scraped = scraper_fn(page, url)
                    row_dict = row.to_dict()
                    row_dict["Platform"] = plat.title()

                    if scraped:
                        row_dict["Name/Handle"] = scraped.get("Handle") or row_dict.get("Name/Handle")
                        row_dict["FollowerCount"] = scraped.get("FollowerCount") or row_dict.get("FollowerCount")
                        if row_dict.get("Email") in [None, "", "not exposed"]:
                            row_dict["Email"] = scraped.get("Email")
                        row_dict["LastScrapedAt"] = scraped.get("LastScrapedAt")
                        row_dict["Region"] = scraped.get("Region") or row_dict.get("Region")
                        row_dict["Language"] = scraped.get("Language") or row_dict.get("Language")
                        row_dict["PrimaryAITool"] = scraped.get("PrimaryAITool") or row_dict.get("PrimaryAITool")
                        row_dict["SampleContentURL"] = scraped.get("SampleContentURL") or row_dict.get("SampleContentURL")
                        row_dict["AIGCVerdict"] = scraped.get("AIGCVerdict")
                        row_dict["Notes"] = scraped.get("Notes")
                        row_dict["FeedURL"] = scraped.get("FeedURL")
                        row_dict["ContactSourceURL"] = scraped.get("ContactSourceURL")
                        row_dict["EvidenceJSON"] = scraped.get("EvidenceJSON")

                    all_updated.append(row_dict)
                    time.sleep(2)

            browser.close()

    # --- Non-browser scrapers (yt-dlp, API) ---
    for plat in sorted(groups.keys()):
        if plat in browser_plats:
            continue
        rows = groups[plat]
        scraper_fn = PLATFORM_SCRAPERS[plat][1]
        print(f"\n--- Scraping {plat.upper()} ({len(rows)} profiles) ---")

        for i, (idx, row) in enumerate(rows, 1):
            url = str(row[url_col]).strip()
            print(f"[{i}/{len(rows)}] {plat}: {url}")

            scraped = scraper_fn(url)
            row_dict = row.to_dict()
            row_dict["Platform"] = plat.title()

            if scraped:
                row_dict["Name/Handle"] = scraped.get("Handle") or row_dict.get("Name/Handle")
                row_dict["FollowerCount"] = scraped.get("FollowerCount") or row_dict.get("FollowerCount")
                if row_dict.get("Email") in [None, "", "not exposed"]:
                    row_dict["Email"] = scraped.get("Email")
                row_dict["LastScrapedAt"] = scraped.get("LastScrapedAt")
                row_dict["Region"] = scraped.get("Region") or row_dict.get("Region")
                row_dict["Language"] = scraped.get("Language") or row_dict.get("Language")
                row_dict["PrimaryAITool"] = scraped.get("PrimaryAITool") or row_dict.get("PrimaryAITool")
                row_dict["SampleContentURL"] = scraped.get("SampleContentURL") or row_dict.get("SampleContentURL")
                row_dict["AIGCVerdict"] = scraped.get("AIGCVerdict")
                row_dict["Notes"] = scraped.get("Notes")
                row_dict["FeedURL"] = scraped.get("FeedURL")
                row_dict["ContactSourceURL"] = scraped.get("ContactSourceURL")
                row_dict["EvidenceJSON"] = scraped.get("EvidenceJSON")

            all_updated.append(row_dict)
            time.sleep(1)

    save_results(all_updated, OUTPUT_CSV_FILE)


if __name__ == "__main__":
    main()
