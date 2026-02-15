import os
import sys
import re
import uuid
import yaml
import warnings
import difflib
from bs4 import BeautifulSoup, NavigableString, MarkupResemblesLocatorWarning

# --- Configuration ---
DEFAULT_PATH = os.path.expanduser("~/github/fudge-org-eleventy-excellent-4.3.3/src/posts")
DRY_RUN = False

# --- Silence Warnings ---
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# --- Global Storage ---
code_block_map = {}

# --- 1. Frontmatter Handling ---

def extract_frontmatter(text):
    match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    if match:
        return match.group(0), text[len(match.group(0)):]
    return "", text

def validate_frontmatter(frontmatter_raw):
    if not frontmatter_raw: return True
    try:
        yaml_content = frontmatter_raw.strip().strip('-')
        yaml.safe_load(yaml_content)
        return True
    except yaml.YAMLError:
        return False

# --- 2. Protection Logic ---

def protect_code_blocks_and_liquid(text):
    """
    Protects Code Blocks AND Liquid/Nunjucks tags {{ ... }} {% ... %}
    so they are not touched by the HTML parser.
    """
    def replacer(match):
        placeholder = f"__CODE_BLOCK_{uuid.uuid4().hex}__"
        code_block_map[placeholder] = match.group(0)
        return placeholder

    # 1. Protect Fenced Code (```)
    text = re.sub(r'```[\s\S]*?```', replacer, text)
    
    # 2. Protect Inline Code (`)
    text = re.sub(r'(?<!`)`[^`\n]+`(?!`)', replacer, text)

    # 3. Protect Liquid/Nunjucks Variables {{ ... }}
    text = re.sub(r'\{\{.*?\}\}', replacer, text)

    # 4. Protect Liquid/Nunjucks Tags {% ... %}
    text = re.sub(r'\{%.*?%\}', replacer, text)

    return text

def restore_blocks(text):
    for placeholder, original in code_block_map.items():
        if placeholder in text:
            text = text.replace(placeholder, original)
    code_block_map.clear()
    return text

# --- 3. Transformation Logic ---

def get_youtube_thumbnail(video_id):
    return f"[https://img.youtube.com/vi/](https://img.youtube.com/vi/){video_id}/0.jpg"

def transform_autolinks_and_artifacts(text):
    """
    Regex-based transformations for raw text issues.
    """
    # 1. Convert <https://...> to [https://...](https://...)
    text = re.sub(r'<((?:https?|mailto):[^>]+)>', r'[\1](\1)', text)
    
    # 2. Fix pseudo-closing email tags </user@domain.com> -> <user@domain.com>
    text = re.sub(r'</([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>', r'<\1>', text)

    # 3. Remove orphaned &nbsp; entities
    text = text.replace('&nbsp;', ' ')

    # 4. Remove orphaned </span> tags (regex to catch them even if they have whitespace)
    text = re.sub(r'</span>', '', text)

    return text

def transform_html_soup(soup):
    changes_made = False

    # A. iFramely Links (<a data-iframely-url...>)
    # These often have an empty body but a valid href
    for a in soup.find_all('a'):
        if a.has_attr('data-iframely-url'):
            href = a.get('href', '')
            if href:
                # Convert to standard link
                replacement = f"[{href}]({href})"
                a.replace_with(NavigableString(replacement))
                changes_made = True

    # B. Horizontal Rules (<hr>)
    for hr in soup.find_all('hr'):
        hr.replace_with(NavigableString("\n\n---\n\n"))
        changes_made = True

    # C. Spans - Unwrap
    for span in soup.find_all('span'):
        span.unwrap()
        changes_made = True

    # D. Line Breaks (<br>)
    for br in soup.find_all('br'):
        br.replace_with(NavigableString("\n"))
        changes_made = True

    # E. Inline Formatting
    for tag in soup.find_all(['strong', 'b']):
        tag.insert_before(NavigableString("**"))
        tag.insert_after(NavigableString("**"))
        tag.unwrap()
        changes_made = True

    for tag in soup.find_all(['em', 'i']):
        tag.insert_before(NavigableString("*"))
        tag.insert_after(NavigableString("*"))
        tag.unwrap()
        changes_made = True

    # F. Headers
    for level in range(1, 7):
        tag_name = f'h{level}'
        for h in soup.find_all(tag_name):
            content = h.get_text(strip=True)
            if content:
                replacement = f"\n\n{'#' * level} {content}\n\n"
                h.replace_with(NavigableString(replacement))
                changes_made = True
            else:
                h.decompose()

    # G. Blockquotes
    for bq in soup.find_all('blockquote'):
        if 'twitter-tweet' in bq.get('class', []):
            links = bq.find_all('a')
            if links:
                tweet_url = links[-1]['href']
                text = bq.get_text(strip=True)
                replacement = f"> {text}\n>\n> — [View on Twitter]({tweet_url})\n"
                bq.replace_with(NavigableString(replacement))
                changes_made = True
            continue

        content = bq.decode_contents()
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            clean = line.strip()
            if clean:
                new_lines.append(f"> {clean}")
        
        if new_lines:
            replacement = "\n\n" + "\n".join(new_lines) + "\n\n"
            bq.replace_with(NavigableString(replacement))
            changes_made = True

    # H. Paragraphs & Lists
    for p in soup.find_all('p'):
        content = p.decode_contents().strip()
        if content:
            p.insert_before(NavigableString("\n\n"))
            p.unwrap()
            changes_made = True
        else:
            p.decompose()

    for li in soup.find_all('li'):
        content = li.decode_contents().strip()
        replacement = f"\n* {content}"
        li.replace_with(NavigableString(replacement))
        changes_made = True
    
    for ul in soup.find_all(['ul', 'ol']):
        ul.unwrap()
        changes_made = True

    # I. Final Structural Unwrap
    for tag in soup.find_all(['div', 'article', 'section']):
        tag.unwrap()
        changes_made = True

    return changes_made

