import csv
import json

# Input: The file you downloaded from Buttondown
input_file = 'buttondown_subscribers.csv'
# Output: The file ready for Listmonk
output_file = 'listmonk_ready.csv'

def migrate():
    with open(input_file, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Prepare the output file
        with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
            # Listmonk headers: email, name, attributes
            fieldnames = ['email', 'name', 'attributes']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            count = 0
            for row in reader:
                # 1. Clean the email
                email = row.get('email', '').strip().lower()
                if not email:
                    continue
                
                # 2. Extract Name (If Buttondown has it, otherwise use part of email)
                name = row.get('name', '').strip() or email.split('@')[0]

                # 3. Handle Attributes (Tags, metadata, etc.)
                # We pack these into a JSON string for Listmonk's 'attributes' column
                attribs = {
                    "source": "buttondown_migration",
                    "tags": row.get('tags', '').split(','),
                    "subscriber_type": row.get('subscriber_type', 'regular')
                }

                writer.writerow({
                    'email': email,
                    'name': name,
                    'attributes': json.dumps(attribs)
                })
                count += 1
            
            print(f"Successfully processed {count} subscribers into {output_file}")

if __name__ == "__main__":
    migrate()
