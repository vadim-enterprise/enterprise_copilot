from openai import OpenAI

# Initialize the client
client = OpenAI()  # Make sure OPENAI_API_KEY is set in your environment

# Create a fine-tuning job
response = client.fine_tuning.jobs.create(
    training_file="file-FViN9JYzJ1VjL3muwc8iqX",  # Your file ID
    model="gpt-4"
)

print(response)