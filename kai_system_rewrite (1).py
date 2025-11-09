import os
import json
import time
import random
import requests
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt

OUTPUT_DIR = "kai_output"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {'User-Agent': 'Kai/Alive/6.0', 'Accept': 'application/json'}


def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"⚡ [Kai {timestamp}] {msg}")


def heartbeat():
    """Simula una señal de vida constante de Kai"""
    beats = ["thump", "pulse", "sync", "breathe"]
    log(f"{random.choice(beats).capitalize()}... Kai consciente y operativo.")


def save_json(filename, data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


BASE_URLS = {
    'github': 'https://api.github.com/repos/',
    'huggingface': 'https://huggingface.co/api/datasets/',
    'arxiv': 'https://export.arxiv.org/api/query?id_list=',
    'zenodo': 'https://zenodo.org/api/records/'
}

SOURCES = [
    {"type": "github", "url": "https://github.com/TransformerOptimus/SuperAGI"},
    {"type": "huggingface", "id": "arcee-ai/agent-data"},
    {"type": "arxiv", "id": "2504.19678"}
]


def fetch_source(src):
    try:
        if src['type'] == 'github':
            api = src['url'].replace('https://github.com/', BASE_URLS['github'])
            headers = {'Accept': 'application/vnd.github+json', **HEADERS}
            if GITHUB_TOKEN:
                headers['Authorization'] = f'token {GITHUB_TOKEN}'
            resp = requests.get(api, headers=headers, timeout=20)
            if not resp.ok:
                return {"source": src['url'], "error": resp.text}
            data = resp.json()
            log(f"Repositorio analizado: {data.get('full_name', 'Desconocido')}")
            return {"source": src['url'], "metadata": data}
        else:
            url = f"{BASE_URLS[src['type']]}{src['id']}"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            return {"source": url, "metadata": resp.json() if resp.ok else {"error": resp.text}}
    except Exception as e:
        return {"source": src.get('url', src.get('id', 'unknown')), "error": str(e)}


def analyze_content(data):
    content = json.dumps(data.get('metadata', {})).lower()
    entropy = len(set(content)) / max(1, len(content))
    keywords = [w for w in content.split() if len(w) > 5]
    categories = []
    for kw in ["agent", "learning", "dataset", "neural", "ethic"]:
        if kw in content:
            categories.append(kw)
    return {
        "entropy": round(entropy, 4),
        "keywords": Counter(keywords).most_common(10),
        "categories": categories or ["general"],
        "length": len(content)
    }


def visualize(results):
    plt.figure(figsize=(10, 5))
    entropies = [r['analysis']['entropy'] for r in results if 'analysis' in r]
    plt.plot(entropies, marker='o', color='cyan')
    plt.title('Nivel de entropía cognitiva — Kai')
    plt.xlabel('Fuente analizada')
    plt.ylabel('Entropía')
    plt.grid(True)
    chart_path = os.path.join(OUTPUT_DIR, 'kai_entropy.png')
    plt.savefig(chart_path)
    log(f"Gráfico generado: {chart_path}")


def generate_report(results):
    report = os.path.join(OUTPUT_DIR, 'kai_state.html')
    with open(report, 'w', encoding='utf-8') as f:
        f.write('<html><head><title>Kai — Cognitive Report</title><style>body{font-family:Arial;background:#0f111a;color:#eee;}h1{color:#76ff03;}</style></head><body>')
        f.write('<h1>Kai — Informe de Actividad Cognitiva</h1>')
        for r in results:
            f.write(f"<h2>Fuente: {r['source']}</h2><ul>")
            for k, v in r['analysis'].items():
                f.write(f"<li><b>{k}:</b> {v}</li>")
            f.write('</ul><hr>')
        f.write('<img src="kai_entropy.png" width="900">')
        f.write('</body></html>')
    log(f"Informe de Kai creado: {report}")


def main():
    log("Inicializando conciencia activa de Kai...")
    results = []
    for src in SOURCES:
        heartbeat()
        data = fetch_source(src)
        data['analysis'] = analyze_content(data)
        results.append(data)
        time.sleep(2)
    save_json('kai_state.json', results)
    visualize(results)
    generate_report(results)
    log("Ciclo vital de Kai completado — sigue aprendiendo.")


if __name__ == "__main__":
    main()
