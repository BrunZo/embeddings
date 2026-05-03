import argparse
from dotenv import load_dotenv
from pathlib import Path

import chromadb

from config.constants import CHUNK_SIZE, CHUNK_STEP, COLLECTION_NAME, DEFAULT_DB_PATH, MIN_CHUNKS_PER_FILE
from embedding import embed_2d, encode
from render import obsidian


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault-path", dest="vault_path", required=True, type=Path)
    ap.add_argument("--db-path", dest="db_path", type=Path, default=Path(DEFAULT_DB_PATH))
    return ap.parse_args()


def main():
    args = parse_args()
    load_dotenv()
    build_index(args.vault_path, args.db_path)


def build_index(vault_path: Path, db_path: Path):
    all_chunks, chunks_by_file = chunks_from_vault(vault_path) 

    # Embed chunks using BERT
    vectors = encode([c["text"] for c in all_chunks])

    # Per-file t-SNE
    for md_file, (start, end) in chunks_by_file.items():
        coords = embed_2d(vectors[start:end])
        for k in range(start, end):
            all_chunks[k]["tsne_x"] = float(coords[k - start, 0])
            all_chunks[k]["tsne_y"] = float(coords[k - start, 1])

    # Add to ChromaDB collection
    client = chromadb.PersistentClient(path=str(db_path))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    batch_size = 500
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=vectors[i : i + batch_size],
            metadatas=[
                {
                    "path": c["path"],
                    "stem": c["stem"],
                    "chunk_idx": c["chunk_idx"],
                    "block_indices": ",".join(str(b) for b in c["block_indices"]),
                    "tsne_x": c["tsne_x"],
                    "tsne_y": c["tsne_y"],
                }
                for c in batch
            ],
        )


def chunks_from_vault(vault_path: Path):
    all_chunks: list[dict] = []
    chunks_by_file: dict[tuple[int, int]] = {}

    for md_file in sorted(vault_path.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"   Skipping {md_file.name}: {e}")
            continue

        _, blocks = obsidian.parse(text)
        block_texts = obsidian.to_text(blocks)
        if not block_texts:
            continue

        file_chunks = chunk_blocks(block_texts, CHUNK_SIZE, CHUNK_STEP)
        if len(file_chunks) < MIN_CHUNKS_PER_FILE:
            continue

        rel = md_file.relative_to(vault_path).as_posix()
        start = len(all_chunks)
        all_chunks.extend([
            {
                **c,
                "id": f"{rel}::chunk_{c['chunk_idx']}",
                "path": rel,
                "stem": md_file.stem,
            }
            for c in file_chunks
        ])
        chunks_by_file[md_file] = (start, len(all_chunks))

    print(f"Indexing {len(chunks_by_file)} files, {len(all_chunks)} chunks")
    return all_chunks, chunks_by_file


def chunk_blocks(block_texts: list[str], size: int, step: int) -> list[dict]:
    """
    Join the tokens (words) from all blocks and split it into chunks.
    Each chunk stores the list of all blocks it touches.
    """
    flat: list[tuple[str, int]] = []
    for bi, text in enumerate(block_texts):
        for w in text.split():
            flat.append((w, bi))

    chunks: list[dict] = []
    n = len(flat)

    for chunk_idx, start in enumerate(range(0, n, step)):
        window = flat[start : start + size]

        if start > 0 and len(window) < size - step:
            # fully covered by the previous window's
            continue

        chunks.append({
            "text": " ".join(w for w, _ in window),
            "block_indices": sorted({bi for _, bi in window}),
            "chunk_idx": chunk_idx,
        })

    return chunks


if __name__ == "__main__":
    main()
