import os
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import frontmatter
from dotenv import load_dotenv
import feedparser
import requests

def get_last_week_updates(start_of_week: datetime) -> str:
    """
    Fetches and formats updates from specified RSS feeds. It ensures at least
    four items are returned if available within the last two weeks.
    """
    urls = [
        "https://www.brighttalk.com/service/channel/v2/channel/20887/feed/rss",
        "https://www.nexustek.com/insights/rss.xml"
    ]
    all_entries = []
    print("\n > Fetching updates for the 'Last Week' section...")

    two_weeks_ago = start_of_week - timedelta(days=7)

    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                print(f"  - WARNING: Feed at {url} may be ill-formed. {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if published_date.date() >= two_weeks_ago.date():
                        author = entry.get('brighttalk_presenter', entry.get('author', 'NexusTek'))
                        author = re.sub(r' &amp;.*|\|.*', '', author).strip()
                        title = entry.title
                        link = entry.link
                        all_entries.append({'date': published_date, 'author': author, 'title': title, 'link': link})
                        # *** ADDED: Console log for discovered entries ***
                        print(f"  - Discovered entry: '{title}' from {published_date.strftime('%Y-%m-%d')}")

        except Exception as e:
            print(f"  - WARNING: Could not fetch or process URL {url}: {e}")
            continue
            
    all_entries.sort(key=lambda x: x['date'], reverse=True)

    updates_current_week = [e for e in all_entries if e['date'].date() >= start_of_week.date()]
    
    final_updates = updates_current_week
    # *** UPDATED: Logic now looks for 4 items instead of 2 ***
    if len(final_updates) < 4:
        updates_previous_week = [e for e in all_entries if e['date'].date() < start_of_week.date()]
        needed = 4 - len(final_updates)
        final_updates.extend(updates_previous_week[:needed])

    if final_updates:
        print(f"  - Found {len(final_updates)} item(s) for the list.")
        # *** UPDATED: Formatting with newline and asterisks ***
        update_strings = [f"* [{u['author']}]({u['link']}) published [{u['title']}]({u['link']})" for u in final_updates]
        return "\n" + "\n".join(update_strings)
    else:
        print("  - No new items found in the last two weeks.")
        return "A look at the week behind..."


def find_post_for_date(directory: Path, target_date: str) -> Path | None:
    """
    Finds a markdown file in a directory that matches the target date in its frontmatter.
    """
    if not directory.is_dir():
        return None
    
    for md_file in directory.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            post_date = post.get('date')
            if post_date:
                if isinstance(post_date, (datetime, date)):
                    post_date_obj = post_date
                else: 
                    post_date_obj = datetime.fromisoformat(str(post_date).replace('Z', '+00:00'))
                
                if post_date_obj.strftime('%Y-%m-%d') == target_date:
                    return md_file
        except Exception as e:
            print(f"  - WARNING: Could not read or parse frontmatter for {md_file.name}: {e}")
            continue
    return None

def create_local_sunday_digest():
    """
    Compiles the past week's local posts into a new Sunday digest Markdown file.
    """
    print("\n--- Mode: Create Local Hot Fudge Sunday Digest ---")

    load_dotenv()
    SYNC_PATH_STR = os.getenv("SYNC_PATH")

    if not SYNC_PATH_STR:
        print("\nERROR: SYNC_PATH not found in your .env file.")
        return

    SYNC_PATH = Path(SYNC_PATH_STR).expanduser()
    if not SYNC_PATH.is_dir():
        print(f"\nERROR: SYNC_PATH '{SYNC_PATH_STR}' is not a valid directory.")
        return

    today = datetime.now()
    if today.weekday() not in [5, 6]:
        print("This script is designed to be run on a Saturday or Sunday.")
        return

    start_of_week = today - timedelta(days=today.weekday())

    print("\n > Checking if all weekly posts are synced locally...")
    all_synced = True
    daily_files_to_process = []
    for i in range(6):
        day_to_check = start_of_week + timedelta(days=i)
        day_name = day_to_check.strftime('%A').lower()
        target_date_str = day_to_check.strftime('%Y-%m-%d')
        day_directory = SYNC_PATH / day_name

        found_file = find_post_for_date(day_directory, target_date_str)

        if not found_file:
            print(f"  - MISSING: No file found in '{day_directory}' for {target_date_str}.")
            all_synced = False
        else:
            daily_files_to_process.append(found_file)
    
    if not all_synced:
        print("\nCannot create digest. Not all posts for the week have been synced locally.")
        return
    else:
        print(" > All weekly posts are synced. Proceeding with digest creation.")

    digest_content_parts = []
    print("\n > Fetching posts from the local SYNC_PATH...")
    for md_file in daily_files_to_process:
        try:
            post = frontmatter.load(md_file)
            subject = post.get('title', md_file.stem)
            body_content = post.content.lstrip()
            
            body_content = re.sub(r'^###\s', '#### ', body_content, flags=re.MULTILINE)

            digest_content_parts.append(f"### {subject}\n{body_content}")
            print(f"  - Added post: '{subject}'")
        except Exception as e:
            print(f"  - WARNING: Could not process file {md_file.name}: {e}")

    digest_content = "\n\n---\n\n".join(digest_content_parts)

    if not digest_content_parts:
        digest_content = "No posts from the past week."

    print("\n > Fetching #OpenToWork Weekly section from the previous local Sunday digest...")
    previous_sunday_date = start_of_week - timedelta(days=1)
    previous_sunday_str = previous_sunday_date.strftime('%Y-%m-%d')
    sunday_dir = SYNC_PATH / "sunday"
    
    open_to_work_section = ""
    found_sunday_file = find_post_for_date(sunday_dir, previous_sunday_str)

    if found_sunday_file:
        try:
            sunday_content = found_sunday_file.read_text(encoding='utf-8')
            match = re.search(r'(#+\s*#OpenToWork Weekly.*)', sunday_content, re.DOTALL | re.IGNORECASE)
            
            if match:
                open_to_work_section = re.sub(r'^#+\s*', '## ', match.group(1).strip())
                print("  - Successfully extracted #OpenToWork Weekly section.")
            else:
                open_to_work_section = "## #OpenToWork Weekly\n\n_Could not find section in previous digest._"
                print("  - WARNING: Could not find '#OpenToWork Weekly' heading in the previous digest.")
        except Exception as e:
            print(f"  - ERROR reading previous Sunday file: {e}")
            open_to_work_section = "## #OpenToWork Weekly\n\n_Placeholder - Error reading previous digest._"
    else:
        print(f"  - WARNING: Could not find a local digest file for {previous_sunday_str}.")
        open_to_work_section = "## #OpenToWork Weekly\n\n_Placeholder - Previous digest not found._"

    sunday_date = today if today.weekday() == 6 else today + timedelta(days=1)
    new_subject = f"🌶️ Hot Fudge Sunday for {sunday_date.strftime('%Y-%m-%d')}"
    slug = f"hot-fudge-sunday-for-{sunday_date.strftime('%Y-%m-%d')}"

    editor_mode_comment = ""
    
    last_week_content = get_last_week_updates(start_of_week)

    body_lines = [
        "## Last Week",
        last_week_content,
        "",
        "## This Week",
        "A look at the week ahead...",
        "",
        "---",
        "",
        "## Hot Fudge Daily Digest",
        "",
        "---",
        digest_content,
        "",
        "---",
        open_to_work_section
    ]
    new_body = "\n".join(body_lines)
    
    week_start_str = start_of_week.strftime('%m-%d-%Y')
    week_end_str = (start_of_week + timedelta(days=5)).strftime('%m-%d-%Y')
    description = f"Hot Fudge Daily digest for the week of {week_start_str} to {week_end_str}."

    frontmatter_content = f"""---
title: "{new_subject}"
permalink: "/archive/{slug}/"
description: "{description}"
date: {sunday_date.strftime('%Y-%m-%d')}
---

"""
    
    final_content = f"{frontmatter_content}{editor_mode_comment}\n\n{new_body}"
    
    output_dir = SYNC_PATH / "sunday"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{slug}.md"
    
    try:
        output_file.write_text(final_content, encoding='utf-8')
        print(f"\n✅ Successfully saved local digest to: {output_file}")
    except Exception as e:
        print(f"  > ERROR: Could not write local digest file. {e}")


if __name__ == "__main__":
    create_local_sunday_digest()