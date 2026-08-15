import base64
import json
import os
import shutil
import tempfile
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)
HF_SPACE = os.environ.get("QWEN_HF_SPACE", "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast")
HF_TOKEN = os.environ.get("HF_TOKEN") or None

LORAS = [
    "Multiple-Angles", "Photo-to-Anime", "Anime-V2", "Light-Migration",
    "Upscaler", "Style-Transfer", "Manga-Tone", "Anything2Real",
    "Fal-Multiple-Angles", "Polaroid-Photo", "Unblur-Anything",
    "Midnight-Noir-Eyes-Spotlight", "Hyper-Realistic-Portrait",
    "Ultra-Realistic-Portrait", "Pixar-Inspired-3D", "Noir-Comic-Book",
    "Any-light", "Studio-DeLight", "Cinematic-FlatLog"
]

app = FastAPI(title="Qwen Image Edit Mobile")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS)), name="outputs")
_client = None


def get_client():
    global _client
    if _client is None:
        kwargs = {}
        if HF_TOKEN:
            kwargs["hf_token"] = HF_TOKEN
        _client = Client(HF_SPACE, **kwargs)
    return _client


def file_to_data_url(path: str) -> str:
    suffix = Path(path).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def extract_seed(value, fallback):
    if isinstance(value, dict) and isinstance(value.get("seed"), (int, float)):
        return int(value["seed"])
    if isinstance(value, (list, tuple)) and len(value) > 1 and isinstance(value[1], (int, float)):
        return int(value[1])
    return int(fallback)


def find_image(value):
    if value is None:
        return None
    if isinstance(value, str):
        if value.startswith(("data:image/", "http://", "https://")):
            return value
        if os.path.exists(value):
            return value
        return None
    if isinstance(value, dict):
        if "image" in value:
            found = find_image(value["image"])
            if found:
                return found
        for key in ("path", "url"):
            found = find_image(value.get(key))
            if found:
                return found
        for key in ("data", "value", "result"):
            found = find_image(value.get(key))
            if found:
                return found
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = find_image(item)
            if found:
                return found
    return None


def localize_image(value):
    image = find_image(value)
    if not image:
        raise RuntimeError(f"No image found in remote result: {type(value).__name__}")
    if image.startswith(("data:image/", "http://", "https://")):
        return image
    src = Path(image)
    ext = src.suffix if src.suffix else ".png"
    name = f"qwen_{uuid.uuid4().hex}{ext}"
    shutil.copy2(src, OUTPUTS / name)
    return f"/outputs/{name}"


def call_remote(paths, prompt, lora, seed, randomize, guidance, steps):
    c = get_client()
    hf_files = [handle_file(p) for p in paths]
    attempts = []

    # Newer custom Server API used by the GitHub repository.
    try:
        b64_json = json.dumps([file_to_data_url(p) for p in paths])
        out = c.predict(
            images_b64_json=b64_json,
            prompt=prompt,
            lora_adapter=lora,
            seed=seed,
            randomize_seed=randomize,
            guidance_scale=guidance,
            steps=steps,
            api_name="/edit_image",
        )
        return out, "edit_image"
    except Exception as e:
        attempts.append(f"/edit_image: {e}")

    # Multi-image Gradio API seen in recent Qwen edit Spaces.
    try:
        out = c.predict(
            images=[{"image": f} for f in hf_files],
            prompt=prompt,
            lora_adapter=lora,
            seed=seed,
            randomize_seed=randomize,
            guidance_scale=guidance,
            steps=steps,
            api_name="/infer",
        )
        return out, "infer-multi"
    except Exception as e:
        attempts.append(f"/infer multi: {e}")

    # Classic single-image API used by earlier versions of the Space.
    try:
        out = c.predict(
            input_image=hf_files[0],
            prompt=prompt,
            lora_adapter=lora,
            seed=seed,
            randomize_seed=randomize,
            guidance_scale=guidance,
            steps=steps,
            api_name="/infer",
        )
        return out, "infer-single"
    except Exception as e:
        attempts.append(f"/infer single: {e}")

    # Positional fallback for Gradio versions that do not expose parameter names.
    try:
        out = c.predict(hf_files[0], prompt, lora, seed, randomize, guidance, steps, api_name="/infer")
        return out, "infer-positional"
    except Exception as e:
        attempts.append(f"/infer positional: {e}")

    raise RuntimeError("Remote Space API did not match any supported layout.\n" + "\n".join(attempts))


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "index.html").read_text(encoding="utf-8")


@app.get("/api/config")
def config():
    return {"space": HF_SPACE, "loras": LORAS, "default_lora": "Photo-to-Anime"}


@app.get("/api/health")
def health():
    return {"ok": True, "space": HF_SPACE}


@app.post("/api/edit")
async def edit(
    images: list[UploadFile] = File(...),
    prompt: str = Form(...),
    lora: str = Form("Photo-to-Anime"),
    seed: int = Form(0),
    randomize: bool = Form(True),
    guidance: float = Form(1.0),
    steps: int = Form(4),
):
    if not images:
        return JSONResponse({"error": "Sube al menos una imagen."}, status_code=400)
    if not prompt.strip():
        return JSONResponse({"error": "Escribe una instrucción de edición."}, status_code=400)

    tmp = Path(tempfile.mkdtemp(prefix="qwen_mobile_"))
    paths = []
    try:
        for i, upload in enumerate(images):
            suffix = Path(upload.filename or "image.png").suffix or ".png"
            path = tmp / f"input_{i}{suffix}"
            path.write_bytes(await upload.read())
            paths.append(str(path))

        result, api_used = call_remote(paths, prompt.strip(), lora, seed, randomize, guidance, steps)
        return {
            "image": localize_image(result),
            "seed": extract_seed(result, seed),
            "api": api_used,
            "space": HF_SPACE,
        }
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "detail": traceback.format_exc(limit=4)},
            status_code=500,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "7860")))
