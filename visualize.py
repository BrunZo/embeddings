import argparse
from pathlib import Path

import chromadb
from flask import Flask, abort, render_template, request

from config.constants import COLLECTION_NAME, DEFAULT_DB_PATH
from embedding.query import retrieve
from render import obsidian


app = Flask(__name__)
root_dir: Path = Path(".")
collection = None  # set in __main__


@app.route("/")
def index():
    paths, _ = _all_paths_and_stems()
    tree = build_tree(paths)
    return render_template("index.html", tree=tree)


@app.route("/search", methods=["GET", "POST"])
def search():
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("q", "").strip()
        if query:
            results = retrieve(query, 10, collection)
    return render_template("search.html", query=query, results=results)


@app.route("/visualize/<path:filepath>")
def visualize(filepath):
    res = collection.get(
        where={"path": filepath},
        include=["documents", "metadatas"],
    )
    if not res["ids"]:
        abort(404)

    rows = sorted(
        zip(res["documents"], res["metadatas"]),
        key=lambda dm: dm[1]["chunk_idx"],
    )
    points = [
        {
            "text": doc,
            "x": meta["tsne_x"],
            "y": meta["tsne_y"],
            "block_indices": [int(b) for b in meta["block_indices"].split(",") if b],
        }
        for doc, meta in rows
    ]

    target = root_dir / filepath
    if not target.is_file():
        abort(404)
    fm, blocks = obsidian.parse(target.read_text())

    _, stem_map = _all_paths_and_stems()
    html = obsidian.to_html(fm, blocks, lambda t: stem_map.get(t))

    return render_template(
        "visualize.html",
        filename=filepath,
        content_html=html,
        points=points,
    )


def _all_paths_and_stems() -> tuple[list[str], dict[str, str]]:
    res = collection.get(include=["metadatas"])
    paths: set[str] = set()
    stem_map: dict[str, str] = {}
    for meta in res["metadatas"]:
        path = meta["path"]
        paths.add(path)
        stem_map.setdefault(meta["stem"], path)
    return sorted(paths), stem_map


def build_tree(paths: list[str]) -> dict:
    """Build a nested {dirs: {name: subtree}, files: [(name, full_path)]} tree."""
    root = {"dirs": {}, "files": []}
    for p in paths:
        parts = p.split("/")
        node = root
        for d in parts[:-1]:
            node = node["dirs"].setdefault(d, {"dirs": {}, "files": []})
        node["files"].append((parts[-1], p))
    return root


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("directory", help="Directory containing .md files")
    ap.add_argument("--db-path", dest="db_path", type=Path, default=Path(DEFAULT_DB_PATH))
    ap.add_argument("--port", type=int, default=5000)
    args = ap.parse_args()

    root_dir = Path(args.directory).resolve()
    client = chromadb.PersistentClient(path=str(args.db_path))
    collection = client.get_collection(COLLECTION_NAME)

    app.run(debug=True, port=args.port)
