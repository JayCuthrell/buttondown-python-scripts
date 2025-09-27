# unfurl_counter.py (v2 with domain normalization)

import os
import re
from urllib.parse import urlparse
from collections import Counter
import argparse

def normalize_domain(domain):
    """
    Normalizes a domain by removing the 'www.' prefix if it exists.

    Args:
        domain (str): The domain name to normalize (e.g., 'www.example.com').

    Returns:
        str: The normalized domain name (e.g., 'example.com').
    """
    if domain.startswith('www.'):
        return domain[4:]
    return domain

def find_standalone_urls(directory):
    """
    Recursively finds all markdown files in a directory, reads them line by line,
    and extracts and normalizes URLs that appear on a line by themselves.

    Args:
        directory (str): The path to the directory to start searching from.

    Returns:
        collections.Counter: A Counter object with normalized FQDNs as keys
                             and their frequencies as values.
    """
    # This regex matches a line that consists ONLY of a URL starting with http or https.
    url_pattern = re.compile(r'^https?://[^\s]+$')
    
    domain_counter = Counter()

    print(f"🔍 Starting search in directory: '{directory}'...")

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            stripped_line = line.strip()
                            if url_pattern.match(stripped_line):
                                parsed_url = urlparse(stripped_line)
                                if parsed_url.netloc:
                                    # *** NEW: Normalize the domain before counting it ***
                                    normalized = normalize_domain(parsed_url.netloc)
                                    domain_counter[normalized] += 1
                except Exception as e:
                    print(f"Could not read file {file_path}: {e}")

    return domain_counter

def print_results(domain_counter):
    """
    Prints the statistics of found domains and the formatted Eleventy config block.

    Args:
        domain_counter (collections.Counter): The counter with domain frequencies.
    """
    if not domain_counter:
        print("\n✅ No standalone URLs found.")
        return

    print("\n--- Domain Statistics (Most to Least Common) ---")
    for domain, count in domain_counter.most_common():
        print(f"{count}: {domain}")

    print("\n--- Eleventy 'allowedDomains' Configuration ---")
    print("Copy and paste the following into your .eleventy.js file:\n")

    sorted_domains = [domain for domain, count in domain_counter.most_common()]
    formatted_domains = ", ".join([f"'{d}'" for d in sorted_domains])
    
    config_block = f"""
// Add the opengraph-unfurl plugin
eleventyConfig.addPlugin(plugins.opengraphUnfurl, {{
  allowedDomains: [{formatted_domains}]
}});
"""
    print(config_block)


def main():
    """
    Main function to parse arguments and run the analysis.
    """
    parser = argparse.ArgumentParser(
        description="Analyzes markdown files to find standalone URLs and generates an Eleventy 'allowedDomains' list."
    )
    parser.add_argument(
        'directory',
        type=str,
        help="The root directory to search for markdown files."
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'")
        return
        
    domain_counts = find_standalone_urls(args.directory)
    print_results(domain_counts)


if __name__ == "__main__":
    main()