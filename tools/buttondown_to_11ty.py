import os
import re
import requests
import frontmatter
import yaml # To catch specific parsing errors
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

# --- Configuration ---
REDIRECTS_FILE = '~/github/buttondown-python-scripts/legacy_redirects.txt'
FUDGE_SITEMAP_URL = "https://fudge.org/sitemap.xml"
JAY_SITEMAP_URL = "https://jaycuthrell.com/sitemap.xml"

POSTS_DIR = os.path.join('src', 'posts')
SEARCH_DIR = os.path.join('src')
LINK_FAILURE_LOG = 'migration_failures_links.txt'
YAML_FAILURE_LOG = 'migration_failures_frontmatter.txt'

# --- Manual Overrides ---
MANUAL_MAPPING = {
    '/subscribe': 'https://fudge.org/subscribe',
    '/login': 'https://fudge.org/login',
    '/p': 'https://fudge.org/archive/',
    '/issues': 'https://fudge.org/archive/',
    '/archive': 'https://fudge.org/archive/',
    '/twenty-years-of-blogging': 'https://fudge.org/archive/20-years-of-blogging/',
    '/my-second-year': 'https://fudge.org/archive/my-second-year-at-vce/',
    '/emc-converged-platforms': 'https://fudge.org/archive/',
    '/dell-emc-converged-platforms-and-solutions': 'https://fudge.org/archive/',
}

LEGACY_DOMAIN_REGEX = r'(https?://(?:sunday\.fudge\.org|jaycuthrell\.com))([a-zA-Z0-9\-\.\/_]*)'

DRY_RUN = True

