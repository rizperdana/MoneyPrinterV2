import os
import sys
from openai import OpenAI
from g4f.providers.base_provider import AsyncGeneratorProvider
from g4f.typing import Messages, AsyncResult, MediaListType

class CustomOpenAIProvider(AsyncGeneratorProvider):
    """A custom provider that uses an OpenAI-compatible endpoint."""
    
    label = "Custom OpenAI Compatible"
    working = True
    supports_stream = True
    supports_message_history = True
    # We don't set models here; we'll let the user pass any model that the endpoint supports.
    # If the endpoint doesn't support the model, it will return an error from the OpenAI API.

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
        # For simplicity, we'll ignore media and just do text.
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
    from g4f.client import Client
    client = Client(provider=CustomOpenAIProvider)  # Pass the class
    
    # Test a simple completion
    response = client.chat.completions.create(
        model="arcee-ai/trinity-large-preview:free",  # We know this model exists
        messages=[{"role": "user", "content": "Say hello in one word"}],
        max_tokens=10
    )
    print("Response:", response.choices[0].message.content)
