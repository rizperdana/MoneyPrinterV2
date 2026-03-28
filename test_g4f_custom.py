import os
# Set the environment variables for the openai provider (used by gpt4free)
os.environ["OPENAI_API_BASE"] = "http://localhost:8317/v1"
os.environ["OPENAI_API_KEY"] = "sk-dIMp6qoD0oWyMvswe"

from g4f.client import Client
client = Client()

# We can try to specify the provider, but let's see if it picks up the env vars by default.
# According to g4f documentation, the openai provider uses these env vars.
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # This is just a placeholder; the actual model is selected by the provider
    messages=[{"role": "user", "content": "Say hello in one word"}],
    max_tokens=10
)
print("Response:", response.choices[0].message.content)
