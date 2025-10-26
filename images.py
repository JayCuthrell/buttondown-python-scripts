# find_images_extended.py

import os
import re
import argparse
from collections import Counter
from urllib.parse import urlparse
from typing import List, Tuple

# Regex for standard Markdown image syntax: ![alt text](url)
MARKDOWN_IMAGE_REGEX = re.compile(r'!\[.*?\]\((.*?)\)')

# NEW: Regex for HTML <img> tags with external sources.
# This pattern specifically looks for `src` attributes containing an http/https URL.
HTML_IMAGE_REGEX = re.compile(r'<img[^>]+src\s*=\s*["\'](https?://[^"\']+)["\']')

def find_markdown_files(root_directory: str) -> List[str]:
    """
    Recursively finds all Markdown files (.md) in a given directory.

    Args:
        root_directory: The path to the directory to start scanning from.

    Returns:
        A list of full file paths for all found Markdown files.
    """
    markdown_files = []
    print(f"🔍 Starting scan in '{root_directory}'...")
    for root, _, files in os.walk(root_directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    print(f"✅ Found {len(markdown_files)} Markdown file(s).")
    return markdown_files

def extract_fqdns_from_file(filepath: str) -> List[str]:
    """
    Reads a file and extracts the FQDN from any external Markdown and HTML image URLs.

    Args:
        filepath: The full path to the file to be read.

    Returns:
        A list of FQDNs (domain names) found in the file.
    """
    fqdns = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Find all URLs from Markdown syntax: ![alt](url)
            markdown_urls = MARKDOWN_IMAGE_REGEX.findall(content)
            
            # MODIFIED: Find all URLs from HTML syntax: <img src="url">
            html_urls = HTML_IMAGE_REGEX.findall(content)

            # MODIFIED: Combine the lists of URLs from both patterns.
            # The HTML regex already filters for http/https, so we process all of them.
            # The Markdown regex captures everything, so we still need to filter those.
            all_urls = markdown_urls + html_urls

            for url in all_urls:
                if url.startswith("http://") or url.startswith("https://"):
                    try:
                        # The 'netloc' attribute contains the domain name (FQDN).
                        domain = urlparse(url).netloc
                        if domain:
                            fqdns.append(domain)
                    except Exception:
                        # Silently ignore URLs that can't be parsed.
                        pass
    except Exception as e:
        print(f"⚠️  Could not read file {filepath}: {e}")
    return fqdns

def main():
    """Main function to run the script."""
    # Set up the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Scan a directory for externally hosted images in Markdown and HTML syntax."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="The path to the directory to scan recursively."
    )
    args = parser.parse_args()

    # Check if the provided directory exists.
    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory not found at '{args.directory}'")
        return

    # Step 1: Find all markdown files.
    markdown_files = find_markdown_files(args.directory)
    if not markdown_files:
        return

    # Step 2: Extract all FQDNs from the files.
    all_fqdns = []
    for file in markdown_files:
        all_fqdns.extend(extract_fqdns_from_file(file))

    # Step 3: Count and sort the FQDNs.
    if not all_fqdns:
        print("\n🎉 No externally hosted images were found!")
        return

    fqdn_counts = Counter(all_fqdns)
    sorted_fqdns: List[Tuple[str, int]] = fqdn_counts.most_common()

    # Step 4: Display the final report.
    print("\n--- External Image Host Report (Markdown + HTML) ---")
    print(f"Found a total of {len(all_fqdns)} external images from {len(sorted_fqdns)} unique domains.\n")
    print(f"{'Domain (FQDN)':<40} {'Image Count'}")
    print(f"{'-'*40:<40} {'-'*11}")

    for fqdn, count in sorted_fqdns:
        print(f"{fqdn:<40} {count}")

    print("\n--- End of Report ---")


if __name__ == "__main__":
    main()