# --- 4. Main Processing Logic ---

def clean_body_content(raw_body):
    if not raw_body.strip(): return "", False

    # 1. Protect Code AND Liquid Tags
    safe_body = protect_code_blocks_and_liquid(raw_body)
    
    # 2. Text-Regex Transformations (Autolinks, Orphaned tags)
    pre_regex_body = safe_body
    safe_body = transform_autolinks_and_artifacts(safe_body)
    regex_modified = (pre_regex_body != safe_body)

    # 3. Parse HTML
    soup = BeautifulSoup(safe_body, 'html.parser')

    # 4. Transform HTML Tags
    html_fixed = transform_html_soup(soup)

    # 5. Output
    cleaned_content = soup.decode(formatter=None)
    final_body = restore_blocks(cleaned_content)
    
    # Cleanup
    final_body = final_body.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    final_body = re.sub(r'\n{3,}', '\n\n', final_body)
    final_body = final_body.replace('** **', ' ')
    final_body = final_body.strip()

    was_modified = regex_modified or html_fixed
    return final_body, was_modified

def print_diff(filename, original, modified):
    print(f"\n👀 PREVIEW CHANGES for: {filename}")
    diff = difflib.unified_diff(
        original.splitlines(), 
        modified.splitlines(), 
        fromfile='Original', 
        tofile='Modified', 
        lineterm=''
    )
    for line in list(diff)[:30]: 
        color = ""
        if line.startswith('+'): color = "\033[92m" 
        elif line.startswith('-'): color = "\033[91m" 
        print(f"{color}{line}\033[0m")
    print("...\n")

def process_directory(directory):
    if not os.path.exists(directory):
        print(f"❌ Error: Directory not found at {directory}")
        return

    print(f"🚀 STARTING SURGICAL MIGRATION V8 (Dry Run: {DRY_RUN})")
    print(f"📂 Scanning: {directory}\n" + "="*40)

    stats = {'processed': 0, 'modified': 0, 'errors': 0}
    preview_shown = False

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.md', '.markdown', '.html')):
                filepath = os.path.join(root, file)
                stats['processed'] += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        original_full = f.read()

                    frontmatter, body = extract_frontmatter(original_full)
                    
                    if not validate_frontmatter(frontmatter):
                        print(f"   ⚠️ Skipping {file}: Invalid YAML detected.")
                        stats['errors'] += 1
                        continue

                    cleaned_body, modified = clean_body_content(body)
                    
                    if modified:
                        new_full = f"{frontmatter}\n{cleaned_body}".strip() + "\n"

                        if new_full.strip() != original_full.strip():
                            if not preview_shown and DRY_RUN:
                                print_diff(file, original_full, new_full)
                                preview_shown = True

                            if not DRY_RUN:
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    f.write(new_full)
                                print(f"   💾 Updated: {file}")
                            else:
                                print(f"   📝 [Dry Run] Found targets in: {file}")
                            
                            stats['modified'] += 1
                
                except Exception as e:
                    print(f"   ❌ Error processing {file}: {e}")
                    stats['errors'] += 1

    print("\n" + "="*40)
    print(f"🏁 COMPLETION SUMMARY")
    print(f"   Files Scanned:  {stats['processed']}")
    print(f"   Files Modified: {stats['modified']}")
    print(f"   Errors:         {stats['errors']}")
    
    if DRY_RUN:
        print("\nℹ️  Review the PREVIEW above.")
        print("    Checks for iFramely, orphaned </span>, pseudo-tags, and {{ liquid }}.")
        print("    If satisfied, set DRY_RUN = False.")

if __name__ == "__main__":
    process_directory(DEFAULT_PATH)
