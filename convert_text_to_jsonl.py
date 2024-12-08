import json

def convert_to_jsonl(input_file, output_file, delimiter='---'):
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            # Split the line into prompt and completion
            parts = line.strip().split(delimiter)
            if len(parts) != 2:
                continue  # Skip lines that don't have exactly one delimiter

            prompt, completion = parts

            # Create the JSONL entry
            entry = {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt.strip()},
                    {"role": "assistant", "content": completion.strip()}
                ]
            }

            # Write the entry to the output file
            json.dump(entry, outfile)
            outfile.write('\n')

# Example usage
convert_to_jsonl('large_text_file.txt', 'fine_tuning_data.jsonl')