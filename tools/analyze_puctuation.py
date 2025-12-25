import os
import re
from collections import defaultdict

# --- Configuration ---
EXTENSIONS = ('.md', '.markdown')

# --- Regex Patterns ---
YEAR_PATTERN = re.compile(r'^date:\s*["\']?(\d{4})', re.MULTILINE)

# Map choices to their names and regex patterns
PUNCTUATION_MAP = {
    'a': {'name': 'Hyphens', 'pattern': re.compile(r'-'), 'symbol': '■'},
    'b': {'name': 'Em Dashes', 'pattern': re.compile(r'—|--'), 'symbol': '█'},
    'c': {'name': 'Ellipses', 'pattern': re.compile(r'\.{3,}'), 'symbol': '░'}
}

def analyze_markdown(target_dir, selected_keys):
    # Stats structure: stats[year][category_name] = count
    stats = defaultdict(lambda: {PUNCTUATION_MAP[k]['name']: 0 for k in selected_keys})

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(EXTENSIONS):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        year_match = YEAR_PATTERN.search(content)
                        if year_match:
                            year = year_match.group(1)
                            
                            for key in selected_keys:
                                p_data = PUNCTUATION_MAP[key]
                                count = len(p_data['pattern'].findall(content))
                                stats[year][p_data['name']] += count
                except Exception as e:
                    print(f"Could not read {path}: {e}")
    return stats

def display_chart(stats, selected_keys):
    if not stats:
        print("\n[!] No data found. Check directory or 'date:' frontmatter.")
        return

    years = sorted(stats.keys())
    categories = [PUNCTUATION_MAP[k]['name'] for k in selected_keys]
    
    # Calculate global max for scaling
    max_val = 0
    for year_data in stats.values():
        for cat_name in categories:
            max_val = max(max_val, year_data[cat_name])
    
    max_bar_width = 50 

    print("\n" + "="*60)
    print("PUNCTUATION FREQUENCY BY YEAR")
    print("="*60)

    for year in years:
        print(f"\n{year}")
        for key in selected_keys:
            cat_name = PUNCTUATION_MAP[key]['name']
            symbol = PUNCTUATION_MAP[key]['symbol']
            count = stats[year][cat_name]
            
            bar_length = int((count / max_val) * max_bar_width) if max_val > 0 else 0
            bar = symbol * bar_length
            print(f"  {cat_name.ljust(12)} | {bar} ({count})")
    print("\n" + "="*60)

if __name__ == "__main__":
    # 1. Get Directory
    user_path = input("Enter the path to your Markdown directory: ").strip()
    
    if os.path.isdir(user_path):
        # 2. Get Punctuation Choices
        print("\nWhich punctuation would you like to report?")
        print("a) Hyphens (-)")
        print("b) Em Dashes (— or --)")
        print("c) Ellipses (...)")
        choice_input = input("\nEnter choices (e.g., 'ab' or 'abc'): ").lower().strip()
        
        # Filter valid choices
        selected_keys = [char for char in choice_input if char in PUNCTUATION_MAP]
        
        if not selected_keys:
            print("No valid choices selected. Exiting.")
        else:
            results = analyze_markdown(user_path, selected_keys)
            display_chart(results, selected_keys)
    else:
        print(f"Error: '{user_path}' is not a valid directory.")