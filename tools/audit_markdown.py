import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import argparse
import datetime
import os
import re
import concurrent.futures
from threading import Lock
from urllib.parse import urlparse

# Rich library imports for UI
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table

# Initialize Rich Console
console = Console()

# Domains that are known to block bots (Report as VALID to reduce noise)
NOISY_DOMAINS = [
    "linkedin.com",
    "www.linkedin.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "unsplash.com",
    "wsj.com",
    "www.wsj.com",
    "tiktok.com",
    "www.tiktok.com",
    "instagram.com",
    "www.instagram.com"
]

# Domains that are known to be offline (Report as BROKEN immediately to save time)
KNOWN_DEAD_DOMAINS = [
    "rev.vu"
]

# File extensions to strictly ignore
IMAGE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', 
    '.tiff', '.bmp', '.mp4', '.mov', '.avi'
)

def get_resilient_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarkdownAuditor/1.0"
    })
    return session

def save_report_to_file(directory, broken_links):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"link_audit_report_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"MARKDOWN LINK AUDIT REPORT\n")
        f.write(f"Target Directory: {os.path.abspath(directory)}\n")
        f.write(f"Date: {datetime.datetime.now()}\n")
        f.write("="*60 + "\n\n")

        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 30 + "\n")
        
        if not broken_links:
            f.write("No broken links found. Great job!\n")
        else:
            f.write(f"[ ] FIX BROKEN LINKS: {len(broken_links)} unique links are invalid.\n")
        
        f.write("\n" + "="*60 + "\n\n")

        if broken_links:
            f.write(f"DETAILED: Broken Links Found ({len(broken_links)})\n")
            f.write("-" * 20 + "\n")
            for broken_url, details in broken_links.items():
                f.write(f" ❌ Invalid Link: {broken_url}\n")
                if details.get('error'):
                    f.write(f"    Error: {details['error']}\n")
                f.write(f"    Found in {len(details['sources'])} file(s):\n")
                for source in details['sources']:
                    f.write(f"      -> {source}\n")
                f.write("\n")
                
    return filename

def extract_links_from_markdown(file_content):
    links = []
    
    # 1. Standard markdown links [text](url)
    # The negative lookbehind (?<!!) ensures we ignore images which start with ![
    md_links = re.findall(r'(?<!\!)\[.*?\]\(([^\)]+)\)', file_content)
    links.extend(md_links)
    
    # 2. HTML hrefs
    html_links = re.findall(r'href=["\'](.*?)["\']', file_content)
    links.extend(html_links)
    
    # REMOVED: HTML src checking (scanning src usually picks up images)
    
    return links

def is_local_file_valid(base_file_path, link_path, project_root=None):
    link_path = link_path.split('#')[0]
    link_path = link_path.split('?')[0] 
    
    if link_path.startswith('mailto:') or not link_path:
        return True, None

    try:
        target_path = None
        if link_path.startswith('/'):
            if project_root:
                target_path = os.path.normpath(os.path.join(project_root, link_path.lstrip('/')))
            else:
                return False, "Missing --root arg for absolute path"
        else:
            base_dir = os.path.dirname(base_file_path)
            target_path = os.path.normpath(os.path.join(base_dir, link_path))
        
        if target_path and os.path.exists(target_path):
            return True, None
        else:
            return False, "File not found locally"
            
    except Exception as e:
        return False, str(e)

def check_link(link, session, file_path, url_cache, cache_lock, project_root):
    is_broken = False
    error_msg = ""
    
    with cache_lock:
        if link in url_cache:
            return link, url_cache[link][0], url_cache[link][1], file_path

    if link.startswith(('http://', 'https://')):
        domain = urlparse(link).netloc.lower()
        
        if any(noisy in domain for noisy in NOISY_DOMAINS):
             with cache_lock:
                url_cache[link] = (False, "Ignored Domain")
             return link, False, "Ignored Domain", file_path

        if any(dead in domain for dead in KNOWN_DEAD_DOMAINS):
             with cache_lock:
                url_cache[link] = (True, "Known Dead Service")
             return link, True, "Known Dead Service", file_path

        try:
            r = session.head(link, timeout=5, allow_redirects=True)
            if r.status_code == 405: 
                r = session.get(link, timeout=5, stream=True)
            
            if r.status_code >= 400:
                if r.status_code == 404:
                    r_get = session.get(link, timeout=5, stream=True)
                    if r_get.status_code >= 400:
                        is_broken = True
                        error_msg = f"Status Code: {r_get.status_code}"
                else:
                    is_broken = True
                    error_msg = f"Status Code: {r.status_code}"
        except requests.RequestException:
            is_broken = True
            error_msg = "Connection Error"

    elif not link.startswith(('mailto:', 'tel:', '#', '{')):
        valid, msg = is_local_file_valid(file_path, link, project_root)
        if not valid:
            is_broken = True
            error_msg = msg
    
    if link.startswith(('http', 'https')):
        with cache_lock:
            url_cache[link] = (is_broken, error_msg)

    return link, is_broken, error_msg, file_path

