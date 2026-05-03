import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.manifold import TSNE

from config.constants import EMBEDDING_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def encode(sentences):
    return _get_model().encode(sentences, normalize_embeddings=True).tolist()


def embed_2d(X):
    return TSNE(
        n_components=2,
        learning_rate="auto",
        init="random",
        perplexity=2,
    ).fit_transform(np.asarray(X))
