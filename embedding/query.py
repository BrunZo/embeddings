import argparse
from pathlib import Path

import chromadb

from config.constants import COLLECTION_NAME, DEFAULT_DB_PATH
from embedding import encode


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--query", required=True, type=str)
    ap.add_argument("--db-path", dest="db_path", type=Path, default=Path(DEFAULT_DB_PATH))
    return ap.parse_args()


def main():
    args = parse_args()

    client = chromadb.PersistentClient(path=str(args.db_path))
    collection = client.get_collection(COLLECTION_NAME)

    results = retrieve(args.query, 10, collection)
    for i, result in enumerate(results):
        text = result["text"][:50]
        print(f" {i+1}. (score={result['score']}) {result['path']} -- {text}")


def retrieve(query: str, n_results: int, collection) -> list[dict]:
    embedding = encode([query])
    results = collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    out = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({
            "text": text,
            "path": meta["path"],
            "stem": meta["stem"],
            "score": round(1 - dist, 3),
        })
    return out


if __name__ == "__main__":
    main()
