"""Tool handlers — thin wrappers around the existing scraper system.

BACKUP POLICY: EVERY operation that modifies the Master CRM creates a 
timestamped backup FIRST. If backup fails, the operation is ABORTED.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Resolve project root relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent

# Use the project's .venv Python if available (matches dependencies)
_PROJECT_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if _PROJECT_VENV_PYTHON.exists() and _PROJECT_VENV_PYTHON.is_file():
    _PYTHON = str(_PROJECT_VENV_PYTHON)
else:
    _PYTHON = sys.executable

# CRM path
_CRM_PATH = PROJECT_ROOT / "data" / "Creator-Intel-CRM-List.csv"
_BACKUP_DIR = PROJECT_ROOT / "data" / "backups"


def _backup_crm():
    """Create timestamped backup of Master CRM. Returns path or raises RuntimeError."""
    import shutil
    
    if not _CRM_PATH.exists():
        raise RuntimeError(f"CRM file not found: {_CRM_PATH}")
    
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"Creator-Intel-CRM-List_{timestamp}.csv"
    backup_path = _BACKUP_DIR / backup_name
    
    # Ensure unique filename
    counter = 1
    while backup_path.exists():
        backup_name = f"Creator-Intel-CRM-List_{timestamp}_{counter}.csv"
        backup_path = _BACKUP_DIR / backup_name
        counter += 1
    
    try:
        shutil.copy2(_CRM_PATH, backup_path)
    except Exception as e:
        raise RuntimeError(f"Failed to create CRM backup: {e}")
    
    if not backup_path.exists():
        raise RuntimeError(f"Backup file not created: {backup_path}")
    
    return str(backup_path)


def creator_scrape(args: dict, **kwargs) -> str:
    """Scrape one public creator profile URL.
    
    BACKUP FIRST: Creates a timestamped backup before scraping.
    If backup fails, the operation is aborted.
    """
    url = args.get("url", "").strip()
    if not url:
        return json.dumps({"success": False, "error": "No URL provided"})
    
    # STEP 1: Backup CRM before any operation
    try:
        backup_path = _backup_crm()
    except RuntimeError as e:
        return json.dumps({
            "success": False,
            "error": f"Backup failed, aborting: {e}",
        })
    
    # STEP 2: Scrape
    try:
        result = subprocess.run(
            [
                _PYTHON,
                str(PROJECT_ROOT / "code" / "scraper" / "run.py"),
                "--url",
                url,
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "url": url,
                "backup_path": backup_path,
                "error": error or "Scraper returned non-zero exit code",
            })

        # Parse the output to extract key information
        lines = output.split("\n")
        platform = None
        records_processed = 0
        records_successful = 0
        for line in lines:
            if "Detected platform:" in line:
                platform = line.split(":")[-1].strip()
            if "Processed:" in line:
                parts = line.split("|")
                for part in parts:
                    part_stripped = part.strip()
                    if "Processed:" in part_stripped:
                        val = part_stripped.split(":")[-1].strip().split()[0]
                        records_processed = int(val)
                    elif "Successful:" in part_stripped:
                        records_successful = int(part_stripped.split(":")[-1].strip())

        return json.dumps({
            "success": True,
            "url": url,
            "platform": platform,
            "records_processed": records_processed,
            "records_successful": records_successful,
            "backup_path": backup_path,
            "output": output,
            "errors": error if error else None,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "url": url,
            "backup_path": backup_path,
            "error": "Scraper timed out (120s)",
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "url": url,
            "backup_path": backup_path,
            "error": str(e),
        })


def creator_batch_scrape(args: dict, **kwargs) -> str:
    """Run the batch scraping pipeline.
    
    BACKUP FIRST: Creates a timestamped backup before scraping.
    If backup fails, the operation is aborted.
    
    Sources creators from the Master CRM (default) or an optional input CSV.
    """
    source = args.get("source", "crm")  # "crm" or "input"
    platform = args.get("platform")
    limit = args.get("limit")
    input_file = args.get("input_file")
    backup_path = None

    # STEP 1: Backup CRM before any operation (skip for legacy input mode)
    if source != "input":
        try:
            backup_path = _backup_crm()
        except RuntimeError as e:
            return json.dumps({
                "success": False,
                "error": f"Backup failed, aborting: {e}",
            })

    # STEP 2: Build the command
    cmd = [
        _PYTHON,
        str(PROJECT_ROOT / "code" / "scraper" / "run.py"),
    ]

    if source == "input" and input_file:
        # Legacy: use input CSV
        input_path = Path(input_file)
        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path
        input_path = input_path.resolve()
        try:
            input_path.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return json.dumps({
                "success": False,
                "error": f"input_file must be within project directory: {input_file}",
            })
        if not input_path.exists():
            return json.dumps({
                "success": False,
                "error": f"input_file not found: {input_path}",
            })
        cmd.extend(["--input", str(input_path)])

    if platform:
        cmd.extend(["--platform", platform])
    if limit is not None:
        cmd.extend(["--limit", str(limit)])

    # STEP 3: Run scraper
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=3600,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "source": source,
                "platform": platform,
                "backup_path": backup_path,
                "error": error or "Batch scraper returned non-zero exit code",
            })

        # Extract summary from output
        lines = output.split("\n")
        processed = 0
        successful = 0
        failed = 0
        for line in lines:
            if "Processed:" in line:
                parts = line.split("|")
                for part in parts:
                    part_stripped = part.strip()
                    if "Processed:" in part_stripped:
                        val = part_stripped.split(":")[-1].strip().split()[0]
                        processed = int(val)
                    elif "Successful:" in part_stripped:
                        successful = int(part_stripped.split(":")[-1].strip())
                    elif "Failed:" in part_stripped:
                        failed = int(part_stripped.split(":")[-1].strip())

        return json.dumps({
            "success": True,
            "source": source,
            "platform": platform,
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "backup_path": backup_path,
            "output": output,
            "errors": error if error else None,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "source": source,
            "platform": platform,
            "backup_path": backup_path,
            "error": "Batch scraper timed out (1 hour)",
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "source": source,
            "platform": platform,
            "backup_path": backup_path,
            "error": str(e),
        })


def creator_validate(args: dict, **kwargs) -> str:
    """Run data quality validation on the creator CRM.
    
    READ-ONLY: Does not modify CRM, no backup needed.
    """
    import pandas as pd

    input_file = args.get("input_file")
    if input_file:
        crm_path = Path(input_file)
    else:
        crm_path = _CRM_PATH

    if not crm_path.exists():
        return json.dumps({
            "success": False,
            "error": f"CRM file not found: {crm_path}",
        })

    try:
        df = pd.read_csv(crm_path, dtype=str)
        total_rows = len(df)

        # Check for duplicates by ProfileURL
        duplicates = df[df.duplicated(subset=["ProfileURL"], keep=False)]
        duplicate_count = len(duplicates)

        # Check for missing required fields
        required_fields = ["ProfileURL", "Name/Handle", "Platform"]
        missing_fields = {}
        for field in required_fields:
            if field in df.columns:
                missing = df[field].isna().sum()
                if missing > 0:
                    missing_fields[field] = int(missing)
            else:
                missing_fields[field] = "column missing"

        # Check for schema compliance
        expected_columns = [
            "ProfileURL", "Name/Handle", "Platform", "FollowerCount", "Email",
            "Tags", "OutreachStatus", "LastScrapedAt", "Region", "Language",
            "PrimaryAITool", "SampleContentURL", "AIGCVerdict", "DiscoveredAt",
            "Source", "Notes", "FeedURL", "ContactSourceURL", "EvidenceJSON"
        ]
        missing_columns = [c for c in expected_columns if c not in df.columns]

        # Check for empty rows (all NaN)
        empty_rows = df.isna().all(axis=1).sum()

        issues = []
        if duplicate_count > 0:
            issues.append(f"{duplicate_count} duplicate ProfileURL rows")
        if missing_columns:
            issues.append(f"Missing columns: {', '.join(missing_columns)}")
        if empty_rows > 0:
            issues.append(f"{empty_rows} completely empty rows")
        for field, count in missing_fields.items():
            issues.append(f"{count} rows missing {field}")

        return json.dumps({
            "success": True,
            "total_rows": total_rows,
            "duplicate_profile_urls": duplicate_count,
            "missing_fields": missing_fields,
            "missing_columns": missing_columns,
            "empty_rows": int(empty_rows),
            "issues": issues,
            "valid": len(issues) == 0,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })
