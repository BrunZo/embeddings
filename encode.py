import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt

from model import embed_2d, encode


def read_file(path: Path):
    with open(path, mode="r") as file:
        payload = file.read()
        payload = payload.lower()
    return payload


def encode_document(payload: str):
    words = re.sub(r"[^a-zA-Z\/]", "", payload).split(" ")
    sentences = [s.strip() for s in payload.split(".")]

    X = encode(sentences + words)
    X_embd = embed_2d(X)
    X, Y = X_embd[:, 0], X_embd[:, 1]

    def _strip(s: str) -> str:
        return s[:10] if len(s) > 10 else s

    ax = plt.axes()
    ax.scatter(X, Y)
    for txt, x, y in zip(sentences, X, Y):
        ax.annotate(_strip(txt), (x, y))

    plt.savefig("out.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    payload = read_file(args.path)
    encode_document(payload)
