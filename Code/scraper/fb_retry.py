#!/usr/bin/env python3
"""Retry scrape: R3DZ3RO and AitanaLopezAI — longer timeout, better error handling."""
import os, re, json, time, requests, csv
from datetime import datetime
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

PROFILES = [
    "https://www.facebook.com/R3DZ3RO",
    "https://www.facebook.com/AitanaLopezAI",
]

def classify_llm(bio, handle):
    try:
        res = requests.post("http://localhost:11434/api/generate",
            json={"model":"qwen3.5:latest","prompt":f"Analyze: {handle} | {bio}\nReturn JSON: {{\"Tags\":[\"Facebook\",\"AIGC\"],\"PrimaryAITool\":\"GenAI\",\"AIGCVerdict\":\"hybrid\",\"Language\":\"English\",\"Evidence\":\"scraped\"}}","format":"json","stream":False},timeout=15)
        return json.loads(res.json().get("response","{}"))
    except:
        return {"Tags":["Facebook","AIGC"],"PrimaryAITool":"GenAI","AIGCVerdict":"hybrid","Language":"English","Evidence":"fallback"}

def extract_email(text):
    if not text: return "not exposed"
    m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return m.group(0) if m else "not exposed"

def extract_handle(url):
    m = re.search(r'facebook\.com/([a-zA-Z0-9_.\-]+)', url)
    if m and m.group(1) not in ("profile.php","pages","groups","share"):
        return f"@{m.group(1)}"
    return url.split('/')[-1] or url

def clean_fb_url(url):
    if "l.facebook.com/l.php" in url:
        m = re.search(r'[?&]u=([^&]+)', url)
        return unquote(m.group(1)) if m else url
    return url

def scrape_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)  # longer wait
        handle = extract_handle(url)
        
        # Try multiple selectors for og:title
        og_t = ""
        for sel in ['meta[property="og:title"]', 'meta[name="title"]', 'title']:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    og_t = el.get_attribute("content") or el.inner_text() or ""
                    if og_t.strip(): break
            except: pass
        
        if not og_t:
            og_t = page.title() or ""
        
        # Try multiple selectors for og:description
        og_d = ""
        for sel in ['meta[property="og:description"]', 'meta[name="description"]']:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    og_d = el.get_attribute("content") or ""
                    if og_d.strip(): break
            except: pass
        
        # Fallback: body text
        if not og_d:
            try:
                bt = page.inner_text("body", timeout=10000)
                # Look for follower patterns in body
                fm = re.search(r'([\d.,]+[KkMmBb]?)\s*(?:followers|likes|pengikut)', bt, re.I)
                if fm:
                    og_d = bt[:500]
            except: pass
        
        fc = "N/A"
        if og_d:
            fm = re.search(r'([\d.,]+[KkMmBb]?)\s*(?:followers|likes|pengikut)', og_d, re.I)
            if fm: fc = fm.group(1)
        else:
            try:
                bt = page.inner_text("body", timeout=10000)
                fm2 = re.search(r'([\d.,]+[KkMmBb]?)\s*(?:followers|likes|pengikut)', bt, re.I)
                if fm2: fc = fm2.group(1)
            except: pass
        
        bio = og_d
        try:
            ie = page.locator('div[role="main"]').inner_text(timeout=5000)
            if ie and len(ie) > len(bio): bio = ie[:300]
        except: pass
        if not bio:
            try:
                bio = page.inner_text("body", timeout=5000)[:300]
            except: pass
        
        ext = ""
        try:
            for l in page.locator('a[href*="http"]').all():
                h = l.get_attribute("href") or ""
                if "l.facebook.com" in h: ext = clean_fb_url(h); break
                elif not any(d in h for d in ["facebook.com","fb.com","instagram.com"]): ext = h; break
        except: pass
        
        ai = classify_llm(bio, handle or og_t)
        email = extract_email(bio)
        ev = {"platform":"Facebook","handle":handle,"title":og_t,"bio_preview":bio[:100],"external_link":ext,"aigc_verdict":ai.get("AIGCVerdict","hybrid"),"ai_reasoning":ai.get("Evidence","scraped-retry")}
        return {"ProfileURL":url,"Name/Handle":handle or og_t,"Platform":"Facebook","FollowerCount":fc,"Email":email,"Tags":", ".join(ai.get("Tags",[])) if isinstance(ai.get("Tags"),list) else str(ai.get("Tags")),"OutreachStatus":"New","LastScrapedAt":datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),"Region":"","Language":ai.get("Language","English"),"PrimaryAITool":ai.get("PrimaryAITool"),"SampleContentURL":ext or url,"AIGCVerdict":ai.get("AIGCVerdict","hybrid"),"DiscoveredAt":"2026-09-01","Source":"Facebook Scrape (batch 3 retry)","Notes":f"Facebook retry: followers={fc}; bio_preview={bio[:60].strip() if bio else 'N/A'}","FeedURL":url,"ContactSourceURL":url if email!="not exposed" else ext,"EvidenceJSON":json.dumps(ev)}
    except Exception as e:
        print(f"[-] Error {url}: {e}")
        import traceback; traceback.print_exc()
        return None

out = "data/output/fb_batch3_retry.csv"
print(f"[+] Retrying 2 failed Facebook creators")
results = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width":1280,"height":800},
        locale="en-US")
    page = ctx.new_page()
    for i, url in enumerate(PROFILES, 1):
        print(f"[{i}/2] {url}")
        r = scrape_page(page, url)
        if r: results.append(r); print(f"      -> {r['Name/Handle']}: {r['FollowerCount']} followers, verdict={r['AIGCVerdict']}")
        else: print(f"      -> FAILED")
        time.sleep(3)
    b.close()

if results:
    cols = ["ProfileURL","Name/Handle","Platform","FollowerCount","Email","Tags","OutreachStatus","LastScrapedAt","Region","Language","PrimaryAITool","SampleContentURL","AIGCVerdict","DiscoveredAt","Source","Notes","FeedURL","ContactSourceURL","EvidenceJSON"]
    with open(out,'w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in results: w.writerow(r)
    print(f"[+] Saved {len(results)} records to {out}")
else:
    print("[!] Both retries failed")
