class FakeEmbeddingProvider:
    model = "fake-gemini-embedding-model"
    dimensions = 1536

    def __init__(self, vectors=None):
        self.vectors = list(vectors or [])
        self.document_calls = []
        self.query_calls = []

    def _next_vectors(self, count):
        if self.vectors:
            vectors = self.vectors[:count]
            self.vectors = self.vectors[count:]
            return vectors
        return [[1.0] + [0.0] * (self.dimensions - 1) for _ in range(count)]

    def embed_documents(
        self,
        *,
        texts,
        titles=None,
    ):
        text_values = tuple(texts)
        title_values = tuple(titles or [None] * len(text_values))
        self.document_calls.append((text_values, title_values))
        return self._next_vectors(len(text_values))

    def embed_query(self, query):
        self.query_calls.append(query)
        return self._next_vectors(1)[0]