def audit_directory(directory, project_root=None, skip_list=None):
    if skip_list is None: skip_list = []
    
    broken_links = {}
    session = get_resilient_session()
    
    md_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(root, file))

    if not md_files:
        console.print("[bold red]❌ No Markdown (.md) files found.[/bold red]")
        return {}

    total_files = len(md_files)
    console.print(f"[bold blue]🚀 Starting analysis for:[/bold blue] {directory}")
    if project_root:
        console.print(f"[bold blue]📂 Project Root set to:[/bold blue] {project_root}")
    
    console.print(f"✅ Found [bold green]{total_files}[/bold green] Markdown files.")

    all_tasks = []
    url_cache = {}
    cache_lock = Lock()
    
    console.print("[yellow]Preparing links...[/yellow]")
    
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            links = extract_links_from_markdown(content)
            
            for link in links:
                if any(skip in link for skip in skip_list): continue
                if link.lower().endswith(IMAGE_EXTENSIONS): continue
                if link.startswith(('#', 'mailto:', 'tel:')): continue
                if link.startswith(('http://', 'https://')):
                     domain = urlparse(link).netloc.lower()
                     if any(noisy in domain for noisy in NOISY_DOMAINS): continue

                all_tasks.append((link, file_path))
                
        except Exception as e:
            console.print(f"[red]Error reading {file_path}: {e}[/red]")

    total_links = len(all_tasks)
    console.print(f"🔗 Found [bold green]{total_links}[/bold green] links to check (Images ignored).")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task_id = progress.add_task("[cyan]Checking Links...", total=total_links)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(check_link, link, session, fpath, url_cache, cache_lock, project_root): link 
                for link, fpath in all_tasks
            }
            
            for future in concurrent.futures.as_completed(futures):
                link, is_broken, error_msg, source_path = future.result()
                rel_path = os.path.relpath(source_path, directory)
                
                if is_broken:
                    if link not in broken_links:
                        broken_links[link] = {'error': error_msg, 'sources': []}
                    broken_links[link]['sources'].append(rel_path)
                
                progress.advance(task_id)

    return broken_links

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Markdown files for broken links.")
    parser.add_argument("directory", nargs='?', default=None, help="The directory to scan recursively")
    parser.add_argument("--root", help="The project root directory (for resolving /absolute/paths)", default=None)
    parser.add_argument("--skip-urls", nargs='*', default=[], help="List of substrings to skip")

    args = parser.parse_args()
    
    target_dir = args.directory
    if not target_dir:
        target_dir = console.input("[bold yellow]Please enter the directory path to scan:[/bold yellow] ")

    if not os.path.isdir(target_dir):
        console.print(f"[bold red]Error: '{target_dir}' is not a valid directory.[/bold red]")
        sys.exit(1)

    project_root = args.root if args.root else None

    bad_links = audit_directory(target_dir, project_root=project_root, skip_list=args.skip_urls)

    console.print("\n")
    if bad_links:
        table = Table(title=f"💔 Broken Links Found (Showing top 50 of {len(bad_links)})", style="red")
        table.add_column("Broken Link/Path", style="red", overflow="fold")
        table.add_column("Error", style="yellow")
        table.add_column("Found In (Count)", style="white")
        
        sorted_links = sorted(bad_links.items(), key=lambda item: len(item[1]['sources']), reverse=True)
        
        for link, details in sorted_links[:50]:
            table.add_row(
                link, 
                details.get('error', 'Unknown'), 
                f"{len(details['sources'])} files"
            )
        console.print(table)
        
        if len(bad_links) > 50:
            console.print(f"\n[yellow]... and {len(bad_links) - 50} more items not shown.[/yellow]")
    else:
        console.print("[bold green]🎉 No broken links found! All systems go.[/bold green]")
            
    report_file = save_report_to_file(target_dir, bad_links)
    console.print(f"\n[bold green]✅ Audit complete![/bold green] Detailed report saved to: [underline]{report_file}[/underline]")
