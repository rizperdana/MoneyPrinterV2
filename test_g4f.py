import os
# Set environment variables for gpt4free to use our endpoint
os.environ["G4F_API_BASE"] = "http://localhost:8317/v1"
os.environ["G4F_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

from g4f.client import Client
client = Client()

# Test a simple completion
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # This will be mapped by gpt4free to one of its providers, but we want to use our endpoint
    messages=[{"role": "user", "content": "Say hello in one word"}],
    max_tokens=10
)
print("Response:", response.choices[0].message.content)
