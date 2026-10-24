"""RAG errors. Messages must stay free of API keys and full user prompts."""


class DocumentValidationError(Exception):
    """A corpus file is missing required metadata or is otherwise unusable."""


class CorpusPathError(Exception):
    """A path escapes the configured corpus root."""


class ModelMismatchError(Exception):
    """The index was built with a different embedding model or vector size."""


class IncompleteIndexError(Exception):
    """A collection is not marked ready, so it cannot become active."""


class StoreError(Exception):
    """The vector store could not complete a read or write."""


class EmbeddingDependencyError(Exception):
    """The local embedding runtime is not installed."""
