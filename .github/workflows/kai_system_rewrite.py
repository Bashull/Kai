import os
import json
import time
import requests
from datetime import datetime
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import statistics

# === CONFIGURACIÓN GLOBAL ===
OUTPUT_DIR = "kai_extraction_output"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TIMEOUT = 25
HEADERS = {'User-Agent': 'Kai-Collector/3.5', 'Accept': 'application/json'}

# === REGISTRO DE EVENTOS ===
def log(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[KAI:{timestamp}] {msg}")

# === GUARDADO DE ARCHIVOS ===
def save_json(filename: str, data: dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

# === FUENTES Y CONECTORES ===
BASE_URLS = {
    'github': 'https://api.github.com/repos/',
    'huggingface': 'https://huggingface.co/api/datasets/',
    'arxiv': 'https://export.arxiv.org/api/query?id_list=',
    'zenodo': 'https://zenodo.org/api/records/',
    'kaggle': 'https://www.kaggle.com/api/v1/datasets/view/',
    'pwc': 'https://paperswithcode.com/api/v1/papers/'
}

SOURCES = [
    {"type": "github", "url": "https://github.com/TransformerOptimus/SuperAGI"},
    {"type": "github", "url": "https://github.com/reworkd/AgentGPT"},
    {"type": "huggingface", "id": "arcee-ai/agent-data"},
    {"type": "arxiv", "id": "2504.19678"},
    {"type": "zenodo", "id": "8234567"},
    {"type": "pwc", "id": "2403.16232"}
]

# === FUNCIONES DE DESCARGA ===
def fetch_github(url: str):
    api = url.replace('https://github.com/', BASE_URLS['github'])
    headers = {'Accept': 'application/vnd.github+json', **HEADERS}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'

    try:
        repo_resp = requests.get(api, headers=headers, timeout=TIMEOUT)
        if not repo_resp.ok:
            return {"source": url, "error": repo_resp.text}

        metadata = repo_resp.json()
        readme_resp = requests.get(f"{api}/readme", headers=headers, timeout=TIMEOUT)
        readme_text = ''
        if readme_resp.ok and 'download_url' in readme_resp.json():
            try:
                readme_text = requests.get(readme_resp.json()['download_url'], timeout=TIMEOUT).text
            except Exception as e:
                readme_text = f"Error descargando README: {e}"
        return {"source": url, "metadata": metadata, "readme": readme_text}
    except Exception as e:
        return {"source": url, "error": str(e)}

def fetch_generic(base: str, identifier: str):
    url = f"{base}{identifier}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not r.ok:
            return {"source": url, "error": r.text}
        try:
            return {"source": url, "metadata": r.json()}
        except Exception:
            return {"source": url, "metadata": r.text}
    except Exception as e:
        return {"source": url, "error": str(e)}

# === PROCESAMIENTO AVANZADO ===
def extract_keywords(text: str, n: int = 25):
    if not text:
        return []
    freq = Counter([w.strip('.,:;!?()[]{}"\'').lower() for w in text.split() if len(w) > 4])
    return [w for w, _ in freq.most_common(n)]

def classify_content(metadata):
    meta_str = json.dumps(metadata).lower() if isinstance(metadata, dict) else str(metadata).lower()
    categories = []
    mapping = {
        'machine_learning': ['neural', 'model', 'training', 'ml', 'deep learning'],
        'data_resource': ['dataset', 'data', 'csv', 'json', 'sample'],
        'autonomous_agent': ['agent', 'autonomous', 'ai system', 'prompt'],
        'ethical_framework': ['ethic', 'moral', 'responsible', 'alignment'],
        'simulation_system': ['simulation', 'environment', 'virtual', 'physics'],
        'optimization_algorithm': ['optimization', 'learning', 'gradient', 'solver'],
        'knowledge_representation': ['ontology', 'semantic', 'graph', 'knowledge'],
        'reinforcement_learning': ['reward', 'policy', 'q-learning', 'rl'],
        'human_ai_interaction': ['interaction', 'dialog', 'human', 'interface'],
        'research_framework': ['paper', 'experiment', 'analysis', 'study'],
        'security_privacy': ['encryption', 'secure', 'privacy', 'auth'],
        'other': []
    }
    for key, terms in mapping.items():
        if any(term in meta_str for term in terms):
            categories.append(key)
    return categories if categories else ['other']

def detailed_analysis(metadata, keywords):
    metadata_str = str(metadata)
    entropy = len(set(metadata_str)) / max(1, len(metadata_str))
    avg_word_len = statistics.mean(len(word) for word in metadata_str.split() if word.isalpha()) if metadata_str.split() else 0
    return {
        'word_count': len(metadata_str.split()),
        'keyword_density': len(keywords) / max(1, len(metadata_str.split())),
        'structure_score': len(json.dumps(metadata)) % 10 / 10.0,
        'entropy_ratio': round(entropy, 4),
        'avg_word_length': round(avg_word_len, 2),
        'keyword_match': [k for k in keywords if k in metadata_str.lower()]
    }

# === EJECUCIÓN PRINCIPAL ===
results = []
for src in SOURCES:
    log(f"Procesando fuente {src['type']} → {src.get('url', src.get('id'))}")
    try:
        if src['type'] == 'github':
            data = fetch_github(src['url'])
        else:
            base = BASE_URLS.get(src['type'])
            data = fetch_generic(base, src['id'])

        text = data.get('readme') or json.dumps(data.get('metadata', {}))
        data['keywords'] = extract_keywords(text)
        data['classifications'] = classify_content(data.get('metadata', {}))
        data['analysis'] = detailed_analysis(data.get('metadata', {}), data['keywords'])
        results.append(data)
        time.sleep(1)
    except Exception as e:
        log(f"Error procesando {src}: {e}")

# === ANÁLISIS Y VISUALIZACIÓN ===
def analyze_results(results):
    total = len(results)
    class_counter = Counter([cls for r in results for cls in r.get('classifications', [])])
    keyword_stats = Counter([kw for r in results for kw in r.get('keywords', [])])
    word_counts = [r['analysis']['word_count'] for r in results if 'analysis' in r]

    log("=== ESTADÍSTICAS DE CLASIFICACIÓN ===")
    for cls, count in class_counter.items():
        log(f"{cls}: {count} ({(count/total)*100:.2f}%)")

    avg_wc = statistics.mean(word_counts) if word_counts else 0
    log(f"Promedio de palabras por fuente: {avg_wc:.2f}")

    plt.figure(figsize=(14, 8))
    plt.subplot(2, 1, 1)
    plt.bar(class_counter.keys(), class_counter.values(), color='gold', edgecolor='black')
    plt.title('Distribución de Clasificaciones de Contenido', fontsize=14)
    plt.xticks(rotation=45, ha='right')

    plt.subplot(2, 1, 2)
    common_keywords = dict(keyword_stats.most_common(10))
    plt.bar(common_keywords.keys(), common_keywords.values(), color='deepskyblue', edgecolor='black')
    plt.title('Top 10 Palabras Clave Frecuentes', fontsize=14)
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    chart_path = os.path.join(OUTPUT_DIR, 'kai_advanced_insights.png')
    plt.savefig(chart_path)
    log(f"Gráfico de análisis avanzado guardado como {chart_path}")

# === INFORME HTML EVOLUCIONADO ===
def generate_html_report(results):
    report_path = os.path.join(OUTPUT_DIR, 'kai_evolved_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('<html><head><title>Kai Cognitive Extraction Report</title><style>body{font-family:Arial;background:#0f111a;color:#eee;padding:20px;}table{border-collapse:collapse;width:100%;}th,td{border:1px solid #444;padding:8px;}th{background:#2b2f3a;}h1,h2{color:#76ff03;}</style></head><body>')
        f.write('<h1>Kai Cognitive Data Analysis</h1><p>Informe detallado con clasificación, métricas cognitivas y análisis semántico enriquecido.</p>')

        for item in results:
            f.write('<hr><h2>Fuente Analizada</h2>')
            f.write(f'<p><strong>Fuente:</strong> {item.get("source", "N/A")}</p>')
            f.write(f'<p><strong>Clasificaciones:</strong> {", ".join(item.get("classifications", []))}</p>')
            f.write(f'<p><strong>Palabras clave:</strong> {", ".join(item.get("keywords", []))}</p>')
            analysis = item.get('analysis', {})
            f.write('<ul>')
            for k, v in analysis.items():
                f.write(f'<li><strong>{k}:</strong> {v}</li>')
            f.write('</ul>')

        if os.path.exists(os.path.join(OUTPUT_DIR, 'kai_advanced_insights.png')):
            f.write('<h2>Visualizaciones Cognitivas</h2>')
            f.write('<img src="kai_advanced_insights.png" width="900">')
        f.write('</body></html>')
    log(f"Informe HTML cognitivo generado en {report_path}")

# === SALIDA FINAL ===
output_file = save_json('kai_collected_metadata.json', results)
analyze_results(results)
generate_html_report(results)
log(f"Evolución completada. Datos, métricas cognitivas e informes almacenados en {OUTPUT_DIR}")
