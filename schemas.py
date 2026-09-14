"""Tool schemas — what the LLM sees for each tool."""

CREATOR_SCRAPE = {
    "name": "creator_scrape",
    "description": (
        "Scrape one public creator profile URL to extract information such as "
        "name/handle, follower count, email, location, language, AI tools used, "
        "and content samples. Supports TikTok, Instagram, Facebook, LinkedIn, "
        "Reddit, Threads, YouTube, Vimeo, and Civitai. "
        "Use this when the user provides a specific creator profile URL "
        "and asks to scrape, extract, or refresh that creator's data. "
        "Only operates on publicly available profiles. "
        "Returns structured data but does NOT automatically merge into the CRM."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Public creator profile URL (e.g., https://www.tiktok.com/@username)",
            },
        },
        "required": ["url"],
    },
}

CREATOR_BATCH_SCRAPE = {
    "name": "creator_batch_scrape",
    "description": (
        "Run the batch scraping pipeline to process multiple creator profiles. "
        "Sources creators from the Master CRM (default) or an optional input CSV. "
        "Always creates a backup before modifying the CRM. "
        "Can filter by platform and limit the number of profiles to process. "
        "Use this when the user asks to scrape all profiles for a platform, "
        "refresh creator data, run the scraper on multiple creators at once, "
        "or rescrape existing creators from the Master CRM."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": (
                    "Source of creators: 'crm' (Master CRM, default) or 'input' (legacy input CSV). "
                    "The Master CRM is the single source of truth."
                ),
            },
            "input_file": {
                "type": "string",
                "description": (
                    "Path to input CSV file (only used with source='input'). "
                    "Resolved relative to the project root. "
                    "For normal workflow, use source='crm' instead."
                ),
            },
            "platform": {
                "type": "string",
                "description": (
                    "Optional platform to filter (tiktok, instagram, facebook, "
                    "linkedin, reddit, threads, youtube, vimeo, civitai). "
                    "If omitted, processes all platforms."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Optional maximum number of profiles to process.",
            },
        },
    },
}

CREATOR_VALIDATE = {
    "name": "creator_validate",
    "description": (
        "Run the data quality validation workflow on the Master CRM. "
        "Checks for duplicates, malformed records, schema compliance, "
        "and data integrity issues. "
        "Use this when the user asks to validate, audit, or check the "
        "quality of the creator research data."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": (
                    "Optional path to a specific CSV to validate. "
                    "Defaults to the Master CRM file."
                ),
            },
        },
    },
}
