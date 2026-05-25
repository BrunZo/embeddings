# Dependencies

Install all with:

```bash
pip install -r requirements.txt
```

| Package                 | Needed for                                                        |
|-------------------------|-------------------------------------------------------------------|
| `sentence-transformers` | `encode()` — turns text into vectors (pulls in `torch`).          |
| `scikit-learn`          | `embed_2d()` — t-SNE projection to 2D.                            |
| `chromadb`              | `indexer.py` — persistent vector store (imported at module load). |
| `python-dotenv`         | `indexer.py` — loads `.env` (imported at module load).            |
| `pyyaml`                | `render/obsidian.py` — parses note frontmatter.                   |
| `flask`                 | `visualize.py` — web server for browsing embeddings.             |
| `matplotlib`            | `visualize.py` / plotting embeddings.                            |

## Just want to encode text?

`encode()` itself only needs `sentence-transformers` and `scikit-learn`. But
importing `chunk_blocks` from `indexer.py` pulls in `chromadb` and
`python-dotenv` at module load, so those are required too if you use the
chunker.
