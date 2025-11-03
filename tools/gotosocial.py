import os
import frontmatter
from datetime import datetime

# --- Configuration ---
# The character limit for a GoToSocial post.
CHARACTER_LIMIT = 5000

def analyze_markdown_files(directory_path):
    """
    Analyzes markdown files in a directory to determine how many are
    under a specific character limit for each day of the week.

    Args:
        directory_path (str): The absolute path to the directory to search.
    """
    # Dictionary to store counts for each day of the week (0=Monday, 6=Sunday)
    # Each day will have a dictionary {'total': count, 'valid': count}
    daily_stats = {i: {'total': 0, 'valid': 0} for i in range(7)}
    
    # Day names for display purposes
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    print(f"🔍 Searching for Markdown files in: {directory_path}\n")

    # Recursively walk through the directory
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                
                try:
                    # Load the markdown file to separate frontmatter and content
                    post = frontmatter.load(file_path)
                    
                    # Ensure the file has a date in its frontmatter
                    if 'date' in post.metadata:
                        post_date = post.metadata['date']
                        
                        # Handle both datetime objects and string dates
                        if isinstance(post_date, str):
                            # Attempt to parse common date formats
                            try:
                                post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                            except ValueError:
                                print(f"⚠️  Could not parse date string: '{post_date}' in {file_path}. Skipping.")
                                continue
                        else:
                            post_datetime = post_date
                            
                        day_of_week = post_datetime.weekday() # Monday is 0 and Sunday is 6
                        
                        # Get the character count of the main content
                        content_char_count = len(post.content)
                        
                        # Update the total count for that day
                        daily_stats[day_of_week]['total'] += 1
                        
                        # Check if it's within the character limit
                        if content_char_count <= CHARACTER_LIMIT:
                            daily_stats[day_of_week]['valid'] += 1
                            
                except Exception as e:
                    print(f"❌ Error processing file {file_path}: {e}")

    # --- Display the results (in Markdown format) ---
    print("--- Analysis Complete ---")
    print("### Post Analysis for GoToSocial\n")
    print(f"Percentage of posts under **{CHARACTER_LIMIT}** characters by day:\n")
    
    # Markdown Table Header
    print(f"| Day       | Suitable Posts | Total Posts | Percentage |")
    print(f"| :-------- | :------------- | :---------- | :--------- |")

    # Calculate and print percentages for Monday through Saturday
    for i in range(6): # Loop from Monday (0) to Saturday (5)
        day_name = day_names[i]
        stats = daily_stats[i]
        
        if stats['total'] > 0:
            percentage_str = f"{((stats['valid'] / stats['total']) * 100):.2f}%"
            print(f"| {day_name} | {stats['valid']} | {stats['total']} | {percentage_str} |")
        else:
            print(f"| {day_name} | 0 | 0 | N/A |")
            
    # Note about Sunday
    print("\n*Sunday is excluded from the percentage calculation as it is reserved for digests.*")
    if daily_stats[6]['total'] > 0:
        print(f"*Found {daily_stats[6]['total']} posts on Sundays.*")


if __name__ == "__main__":
    # Get the directory path from the user
    target_directory = input("Enter the full path to the directory containing your markdown files: ")
    
    # Check if the directory exists
    if os.path.isdir(target_directory):
        analyze_markdown_files(target_directory)
    else:
        print("❌ Error: The provided path is not a valid directory.")
