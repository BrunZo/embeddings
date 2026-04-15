import json
import argparse
from pathlib import Path

from model import embed_2d, encode

REFERENCE_WORDS = ["muerte", "vida", "conciencia", "entendimiento"]


def visualize_document(path: Path):
    with open(path) as f:
        payload = f.read()

    sentences = [s.strip() for s in payload.split(". ") if s.strip()]
    all_items = sentences + REFERENCE_WORDS

    vectors = encode(all_items)
    coords = embed_2d(vectors)

    points = [
        {
            "text": item,
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "is_reference": i >= len(sentences),
        }
        for i, item in enumerate(all_items)
    ]

    out = path.with_suffix(".html")
    out.write_text(_build_html(sentences, points))
    print(f"Saved: {out}")


def _build_html(sentences, points):
    data_json = json.dumps(points)
    sentence_spans = "\n".join(
        f'<span class="sentence" data-index="{i}">{s}.</span>'
        for i, s in enumerate(sentences)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sentence Embeddings</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ display: flex; height: 100vh; font-family: system-ui, sans-serif; background: #fafafa; }}

  #text-panel {{
    width: 40%;
    padding: 28px 24px;
    overflow-y: auto;
    border-right: 1px solid #e0e0e0;
    background: #fff;
    font-size: 15px;
    line-height: 1.9;
    color: #222;
  }}

  .sentence {{
    cursor: default;
    border-radius: 3px;
    padding: 1px 2px;
    transition: background 0.12s;
  }}
  .sentence:hover {{ background: #ffe082; }}
  .sentence.active  {{ background: #ffb300; color: #000; }}

  #chart-panel {{ flex: 1; position: relative; }}
  #chart {{ width: 100%; height: 100%; }}
</style>
</head>
<body>

<div id="text-panel">{sentence_spans}</div>
<div id="chart-panel"><div id="chart"></div></div>

<script>
const POINTS = {data_json};
const nSentences = POINTS.filter(p => !p.is_reference).length;

const DEFAULT_COLOR    = '#5b9bd5';
const HIGHLIGHT_COLOR  = '#e74c3c';
const REF_COLOR        = '#aaaaaa';

function colorArray(activeIdx) {{
  return POINTS.map((p, i) => {{
    if (p.is_reference) return REF_COLOR;
    return (i === activeIdx) ? HIGHLIGHT_COLOR : DEFAULT_COLOR;
  }});
}}

const trace = {{
  x: POINTS.map(p => p.x),
  y: POINTS.map(p => p.y),
  mode: 'markers',
  type: 'scatter',
  text: POINTS.map(p => p.text),
  hoverinfo: 'text',
  marker: {{
    color: colorArray(-1),
    size: POINTS.map(p => p.is_reference ? 11 : 7),
    line: {{ width: 0 }},
  }},
}};

const layout = {{
  margin: {{ t: 16, r: 16, b: 16, l: 16 }},
  paper_bgcolor: '#fafafa',
  plot_bgcolor:  '#fafafa',
  xaxis: {{ showgrid: false, zeroline: false, showticklabels: false }},
  yaxis: {{ showgrid: false, zeroline: false, showticklabels: false }},
  hovermode: 'closest',
}};

Plotly.newPlot('chart', [trace], layout, {{ responsive: true }});

const chartDiv  = document.getElementById('chart');
const sentenceEls = Array.from(document.querySelectorAll('.sentence'));

function clearActive() {{
  sentenceEls.forEach(el => el.classList.remove('active'));
}}

// Chart hover -> highlight sentence
chartDiv.on('plotly_hover', (evt) => {{
  const idx = evt.points[0].pointIndex;
  if (POINTS[idx].is_reference) return;
  clearActive();
  sentenceEls[idx].classList.add('active');
  sentenceEls[idx].scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
}});

chartDiv.on('plotly_unhover', () => clearActive());

// Sentence hover -> highlight point on chart
sentenceEls.forEach((el, i) => {{
  el.addEventListener('mouseenter', () => {{
    Plotly.restyle('chart', {{ 'marker.color': [colorArray(i)] }}, [0]);
  }});
  el.addEventListener('mouseleave', () => {{
    Plotly.restyle('chart', {{ 'marker.color': [colorArray(-1)] }}, [0]);
  }});
}});
</script>

</body>
</html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to the text file to visualize")
    args = ap.parse_args()
    visualize_document(Path(args.path))
