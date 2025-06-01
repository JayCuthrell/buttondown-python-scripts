import feedparser
import datetime
import argparse
from collections import defaultdict

def analyze_blog_posts(rss_url, max_posts=200):
    """Analyzes blog posts from an RSS feed and generates a report with a simplified histogram."""

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        return f"Error parsing RSS feed: {e}"

    if feed.status!= 200:
        return f"Error: RSS feed returned status code {feed.status}"

    max_posts = min(max_posts, len(feed.entries))
    posts = feed.entries[:max_posts]
    earliest_date = None

    report = f"Blog Post Analysis for {rss_url} (Up to {max_posts} Posts):\n\n"

    for i, entry in enumerate(posts):
        try:
            title = entry.title
            published_date = datetime.datetime(*entry.published_parsed[:6])
            if earliest_date is None or published_date < earliest_date:
                earliest_date = published_date
            link = entry.link

            report += f"Post {i+1}:\n"
            report += f"  Title: {title}\n"
            report += f"  Published Date: {published_date.strftime('%Y-%m-%d')}\n"
            report += f"  Link: {link}\n\n"
        except (AttributeError, TypeError):
            report += f"Error: Could not retrieve information for post {i+1}.\n\n"
            continue

    if earliest_date is None:
        return "No valid dates found in the RSS feed."

    monthly_counts = defaultdict(int)
    for entry in posts:
        try:
            published_date = datetime.datetime(*entry.published_parsed[:6])
            month_year = published_date.strftime("%Y-%b")  # Combine year and month
            monthly_counts[month_year] += 1
        except (AttributeError, TypeError):
            continue

    report += "\nMonthly Histogram (All Time):\n"
    months = sorted(monthly_counts.keys())  # Sort by year-month

    max_count = max(monthly_counts.values()) if monthly_counts else 0

    for month_year in months:
        count = monthly_counts.get(month_year, 0)
        bar_length = int((count / max_count) * 20) if max_count > 0 else 0
        report += f"{month_year}: {'*' * bar_length} ({count})\n"

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze blog posts from an RSS feed.")
    parser.add_argument("rss_url", help="The RSS feed URL")
    parser.add_argument("-m", "--max_posts", type=int, default=200, help="Maximum number of posts to analyze (default: 200)")
    args = parser.parse_args()

    report = analyze_blog_posts(args.rss_url, args.max_posts)
    print(report)
