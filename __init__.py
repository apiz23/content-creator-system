"""Content Creator System plugin — registration.

BACKUP POLICY: Every discovery/scrape operation creates a 
timestamped backup BEFORE modifying the Master CRM.
"""

import sys
from pathlib import Path

# Ensure the project root is in the package path for tool imports
_PLUGIN_ROOT = Path(__file__).resolve().parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

try:
    from . import schemas, tools
except ImportError:
    import schemas
    import tools

# CRM path for discovery dedup
_CRM_PATH = _PLUGIN_ROOT / "data" / "Creator-Intel-CRM-List.csv"


def _handle_creator_discover(ctx, raw_args: str) -> str:
    """
    Slash command handler for /creator-discover.

    Parses arguments:
        /creator-discover platform:tiktok keywords:"AI video" count=10

    BACKUP FIRST: Creates a backup before scraping.
    Uses native web_search to find creators, deduplicates against Master CRM, and scrapes them.
    """
    import re
    import shutil
    import json
    from datetime import datetime

    # Parse arguments
    args = {}
    for match in re.finditer(r'(\w+):"([^"]*)"', raw_args):
        args[match.group(1)] = match.group(2)
    for match in re.finditer(r'(\w+):(\S+)', raw_args):
        if match.group(1) not in args:
            args[match.group(1)] = match.group(2)

    platform = args.get("platform", "tiktok").lower()
    keywords = args.get("keywords", "AI creator")
    count = int(args.get("count", "10"))

    # STEP 1: Backup CRM before any scraping
    backup_path = None
    if _CRM_PATH.exists():
        try:
            backup_dir = _PLUGIN_ROOT / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"Creator-Intel-CRM-List_{timestamp}.csv"
            backup_path = backup_dir / backup_name
            shutil.copy2(_CRM_PATH, backup_path)
        except Exception as e:
            return f"Backup failed, aborting discovery: {e}"

    # STEP 2: Search for candidates
    sys.path.insert(0, str(_PLUGIN_ROOT / "code" / "scraper"))
    from common import (
        PROJECT_ROOT, detect_platform_from_url,
    )

    # Use native web_search to find creators
    search_result = ctx.dispatch_tool("web_search", {
        "query": f"{keywords} {platform} creator profile",
        "limit": count * 2,
    })

    # Extract URLs from search result
    urls = []
    for line in search_result.split("\n"):
        line = line.strip()
        if line.startswith("http"):
            detected = detect_platform_from_url(line)
            if detected and detected.lower() == platform.lower():
                urls.append(line)

    # STEP 3: Deduplicate against Master CRM only (not input_channels.csv)
    import pandas as pd
    
    existing = set()
    if _CRM_PATH.exists():
        try:
            df = pd.read_csv(_CRM_PATH, dtype=str)
            for url in df.get("ProfileURL", []):
                if pd.notna(url):
                    existing.add(str(url).strip().lower().rstrip("/"))
        except Exception:
            pass

    new_urls = [u for u in urls if u.strip().lower().rstrip("/") not in existing]
    new_urls = new_urls[:count]

    if not new_urls:
        return f"No new creators found (all {len(urls)} results already exist in Master CRM)"

    # STEP 4: Scrape each new URL using the plugin tool
    scraped = 0
    for url in new_urls:
        try:
            result_json = ctx.dispatch_tool("creator_scrape", {"url": url})
            result = json.loads(result_json) if isinstance(result_json, str) else result_json
            if result.get("success"):
                scraped += 1
        except Exception:
            pass

    backup_msg = f"\n  Backup: {backup_path}" if backup_path else ""
    return (
        f"Discovery complete:{backup_msg}\n"
        f"  Platform: {platform}\n"
        f"  Keywords: {keywords}\n"
        f"  Found: {len(urls)} candidates\n"
        f"  New: {len(new_urls)}\n"
        f"  Scraped: {scraped}"
    )


def register(ctx):
    """Register all tools for the Content Creator System plugin."""
    ctx.register_tool(
        name="creator_scrape",
        toolset="creator",
        schema=schemas.CREATOR_SCRAPE,
        handler=tools.creator_scrape,
    )

    ctx.register_tool(
        name="creator_batch_scrape",
        toolset="creator",
        schema=schemas.CREATOR_BATCH_SCRAPE,
        handler=tools.creator_batch_scrape,
    )

    ctx.register_tool(
        name="creator_validate",
        toolset="creator",
        schema=schemas.CREATOR_VALIDATE,
        handler=tools.creator_validate,
    )

    # Register slash command for discovery using native web_search
    ctx.register_command(
        "creator-discover",
        lambda raw: _handle_creator_discover(ctx, raw),
        description="Discover creators via web search, deduplicate against Master CRM, then scrape. Usage: /creator-discover platform:tiktok keywords:\"AI video\" count=10",
    )
