import os
# Set the environment variables for the OpenAI API
os.environ["OPENAI_API_BASE"] = "http://localhost:8317/v1"
os.environ["OPENAI_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

from g4f.client import Client
from g4f.Provider.needs_auth.OpenaiAccount import OpenaiAccount

client = Client(provider=OpenaiAccount)

response = client.chat.completions.create(
    model="arcee-ai/trinity-large-preview:free",  # We know this model exists
    messages=[{"role": "user", "content": "Say hello in one word"}],
    max_tokens=10
)
print("Response:", response.choices[0].message.content)
