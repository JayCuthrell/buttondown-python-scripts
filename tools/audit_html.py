import os
import re
import uuid

# --- CONFIGURATION ---
DEFAULT_PATH = os.path.expanduser("~/github/fudge-org-eleventy-excellent-4.3.3/src/posts")

# --- GLOBAL STORAGE ---
code_block_map = {}

def protect_code_blocks(text):
    """
    Hides fenced and inline code blocks so we don't count HTML inside them.
    """
    def replacer(match):
        placeholder = f"__CODE_BLOCK_{uuid.uuid4().hex}__"
        code_block_map[placeholder] = match.group(0)
        return placeholder

    # 1. Fenced Code (``` ... ```)
    text = re.sub(r'```[\s\S]*?```', replacer, text)
    
    # 2. Inline Code (` ... `)
    # Negative lookbehind/lookahead ensures we don't match inside existing placeholders
    text = re.sub(r'(?<!`)`[^`\n]+`(?!`)', replacer, text)
    
    return text

def find_html_tags(text):
    """
    Scans for HTML tags.
    Matches: <tag>, </tag>, <tag attribute="...">, <tag />
    Excludes: XML/HTML comments """
    # Remove comments first to avoid false positives
    text = re.sub(r'', '', text)
    
    # Regex for HTML tags:
    # </?       -> Start with < or </
    # [a-zA-Z]  -> Tag name must start with a letter (avoids < 5 math)
    # [^>]* -> Anything else until...
    # >         -> Closing bracket
    tag_pattern = r'</?([a-zA-Z][a-zA-Z0-9:-]*)\b[^>]*>'
    
    matches = re.findall(tag_pattern, text)
    
    # Return a unique list of tag names (lowercase) found in this file
    return sorted(list(set(m.lower() for m in matches)))

def scan_directory(directory):
    print(f"🕵️  STARTING HTML AUDIT")
    print(f"📂 Scanning: {directory}\n" + "="*50)
    
    files_with_html = 0
    total_files = 0
    
    # Tags we generally expect in Markdown (optional whitelist)
    # If you want to see EVERYTHING, leave this empty.
    # whitelist = ['br', 'img'] 
    whitelist = [] 

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.md', '.markdown')):
                total_files += 1
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 1. Hide Code Blocks
                    clean_text = protect_code_blocks(content)
                    
                    # 2. Find Tags
                    tags_found = find_html_tags(clean_text)
                    
                    # 3. Filter out whitelist (if any)
                    tags_found = [t for t in tags_found if t not in whitelist]
                    
                    if tags_found:
                        files_with_html += 1
                        print(f"🚩 {file}")
                        print(f"   Tags: {tags_found}")
                        print("-" * 50)
                        
                except Exception as e:
                    print(f"❌ Error reading {file}: {e}")

    print("\n" + "="*50)
    print(f"🏁 AUDIT COMPLETE")
    print(f"   Files Scanned: {total_files}")
    print(f"   Files with HTML: {files_with_html}")

if __name__ == "__main__":
    if os.path.exists(DEFAULT_PATH):
        scan_directory(DEFAULT_PATH)
    else:
        print(f"❌ Path not found: {DEFAULT_PATH}")
