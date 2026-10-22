"""Fixed provider policies bind consent, model identity, and request accounting."""

from dataclasses import dataclass

from app.core.config import Settings
from app.documents.embeddings import EMBEDDING_MODEL, OpenAIEmbeddings
from app.documents.gemini import GEMINI_MODEL, GeminiEmbeddings


@dataclass(frozen=True)
class EmbeddingPolicy:
    name: str
    label: str
    model: str
    disclosure: str
    query_disclosure: str
    batch_size: int
    document_prefix: str = ""
    query_prefix: str = ""


OPENAI = EmbeddingPolicy(
    "openai",
    "OpenAI",
    EMBEDDING_MODEL,
    "paper-embeddings-v1",
    "paper-query-embeddings-v1",
    32,
)
GEMINI = EmbeddingPolicy(
    "gemini",
    "Google Gemini",
    GEMINI_MODEL,
    "paper-gemini-v1",
    "paper-query-gemini-v1",
    1,
    "title: none | text: ",
    "task: search result | query: ",
)


def policy(settings: Settings) -> EmbeddingPolicy:
    return GEMINI if settings.document_embedding_provider == "gemini" else OPENAI


def configured(settings: Settings) -> bool:
    return bool(
        settings.gemini_api_key
        if policy(settings) == GEMINI
        else settings.openai_api_key
    )


def create_embedder(settings: Settings, *, query: bool = False) -> OpenAIEmbeddings:
    if policy(settings) == GEMINI:
        return GeminiEmbeddings(settings, query=query)
    return OpenAIEmbeddings(settings)
