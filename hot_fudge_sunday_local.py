import os
import re
from pathlib import Path
from datetime import datetime, timedelta
import frontmatter
from dotenv import load_dotenv

def find_post_for_date(directory: Path, target_date: str) -> Path | None:
    """
    Finds a markdown file in a directory that matches the target date in its frontmatter.
    """
    if not directory.is_dir():
        return None
    
    # Use glob to find potential files, making it more efficient
    for md_file in directory.glob(f"*{target_date}*.md"):
        try:
            post = frontmatter.load(md_file)
            post_date = post.get('date')
            if post_date:
                if isinstance(post_date, str):
                    post_date = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                
                if post_date.strftime('%Y-%m-%d') == target_date:
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

    # --- 1. Load Environment Variables ---
    load_dotenv()
    SYNC_PATH_STR = os.getenv("SYNC_PATH")

    if not SYNC_PATH_STR:
        print("\nERROR: SYNC_PATH not found in your .env file.")
        return

    SYNC_PATH = Path(SYNC_PATH_STR).expanduser()
    if not SYNC_PATH.is_dir():
        print(f"\nERROR: SYNC_PATH '{SYNC_PATH_STR}' is not a valid directory.")
        return

    # --- 2. Check Day and Local Files ---
    today = datetime.now()
    if today.weekday() not in [5, 6]:  # 5 = Saturday, 6 = Sunday
        print("This script is designed to be run on a Saturday or Sunday.")
        return

    start_of_week = today - timedelta(days=today.weekday())

    print("\n > Checking if all weekly posts are synced locally...")
    all_synced = True
    daily_files_to_process = []
    for i in range(6):  # Monday to Saturday
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

    # --- 3. Compile Weekly Content ---
    digest_content_parts = []
    print("\n > Fetching posts from the local SYNC_PATH...")
    for md_file in daily_files_to_process:
        try:
            post = frontmatter.load(md_file)
            subject = post.get('title', md_file.stem)
            body_content = post.content.lstrip()
            
            digest_content_parts.append(f"### {subject}\n{body_content}")
            print(f"  - Added post: '{subject}'")
        except Exception as e:
            print(f"  - WARNING: Could not process file {md_file.name}: {e}")

    digest_content = "\n\n---\n\n".join(digest_content_parts)

    if not digest_content_parts:
        digest_content = "No posts from the past week."

    # --- 4. Fetch #OpenToWork Section from Previous Sunday's Local File ---
    print("\n > Fetching #OpenToWork Weekly section from the previous local Sunday digest...")
    previous_sunday_date = start_of_week - timedelta(days=1)
    previous_sunday_str = previous_sunday_date.strftime('%Y-%m-%d')
    sunday_dir = SYNC_PATH / "sunday"
    
    open_to_work_section = ""
    found_sunday_file = find_post_for_date(sunday_dir, previous_sunday_str)

    if found_sunday_file:
        try:
            sunday_content = found_sunday_file.read_text(encoding='utf-8')
            # *** THE FIX IS HERE ***
            # This regex now accepts one or two '#' characters before the heading.
            parts = re.split(r'#+\s*#OpenToWork Weekly', sunday_content, flags=re.IGNORECASE)
            if len(parts) > 1:
                # Standardize on H2 for the new file
                open_to_work_section = "## #OpenToWork Weekly\n" + parts[1].strip()
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

    # --- 5. Assemble and Save the New Digest File ---
    sunday_date = today if today.weekday() == 6 else today + timedelta(days=1)
    new_subject = f"🌶️ Hot Fudge Sunday for {sunday_date.strftime('%Y-%m-%d')}"
    slug = f"hot-fudge-sunday-for-{sunday_date.strftime('%Y-%m-%d')}"

    editor_mode_comment = ""
    
    body_lines = [
        "## Last Week",
        "A look at the week behind...",
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
    
    frontmatter_content = f"""---
title: "{new_subject}"
permalink: "/archive/{slug}/"
description: "Your weekly digest of Hot Fudge Daily."
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