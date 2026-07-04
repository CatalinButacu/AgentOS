from __future__ import annotations

import hashlib
import math
import os

from agentos.knowledge.lexical import tokenize

_EMBEDDING_DIM = 256


def _local_embedding(text: str) -> list[float]:
    vector = [0.0] * _EMBEDDING_DIM
    for token in tokenize(text):
        index = int(hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest(), 16) % _EMBEDDING_DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


class ModelRouter:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None,
                 api_version: str = "2024-10-21", chat_deployment: str | None = None,
                 embedding_deployment: str | None = None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.chat_deployment = chat_deployment
        self.embedding_deployment = embedding_deployment
        self._client = None

    @classmethod
    def from_env(cls) -> "ModelRouter":
        return cls(endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
                   api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                   chat_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
                   embedding_deployment=os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"))

    @property
    def is_live(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def _client_or_create(self):
        if self._client is None:
            try:
                from openai import AzureOpenAI
            except ImportError as error:
                raise RuntimeError("openai is required for a live ModelRouter") from error
            self._client = AzureOpenAI(azure_endpoint=self.endpoint, api_key=self.api_key,
                                       api_version=self.api_version)
        return self._client

    def complete(self, prompt: str, difficulty: str = "standard") -> str:
        if not self.is_live or not self.chat_deployment:
            return ""
        response = self._client_or_create().chat.completions.create(
            model=self.chat_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0)
        return response.choices[0].message.content or ""

    def embed(self, text: str) -> list[float]:
        if not self.is_live or not self.embedding_deployment:
            return _local_embedding(text)
        response = self._client_or_create().embeddings.create(
            model=self.embedding_deployment, input=text)
        return list(response.data[0].embedding)
