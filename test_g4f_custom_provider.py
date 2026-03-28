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
    
    # Class attributes to hold the API base and key
    api_base = None
    api_key = None

    @staticmethod
    async def create_async_generator(
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
            # We create an OpenAI client using the class attributes for base_url and rely on the environment variable for api_key.
            client = OpenAI(
                base_url=CustomOpenAIProvider.api_base
                # api_key is taken from the environment variable OPENAI_API_KEY
            )
            stream_response = client.chat.completions.create(
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
            client = OpenAI(
                base_url=CustomOpenAIProvider.api_base
                # api_key is taken from the environment variable OPENAI_API_KEY
            )
            response = client.chat.completions.create(
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
    
    # Set the environment variable for the OpenAI client
    os.environ["OPENAI_API_KEY"] = api_key
    # Set the class attributes
    CustomOpenAIProvider.api_base = api_base
    # Note: we don't set the api_key class attribute because we are using the environment variable
    
    provider = CustomOpenAIProvider()
    from g4f.client import Client
    client = Client(provider=CustomOpenAIProvider)  # Pass the class
    
    # Test a simple completion
    response = client.chat.completions.create(
        model="arcee-ai/trinity-large-preview:free",  # We know this model exists
        messages=[{"role": "user", "content": "Say hello in one word"}],
        max_tokens=10
    )
    print("Response:", response.choices[0].message.content)
