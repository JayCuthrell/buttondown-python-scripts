import os
import re
from pathlib import Path
from datetime import datetime, timedelta, date
import frontmatter
from dotenv import load_dotenv

def get_fudge_factor_posts(directory: Path, start_date: date, end_date: date):
    """
    Scans for markdown files with 'Fudge Factor' tag within a date range.
    """
    found_posts = []
    print(f" > Searching for 'Fudge Factor' posts from {start_date} to {end_date}...")

    file_count = 0
    # Recursively find all markdown files
    for md_file in directory.rglob("*.md"):
        # Skip node_modules or hidden folders
        if "node_modules" in md_file.parts or md_file.name.startswith("."):
            continue
            
        file_count += 1
        try:
            post = frontmatter.load(md_file)
            post_date = post.get('date')
            raw_tags = post.get('tags', [])
            
            if raw_tags is None: raw_tags = []
            # Normalize tags to lower case for reliable checking
            tags = [t.lower() for t in (raw_tags if isinstance(raw_tags, list) else [raw_tags])]

            # Filter logic: Check tag and date range
            if 'fudge factor' in tags and post_date:
                # Convert post_date to date object
                if isinstance(post_date, datetime):
                    current_post_date = post_date.date()
                elif isinstance(post_date, date):
                    current_post_date = post_date
                else:
                    # Attempt to parse string dates
                    current_post_date = datetime.fromisoformat(str(post_date).replace('Z', '+00:00')).date()
                
                if start_date <= current_post_date <= end_date:
                    found_posts.append((current_post_date, post))
                    print(f"  ✅ MATCH: '{post.get('title')}' published on {current_post_date}")
        except Exception:
            continue
            
    print(f"ℹ️ Total markdown files scanned: {file_count}")
    # Sort posts chronologically by date
    found_posts.sort(key=lambda x: x[0])
    return found_posts

def create_fudge_factor_digest():
    """
    Compiles the Fudge Factor digest and provides a terminal preview.
    """
    load_dotenv()
    SYNC_PATH_STR = os.getenv("SYNC_PATH")
    if not SYNC_PATH_STR:
        print("\n❌ ERROR: SYNC_PATH not found in your .env file.")
        return

    SYNC_PATH = Path(SYNC_PATH_STR).expanduser()
    
    today = datetime.now().date()
    # Calculate range for current week (Monday to Saturday)
    start_of_week = today - timedelta(days=today.weekday()) 
    end_of_week = today

    # Fetch matching posts
    daily_posts = get_fudge_factor_posts(SYNC_PATH, start_of_week, end_of_week)

    if not daily_posts:
        print("\n🤷 No posts found. Ensure files have 'tags: [\"Fudge Factor\"]' in the YAML.")
        return

    # Assemble the content parts
    digest_parts = []
    for post_date, post in daily_posts:
        subject = post.get('title', 'Untitled')
        body = post.content.strip()
        # Convert any H1/H2/H3 in the post to H4 for the digest structure
        body = re.sub(r'^#+\s', '#### ', body, flags=re.MULTILINE)
        digest_parts.append(f"### {subject}\n*Published on {post_date}*\n\n{body}")

    digest_content = "\n\n---\n\n".join(digest_parts)

    # Sunday file metadata setup
    sunday_date = today + timedelta(days=(6 - datetime.now().weekday()))
    date_str = sunday_date.strftime('%Y-%m-%d')
    
    # Required descriptive slug format
    permalink_slug = f"fudge-factor-digest-for-{date_str}"
    
    # Frontmatter template following specific tag and permalink requirements
    frontmatter_block = f"""---
title: "Fudge Factor Weekly: {sunday_date.strftime('%B %d, %Y')}"
description: "Weekly digest of Fudge Factor insights for the week of {start_of_week}."
date: {date_str}
tags: ["Fudge Factor"]
permalink: "/archive/{permalink_slug}/"
---
"""

    final_output = f"{frontmatter_block}\n\n## The Week in Review\n\n{digest_content}\n\n---\n*This digest was automatically generated.*"

    # PREVIEW MODE
    print("\n" + "="*60)
    print(f"--- PREVIEW FOR: src/posts/fudge-factor/{date_str}.md ---")
    print("="*60 + "\n")
    print(final_output)
    print("\n" + "="*60)

    # FINAL CREATION PROMPT
    save_choice = input(f"\nSave to src/posts/fudge-factor/{date_str}.md? (y/N): ").lower()
    if save_choice == 'y':
        output_dir = SYNC_PATH / "src" / "posts" / "fudge-factor"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{date_str}.md"
        
        try:
            output_file.write_text(final_output, encoding='utf-8')
            print(f"\n✅ File successfully saved to: {output_file}")
        except Exception as e:
            print(f"  > ERROR: Could not write file. {e}")
    else:
        print("\nSave cancelled. Preview complete.")

if __name__ == "__main__":
    create_fudge_factor_digest()