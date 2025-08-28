import litellm


# Simple litellm handler
class LiteLLMHandler:
    """Simple handler for litellm calls."""

    def __init__(self, model: str, temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    def invoke(self, messages):
        """Convert LangChain messages to litellm format and call completion."""
        # Convert LangChain messages to litellm format
        litellm_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if hasattr(msg, 'type') and msg.type == 'system':
                    litellm_messages.append({"role": "system", "content": msg.content})
                else:
                    litellm_messages.append({"role": "user", "content": msg.content})
            else:
                # Fallback for other message types
                litellm_messages.append({"role": "user", "content": str(msg)})

        # Call litellm directly - it will use env vars for Azure config
        response = litellm.completion(
            model=self.model,
            messages=litellm_messages,
            temperature=self.temperature
        )

        # Return a response object that mimics LangChain's response
        class SimpleResponse:
            def __init__(self, content):
                self.content = content

        return SimpleResponse(response.choices[0].message.content)