import feedparser
import time

def get_sunday_articles(rss_feed_url):
    """
    Fetches articles from an RSS feed, filters them based on the publication date 
    (Sunday), and prints the titles and links of the filtered articles to the terminal.

    Args:
      rss_feed_url: The URL of the RSS feed.
    """
    feed = feedparser.parse(rss_feed_url)
    articles = []

    for entry in feed.entries:
        if entry.published_parsed.tm_wday == 6:  # 6 represents Sunday
            published = time.strftime('%Y %b %d', entry.published_parsed)
            articles.append(f" - [{entry['title']}]({entry['link']}) {published}")

    if articles:
        print("Articles published on Sunday:")
        for article in articles:
            print(article)
    else:
        print("No articles published on Sunday found.")

# Replace with the actual RSS feed URL
rss_feed_url = "https://hot.fudge.org/rss"  
get_sunday_articles(rss_feed_url)
