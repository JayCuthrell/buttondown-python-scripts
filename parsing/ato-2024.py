import requests
from bs4 import BeautifulSoup
import os

def extract_div_content(source, div_tag=None):
  """
  Extracts content from specific div tags in a given URL or HTML file,
  and formats the content into pipe-separated values with When, Title,
  Speaker, and Description on a single line per div, removing any line
  breaks within each element.

  Args:
    source: The URL of the webpage or the path to the local HTML file.
    div_tag: A dictionary specifying the div tag attributes to match (optional).
             e.g., {'id': 'my-div'} or {'class': 'content-block'}

  Returns:
    A list of strings, where each string is the formatted content of a
    matching div.
  """

  try:
    if source.startswith('http://') or source.startswith('https://'):
      # It's a URL
      response = requests.get(source)
      response.raise_for_status()
      soup = BeautifulSoup(response.content, 'html.parser')
    elif os.path.isfile(source):
      # It's a local file
      with open(source, 'r') as f:
        soup = BeautifulSoup(f, 'html.parser')
    else:
      print("Error: Invalid source. Please provide a URL or a valid local HTML file path.")
      return []

    if div_tag:
      divs = soup.find_all('div', div_tag)
    else:
      divs = soup.find_all('div', class_="ato-speaker col c6 b2c6 b3c4 b5c3")

    results = []
    for div in divs:
      url = div.find('a')['href']
      speaker = div.find(class_='ato-speaker-name').get_text(strip=True).replace('\n', '')
      title = div.find(class_='ato-speaker-title').get_text(strip=True).replace('\n', '')
      company = div.find(class_='ato-speaker-employer').get_text(strip=True).replace('\n', '')
      results.append(f"{speaker}|{title}|{company}|{url}")
    return results

  except requests.exceptions.RequestException as e:
    print(f"Error fetching URL: {e}")
    return []
  except Exception as e:
    print(f"An error occurred: {e}")
    return []

if __name__ == "__main__":
  source = input("Enter the URL or local HTML file path: ")
  div_id = input("Enter the div id (leave blank if not applicable): ")
  div_class = input("Enter the div class (leave blank if not applicable): ")

  div_tag = {}
  if div_id:
    div_tag['id'] = div_id
  if div_class:
    div_tag['class'] = div_class

  results = extract_div_content(source, div_tag)

  if results:
    print("Extracted content:")
    for content in results:
      print(content)
  else:
    print("No matching divs found.")
