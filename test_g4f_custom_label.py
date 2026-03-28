import os
# Set the environment variables for the openai provider
os.environ["OPENAI_API_BASE"] = "http://localhost:8317/v1"
os.environ["OPENAI_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

from g4f.client import Client

# Try to use the custom provider
client = Client(provider="custom")

response = client.chat.completions.create(
    model="arcee-ai/trinity-large-preview:free",  # We know this model exists
    messages=[{"role": "user", "content": "Say hello in one word"}],
    max_tokens=10
)
print("Response:", response.choices[0].message.content)
