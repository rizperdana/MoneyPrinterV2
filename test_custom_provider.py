import os
import sys
from openai import OpenAI

# We'll create a simple provider that mimics the g4f provider interface
class CustomOpenAIProvider:
    """A custom provider that uses an OpenAI-compatible endpoint."""
    
    # These are required by g4f's provider interface
    working = True
    supports_stream = True
    supports_message_history = True
    
    # You need to set these based on your endpoint's capabilities
    # For now, we'll leave them empty and let g4f handle model mapping?
    # Actually, we need to define what models we support.
    # Since our endpoint has many models, we can say we support all?
    # But g4f expects a list of models. We'll fetch them dynamically?
    # For simplicity, we'll just support a few common ones and let the user specify.
    
    def __init__(self, api_base, api_key):
        self.client = OpenAI(
            base_url=api_base,
            api_key=api_key
        )
    
    # This is the method g4f calls to get a completion
    # We'll implement a non-streaming version for simplicity
    def create_completion(self, model, messages, **kwargs):
        # Convert messages to the format expected by OpenAI
        # g4f messages are a list of dicts with role and content
        # OpenAI expects the same format
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        # Yield chunks if streaming, but we'll just return the whole response
        # For non-streaming, we need to yield the content
        yield response.choices[0].message.content
    
    # For streaming, we'd need to implement create_async_generator
    # but let's keep it simple for now.

# Now, let's try to use this provider with g4f's client by replacing the provider list?
# Actually, g4f's Client allows you to specify a provider.
# We'll try to use our custom provider.

from g4f.client import Client
from g4f.provider import BaseProvider

# We need to make our provider inherit from BaseProvider
from g4f.provider.base_provider import AbstractProvider, AsyncGeneratorProvider
from g4f.typing import Messages, AsyncResult, MediaListType
import asyncio

class CustomOpenAIProvider(AbstractProvider, AsyncGeneratorProvider):
    """A custom provider that uses an OpenAI-compatible endpoint."""
    
    label = "Custom OpenAI Compatible"
    working = True
    supports_stream = True
    supports_message_history = True
    
    # We need to define the models we support. Let's fetch from the endpoint?
    # For now, we'll hardcode a few and hope the user passes the correct model.
    # Alternatively, we can implement get_models to fetch from the endpoint.
    
    def __init__(self, api_base, api_key):
        super().__init__()
        self.client = OpenAI(
            base_url=api_base,
            api_key=api_key
        )
    
    async def create_async_generator(
        self,
        model: str,
        messages: Messages,
        stream: bool = True,
        media: MediaListType = None,
        **kwargs
    ) -> AsyncResult:
        # For simplicity, we'll ignore media and just do text
        # If stream is True, we'll stream; otherwise, we'll yield the whole response.
        if stream:
            # Stream the response
            stream_response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in stream_response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        else:
            # Non-streaming
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
                **kwargs
            )
            yield response.choices[0].message.content

# Now test it
if __name__ == "__main__":
    api_base = "http://localhost:8317/v1"
    api_key = "sk-dIMp6qoD0oWyMvswe"
    
    provider = CustomOpenAIProvider(api_base, api_key)
    client = Client(provider=provider)  # Use only our provider
    
    # Test a simple completion
    response = client.chat.completions.create(
        model="arcee-ai/trinity-large-preview:free",  # We know this model exists
        messages=[{"role": "user", "content": "Say hello in one word"}],
        max_tokens=10
    )
    print("Response:", response.choices[0].message.content)
