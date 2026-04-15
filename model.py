from sentence_transformers import SentenceTransformer
from sklearn.manifold import TSNE

model = SentenceTransformer("all-mpnet-base-v2")


def encode(sentence_list):
    vectors = model.encode(sentence_list, normalize_embeddings=True)
    return vectors


def embed_2d(X):
    return TSNE(
        n_components=2, learning_rate="auto", init="random", perplexity=3
    ).fit_transform(X)
