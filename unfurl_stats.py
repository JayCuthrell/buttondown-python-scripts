# unfurl_counter.py

import os
import re
from urllib.parse import urlparse
from collections import Counter
import argparse

def find_standalone_urls(directory):
    """
    Recursively finds all markdown files in a directory, reads them line by line,
    and extracts URLs that appear on a line by themselves.

    Args:
        directory (str): The path to the directory to start searching from.

    Returns:
        collections.Counter: A Counter object with FQDNs as keys and their
                             frequencies as values.
    """
    # This regex matches a line that consists ONLY of a URL starting with http or https.
    # The `^` and `$` ensure the entire line must match the URL pattern.
    url_pattern = re.compile(r'^https?://[^\s]+$')
    
    # Using collections.Counter is a clean and efficient way to count hashable objects.
    domain_counter = Counter()

    print(f"🔍 Starting search in directory: '{directory}'...")

    # os.walk is perfect for recursively traversing a directory tree.
    for root, _, files in os.walk(directory):
        for filename in files:
            # We only want to examine markdown files.
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            # .strip() removes leading/trailing whitespace, including newlines.
                            stripped_line = line.strip()
                            if url_pattern.match(stripped_line):
                                # If a match is found, parse the URL to get the domain.
                                # urlparse().netloc gives us the FQDN (e.g., 'www.example.com').
                                parsed_url = urlparse(stripped_line)
                                if parsed_url.netloc:
                                    domain_counter[parsed_url.netloc] += 1
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

    # --- Print the sorted statistics ---
    print("\n--- Domain Statistics (Most to Least Common) ---")
    # .most_common() returns a list of (element, count) tuples, sorted by count.
    for domain, count in domain_counter.most_common():
        print(f"{count}: {domain}")

    # --- Print the Eleventy configuration block ---
    print("\n--- Eleventy 'allowedDomains' Configuration ---")
    print("Copy and paste the following into your .eleventy.js file:\n")

    # Get a list of just the domain names, already sorted by frequency.
    sorted_domains = [domain for domain, count in domain_counter.most_common()]
    
    # Format the list of strings for JavaScript array syntax.
    # e.g., ['github.com', 'techmeme.com']
    formatted_domains = ", ".join([f"'{d}'" for d in sorted_domains])
    
    # The final, formatted code block.
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
    # argparse provides a professional command-line interface.
    parser = argparse.ArgumentParser(
        description="Analyzes markdown files to find standalone URLs and generates an Eleventy 'allowedDomains' list."
    )
    # This defines the 'directory' argument we expect from the user.
    parser.add_argument(
        'directory',
        type=str,
        help="The root directory to search for markdown files."
    )

    args = parser.parse_args()

    # Check if the provided directory actually exists.
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'")
        return
        
    domain_counts = find_standalone_urls(args.directory)
    print_results(domain_counts)


if __name__ == "__main__":
    main()