import pandas as pd
import requests
import re
import time
import json
from datetime import datetime

# Load CRM
crm_path = 'data/Creator-Intel-CRM-List.csv'
df = pd.read_csv(crm_path)

# Filter Civitai entries missing followers
civ_mask = df['Platform'].str.lower() == 'civitai'
empty_mask = df['FollowerCount'].isna() | (df['FollowerCount'] == '') | (df['FollowerCount'] == 'N/A')
targets = df[civ_mask & empty_mask]

print(f"Total Civitai: {len(df[civ_mask])}")
print(f"Missing followers: {len(targets)}")

batch_size = 5
pause_sec = 180  # 3 minutes
total = len(targets)
processed = 0
succeeded = 0
failed = 0

for batch_start in range(0, total, batch_size):
    batch = targets.iloc[batch_start:batch_start + batch_size]
    batch_num = batch_start // batch_size + 1
    total_batches = (total + batch_size - 1) // batch_size
    
    print(f"\n=== Batch {batch_num}/{total_batches} ===")
    
    for _, row in batch.iterrows():
        idx = row.name
        url = str(row['ProfileURL'])
        name = row['Name/Handle']
        
        # Extract username from URL
        match = re.search(r'civitai\.com/user/([a-zA-Z0-9_\-\.]+)', url)
        if not match:
            print(f"  [SKIP] {name}: invalid URL")
            failed += 1
            continue
        
        username = match.group(1)
        profile_url = f"https://civitai.com/user/{username}"
        
        try:
            res = requests.get(profile_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if res.status_code != 200:
                print(f"  [FAIL] {name}: HTTP {res.status_code}")
                df.at[idx, 'FollowerCount'] = 'needs_manual_check'
                failed += 1
                continue
            
            # Extract followerCountAllTime
            match = re.search(r'"followerCountAllTime":(\d+)', res.text)
            if match:
                followers = int(match.group(1))
                # Format as K/M
                if followers >= 1000000:
                    fstr = f"{followers/1000000:.1f}M"
                elif followers >= 1000:
                    fstr = f"{followers/1000:.1f}K"
                else:
                    fstr = str(followers)
                
                df.at[idx, 'FollowerCount'] = fstr
                df.at[idx, 'LastScrapedAt'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                print(f"  [OK] {name}: {fstr} followers")
                succeeded += 1
            else:
                print(f"  [CHECK] {name}: follower element not found")
                df.at[idx, 'FollowerCount'] = 'needs_manual_check'
                failed += 1
        
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            df.at[idx, 'FollowerCount'] = 'needs_manual_check'
            failed += 1
        
        processed += 1
    
    # Save after each batch
    df.to_csv(crm_path, index=False)
    print(f"\nBatch {batch_num}/{total_batches} done — {processed}/{total} processed, {succeeded} ok, {failed} failed")
    
    # Pause between batches
    if batch_start + batch_size < total:
        print(f"Pausing {pause_sec}s...")
        time.sleep(pause_sec)

print(f"\n=== COMPLETE ===")
print(f"Processed: {processed}")
print(f"Succeeded: {succeeded}")
print(f"Failed: {failed}")