def load_local_redirects():
    full_path = os.path.abspath(os.path.expanduser(REDIRECTS_FILE))
    redirects = {}
    if not os.path.exists(full_path):
        print(f"❌ CRITICAL: Redirects file not found at {full_path}")
        return redirects

    print(f"📂 Loading redirects from {full_path}...")
    with open(full_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            parts = line.split()
            if len(parts) >= 2: redirects[parts[0]] = parts[1]
    
    print(f"✅ Loaded {len(redirects)} redirect rules.")
    return redirects

def fetch_sitemap_paths(url, label="Sitemap"):
    print(f"🌍 Fetching {label} from {url}...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return set()
        root = ET.fromstring(response.content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        paths = set()
        for url_tag in root.findall('ns:url', namespaces):
            loc = url_tag.find('ns:loc', namespaces).text
            paths.add(urlparse(loc).path)
        print(f"✅ {label} verified. Found {len(paths)} live URLs.")
        return paths
    except Exception: return set()

def clean_slug(text):
    return re.sub(r'-\d+$', '', text)

def normalize_path(path):
    return path + '/' if not path.endswith('/') else path

def find_best_match(domain, path, redirects_map, fudge_paths, jay_paths):
    clean_path = path.rstrip('/')
    if clean_path == '':
        return "https://jaycuthrell.com/" if 'jaycuthrell.com' in domain else "https://fudge.org/"

    if 'jaycuthrell.com' in domain:
        if normalize_path(clean_path) in jay_paths:
            return f"https://jaycuthrell.com{clean_path}/"

    if clean_path in MANUAL_MAPPING: return MANUAL_MAPPING[clean_path]
    if clean_path in redirects_map: return redirects_map[clean_path]
    if path in redirects_map: return redirects_map[path]

    segments = clean_path.strip('/').split('/')
    clean_key_map = {clean_slug(k.split('/')[-1]): v for k, v in redirects_map.items()}

    for segment in reversed(segments):
        cleaned_segment = clean_slug(segment)
        if cleaned_segment in clean_key_map:
            return clean_key_map[cleaned_segment]

    for segment in segments:
        if segment.isdigit():
            for key, target in redirects_map.items():
                if segment in key: return target

    potential_slug = clean_slug(segments[-1]) if segments else ""
    if potential_slug:
        potential_path = f"/archive/{potential_slug}/"
        if potential_path in fudge_paths:
            return f"https://fudge.org{potential_path}"

    return None

def sanitize_and_heal_frontmatter(directory, redirects_map):
    """
    1. Reads every file.
    2. Checks for YAML errors (bad quotes, colons).
    3. Heals missing permalinks using redirects_map.
    4. RE-SAVES file to enforce standard YAML formatting.
    """
    print(f"\n🔍 Auditing & Sanitizing Frontmatter in {directory}...")
    yaml_failures = []
    
    # Map for healing: slug -> permalink
    slug_perm_map = {clean_slug(k.split('/')[-1]): urlparse(v).path for k, v in redirects_map.items()}
    
    files_processed = 0
    files_healed = 0

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                filename_slug = os.path.splitext(file)[0]
                
                try:
                    # Attempt to Parse
                    post = frontmatter.load(filepath)
                    
                    # Track if we need to save (always save if valid to normalize quotes)
                    needs_save = True 
                    
                    # Logic 1: Heal Permalink
                    if 'permalink' not in post.metadata:
                        if filename_slug in slug_perm_map:
                            new_perm = slug_perm_map[filename_slug]
                            print(f"   ✨ Healing {file} -> {new_perm}")
                            post.metadata['permalink'] = new_perm
                            files_healed += 1
                    
                    # Logic 2: Re-Save to normalize YAML (Fixes 'Title: Subtitle' issues)
                    if needs_save and not DRY_RUN:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                            
                    files_processed += 1

                except (yaml.YAMLError, Exception) as e:
                    print(f"   ❌ CORRUPT FRONTMATTER: {file}")
                    print(f"      Reason: {e}")
                    yaml_failures.append(f"{filepath} | Error: {e}")

    return yaml_failures

def replace_links_in_content(directory, redirects_map, fudge_paths, jay_paths):
    print("\n🔍 Scanning content for links...")
    failures = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.md', '.njk', '.html', '.json')):
                filepath = os.path.join(root, file)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                    except UnicodeDecodeError:
                        print(f"   ⚠️ Skipping binary/non-utf8 file: {file}")
                        continue
                        
                    if 'sunday.fudge.org' not in content and 'jaycuthrell.com' not in content:
                        continue

                new_lines = []
                modified = False
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    matches = re.finditer(LEGACY_DOMAIN_REGEX, line)
                    current_line = line
                    for match in matches:
                        full_match = match.group(0) 
                        domain = match.group(1)     
                        path = match.group(2)       
                        
                        new_target = find_best_match(domain, path, redirects_map, fudge_paths, jay_paths)
                        
                        if new_target:
                            if full_match != new_target:
                                print(f"   ✅ [Fixed] {full_match} -> {new_target}")
                                current_line = current_line.replace(full_match, new_target)
                                modified = True
                        else:
                            print(f"   ❌ [Failed] {full_match}")
                            failures.append(f"{filepath}:{i+1} - {full_match}")

                    new_lines.append(current_line)

                if modified and not DRY_RUN:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    print(f"   💾 Saved link updates: {filepath}")
    return failures

def main():
    print("🚀 STARTING MIGRATION V11 (Sanitizer Mode)\n" + "="*40)
    
    redirects_map = load_local_redirects()
    fudge_paths = fetch_sitemap_paths(FUDGE_SITEMAP_URL, "Fudge.org")
    jay_paths = fetch_sitemap_paths(JAY_SITEMAP_URL, "JayCuthrell.com")
    
    # Step 1: Frontmatter Audit & Heal
    yaml_errors = sanitize_and_heal_frontmatter(POSTS_DIR, redirects_map)
    
    # Step 2: Link Migration
    link_errors = replace_links_in_content(SEARCH_DIR, redirects_map, fudge_paths, jay_paths)

    # --- Reporting ---
    print("\n" + "="*40)
    
    if yaml_errors:
        with open(YAML_FAILURE_LOG, 'w') as f: f.write("\n".join(yaml_errors))
        print(f"🚨 {len(yaml_errors)} files have BROKEN frontmatter (quotes/colons).")
        print(f"   Review: {YAML_FAILURE_LOG}")
    else:
        print("✨ Frontmatter check passed! All files valid.")

    if link_errors:
        with open(LINK_FAILURE_LOG, 'w') as f: f.write("\n".join(link_errors))
        print(f"⚠️  {len(link_errors)} links could not be resolved.")
        print(f"   Review: {LINK_FAILURE_LOG}")
    else:
        print("🔗 All links resolved successfully!")

    if DRY_RUN:
        print("\n🏁 DRY RUN COMPLETE.")
        print("   1. Check the logs above.")
        print("   2. To apply fixes (and normalize quotes), set DRY_RUN = False.")
    else:
        print("\n🏁 MIGRATION & SANITIZATION APPLIED.")

if __name__ == "__main__":
    main()
