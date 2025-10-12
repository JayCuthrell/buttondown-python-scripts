# analyze_posts.py

import os
import re
import yaml
from collections import defaultdict
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
REQUIRED_FRONTMATTER_KEYS = {'title', 'date'} 
LEGACY_HTML_TAGS = ['div', 'span', 'font', 'center', 'table'] 
FRONTMATTER_DELIMITER = re.compile(r'^---\s*$', re.MULTILINE)

def analyze_markdown_file(filepath):
    """
    Analyzes a single markdown file for frontmatter consistency and legacy HTML.
    Returns a tuple: (title, list_of_issues, issue_types_set, found_legacy_tags_list).
    """
    issues = []
    issue_types = set()
    found_tags_list = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            _, fm_string, md_content = FRONTMATTER_DELIMITER.split(content, 2)
            frontmatter = yaml.safe_load(fm_string)
            if not isinstance(frontmatter, dict):
                raise yaml.YAMLError("Frontmatter is not a valid dictionary.")
        except (ValueError, yaml.YAMLError) as e:
            issues.append(f"Invalid or missing YAML frontmatter: {e}")
            issue_types.add('invalid_frontmatter')
            md_content = content 
            frontmatter = {}

        if frontmatter:
            missing_keys = REQUIRED_FRONTMATTER_KEYS - set(frontmatter.keys())
            if missing_keys:
                issues.append(f"Missing required frontmatter keys: {', '.join(missing_keys)}")
                issue_types.add('missing_keys')
        
        # Count all occurrences of each legacy tag
        for tag in LEGACY_HTML_TAGS:
            # re.findall will find all non-overlapping matches of the tag
            matches = re.findall(f'<{tag}[^>]*>', md_content, re.IGNORECASE)
            if matches:
                found_tags_list.extend([f'<{tag}>'] * len(matches))
        
        if found_tags_list:
            # Create a summary of unique tags for the individual file report
            unique_tags_in_file = sorted(list(set(found_tags_list)))
            issues.append(f"Found potential legacy HTML tags: {', '.join(unique_tags_in_file)}")
            issue_types.add('legacy_html')

        return frontmatter.get('title'), issues, issue_types, found_tags_list

    except Exception as e:
        return None, [f"Could not read or process file: {e}"], {'read_error'}, []

def main():
    """
    Main function to find the correct directory, orchestrate the analysis, and print a summary.
    """
    initial_path_str = os.getenv("SYNC_PATH")
    
    if not initial_path_str:
        print("❌ Error: SYNC_PATH not found in your .env file.")
        return

    expanded_path = os.path.expanduser(initial_path_str)
    scan_target_root = "src/posts"
    posts_dir = expanded_path
    
    try:
        target_index = expanded_path.rfind(scan_target_root)
        if target_index != -1:
            posts_dir = expanded_path[:target_index + len(scan_target_root)]
            print(f"✅ Found '{scan_target_root}'. Scanning directory: '{posts_dir}'")
        else:
            print(f"⚠️ Warning: '{scan_target_root}' not found in SYNC_PATH. Scanning the provided directory directly.")
    except Exception:
        pass

    if not os.path.isdir(posts_dir):
        print(f"❌ Error: The directory to scan does not exist: '{posts_dir}'")
        return
        
    print(f"🔍 Starting analysis...")
    
    all_issues = defaultdict(list)
    titles_seen = defaultdict(list)
    issue_type_counts = defaultdict(int)
    legacy_html_tag_counts = defaultdict(int)
    total_files_scanned = 0

    for root, _, files in os.walk(posts_dir):
        for filename in files:
            if filename.endswith('.md'):
                total_files_scanned += 1
                filepath = os.path.join(root, filename)
                title, issues, issue_types, found_tags = analyze_markdown_file(filepath)
                
                if title:
                    titles_seen[title].append(filepath)

                if issues:
                    all_issues[filepath].extend(issues)
                    for issue_type in issue_types:
                        issue_type_counts[issue_type] += 1
                
                if found_tags:
                    for tag in found_tags:
                        legacy_html_tag_counts[tag] += 1
    
    print("\n--- Analysis Complete ---")

    # --- Report on Duplicate Titles ---
    duplicate_title_count = 0
    has_duplicates = False
    for title, paths in titles_seen.items():
        if len(paths) > 1:
            if not has_duplicates:
                print("\n❗️ Found Duplicate Titles:")
                has_duplicates = True
            print(f"\n- Title: \"{title}\"")
            duplicate_title_count += len(paths)
            for path in paths:
                print(f"  - {path}")
    
    if not has_duplicates:
        print("\n✅ No duplicate titles found.")

    # --- Report on File-Specific Issues ---
    if all_issues:
        print("\n❗️ Found Files Needing Attention:")
        for filepath, issues in sorted(all_issues.items()):
            print(f"\n📄 File: {filepath}")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print("\n✅ All files passed the consistency and HTML checks.")

    # --- NEW: Report on Legacy HTML Tag Breakdown ---
    if legacy_html_tag_counts:
        print("\n❗️ Legacy HTML Tag Breakdown (Most to Least Common):")
        # Sort the tags by count in descending order
        sorted_tags = sorted(legacy_html_tag_counts.items(), key=lambda item: item[1], reverse=True)
        for tag, count in sorted_tags:
            print(f"  - {tag}: {count} occurrences")
        
    print("\n-------------------------")
    
    # --- Final Summary Statistics ---
    print("\n📊 Analysis Summary")
    print("="*25)
    print(f"Total Files Scanned:         {total_files_scanned}")
    print(f"Files With Issues:           {len(all_issues)}")
    print("-" * 25)
    print(f"Duplicate Titles Found:      {duplicate_title_count}")
    print(f"Files with Legacy HTML:      {issue_type_counts['legacy_html']} (see breakdown above)")
    print(f"Files with Missing Keys:     {issue_type_counts['missing_keys']}")
    print(f"Files with Invalid Frontmatter: {issue_type_counts['invalid_frontmatter']}")
    print("="*25)


if __name__ == '__main__':
    main()