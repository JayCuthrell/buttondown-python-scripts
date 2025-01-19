import re
from datetime import datetime

def process_markdown(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Split the content into lines
    lines = content.splitlines()
    
    # Initialize an empty list to store the extracted data
    data = []

    # Extract the title, URL, and date posted from each list item using regex
    for line in lines:
        match = re.match(r'[\s-]*\[(.*?)\]\((.*?)\)\s*(.*)', line)
        if match:
            title = match.group(1)
            url = match.group(2)
            date_str = match.group(3).strip()
            if date_str:  # Check if date_str is not empty
                date_obj = datetime.strptime(date_str, '%Y %b %d')
                data.append({'title': title, 'url': url, 'date': date_obj})

    # Sort the data list in reverse chronological order
    data.sort(key=lambda x: x['date'], reverse=True)

    # Generate output file name
    output_file_path = "sorted-" + file_path

    # Output the updated markdown list to the output file
    with open(output_file_path, 'w') as outfile:
        outfile.write("# Newsletters published in 2024\n")
        for item in data:
            outfile.write(f"- [{item['title']}]({item['url']}) {item['date'].strftime('%Y %b %d')}\n")

# Ask for the input file name
file_path = input("Enter the input file name: ")

# Process the markdown file
process_markdown(file_path)
