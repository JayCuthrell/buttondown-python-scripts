import feedparser
from markdownify import markdownify as md
from datetime import date
import re

def slugify(text):
    """
    Converts a string into a URL-friendly slug.
    Example: "A new format" -> "a-new-format"
    """
    # Lowercase, remove non-alphanumeric chars (except spaces), replace spaces with dashes
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text).strip('-')
    return text

def clean_yaml_string(text):
    """
    Escapes double quotes to ensure valid YAML.
    """
    if text:
        return text.replace('"', '\\"')
    return ""

def gather_and_convert(feed_url):
    today = date.today()
    
    # We will suppress the "Checking feed..." messages to keep output purely content
    # unless you are debugging.
    # print(f"Checking feed for: {today}...") 
    
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        # --- Date Logic ---
        entry_time = entry.get('published_parsed') or entry.get('updated_parsed')
        if not entry_time:
            continue
            
        entry_date = date(entry_time.tm_year, entry_time.tm_mon, entry_time.tm_mday)

        # --- Filter by Date ---
        if entry_date == today:
            
            # --- Check for Content ---
            if 'content' in entry:
                
                # --- Prepare Data for Frontmatter ---
                # 1. Title
                raw_title = entry.get('title', 'Untitled')
                clean_title = clean_yaml_string(raw_title)
                
                # 2. Slug (for Permalink)
                slug = slugify(raw_title)
                
                # 3. Description
                # GTS feeds put a summary in the 'description' tag
                raw_desc = entry.get('description', '')
                clean_desc = clean_yaml_string(raw_desc)
                
                # 4. Content
                raw_html = entry.content[0].value
                markdown_content = md(raw_html, heading_style="ATX")

                # --- OUTPUT FORMAT ---
                print("---")
                print(f'title: "{clean_title}"')
                print(f'permalink: "/archive/{slug}"')
                print(f'description: "{clean_desc}"')
                print(f'date: {today}')
                print("---")
                print("")
                print(markdown_content)
                print("") # Empty line at the very end to separate from next entry if any

if __name__ == "__main__":
    rss_url = "https://cuthrell.com/@jay/feed.rss"
    gather_and_convert(rss_url)
