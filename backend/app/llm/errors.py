"""Provider-neutral LLM errors.

Messages are safe to show to users: they must not include API keys or raw
provider payloads.
"""


class LLMError(Exception):
    """Raised when a text-generation provider cannot return usable text."""
