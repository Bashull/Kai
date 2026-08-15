import { Client, handle_file } from "https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js";
import { createSession, currentItem, recordAttempt, chooseCandidate, skipItem } from "./state.mjs";

const SPACE = "Bashull/Qwen-Image-Edit-2511-LoRAs-Fast";
const SESSION_KEY = "kai-edit-v2-session";
const DB_NAME = "kai-edit-v2";
const DB_VERSION = 1;
const $ = (id) => document.getElementById(id);

let client = null;
let session = null;
let selectedFiles = [];
let currentPair = null;
let outputDirectory = null;
let deferredInstall = null;
let busy = false;

function setStatus(text, kind = "") {
  $("status").className = `status ${kind}`;
  $("status").textContent = text;
}
function setReviewStatus(text, kind = "") {
  $("reviewStatus").className = `status ${kind}`;
  $("reviewStatus").textContent = text;
}
function imageKey(file, index) {
  const rel = file.webkitRelativePath || file.name;
  return `${index}:${rel}:${file.size}:${file.lastModified}`;
}
function isImage(file) {
  return file?.type?.startsWith("image/") || /\.(png|jpe?g|webp|bmp|tiff?)$/i.test(file?.name || "");
}

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("files")) db.createObjectStore("files");
      if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function dbPut(store, key, value) {
  const db = await openDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value, key);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}
async function dbGet(store, key) {
  const db = await openDb();
  const value = await new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  db.close();
  return value;
}
async function dbClear(store) {
  const db = await openDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).clear();
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}
async function persistSession() {
  if (!session) return;
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
async function storeSelectedFiles(files) {
  await dbClear("files");
  selectedFiles = [];
  for (let i = 0; i < files.length; i += 1) {
    const file = files[i];
    if (!isImage(file)) continue;
    const key = imageKey(file, i);
    await dbPut("files", key, file);
    selectedFiles.push({ key, file, name: file.webkitRelativePath || file.name });
  }
  selectedFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  $("folderInfo").textContent = selectedFiles.length
    ? `${selectedFiles.length} imágenes enlazadas · ${selectedFiles[0].name}${selectedFiles.length > 1 ? " …" : ""}`
    : "Sin imágenes.";
}
async function loadFilesForSession(saved) {
  const loaded = [];
  for (const item of saved.items || []) {
    const file = await dbGet("files", item.key);
    if (file) loaded.push({ key: item.key, file, name: item.name });
  }
  return loaded;
}

function findImage(value) {
  if (!value) return null;
  if (typeof value === "string") {
    if (value.startsWith("data:image/") || /^https?:\/\//.test(value) || value.startsWith("blob:")) return value;
    return null;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findImage(item);
      if (found) return found;
    }
    return null;
  }
  if (typeof value === "object") {
    for (const key of ["url", "image", "path", "data", "value", "result"]) {
      const found = findImage(value[key]);
      if (found) return found;
    }
  }
  return null;
}
function rawImage(value) {
  if (Array.isArray(value) && value.length === 1) return value[0];
  return value;
}
function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [result?.data];
}
function randomSeed() {
  const buf = new Uint32Array(1);
  crypto.getRandomValues(buf);
  return buf[0] & 0x7fffffff;
}
function fileForCurrent() {
  const item = currentItem(session);
  return selectedFiles.find((entry) => entry.key === item?.key)?.file || null;
}

function renderQueue() {
  const host = $("queue");
  host.innerHTML = "";
  if (!session) {
    $("progressText").textContent = "0 / 0";
    $("bar").style.width = "0%";
    return;
  }
  const total = session.items.length;
  const finished = session.items.filter((x) => ["done", "skipped"].includes(x.status)).length;
  $("progressText").textContent = `${finished} / ${total} · perfil ${session.profile}`;
  $("bar").style.width = `${total ? (finished / total) * 100 : 0}%`;
  session.items.forEach((item) => {
    const node = document.createElement("div");
    node.className = `qitem ${item.index === session.cursor ? "active" : ""} ${item.status === "done" ? "done" : ""} ${item.status === "skipped" ? "skip" : ""}`;
    const icon = item.status === "done" ? `❤️${item.choice}` : item.status === "skipped" ? "⏭" : item.status === "review" ? "👀" : "•";
    node.textContent = `${icon} ${item.name.split("/").pop()}`;
    host.appendChild(node);
  });
}
function renderMemory() {
  if (!session) return $("memory").textContent = "Todavía no hay decisiones.";
  const liked = session.items.filter((x) => x.status === "done");
  const anchors = liked.filter((x) => x.promote);
  const skipped = session.items.filter((x) => x.status === "skipped");
  $("memory").textContent = `${liked.length} favoritas · ${anchors.length} anclas · ${skipped.length} saltadas · ${session.items.length} total${session.serverRunId ? " · sincronizado con bucket" : " · memoria local"}`;
}
function clearPair() {
  currentPair = null;
  $("candidateA").removeAttribute("src");
  $("candidateB").removeAttribute("src");
  $("metaA").textContent = "";
  $("metaB").textContent = "";
  $("cardA").classList.remove("winner");
  $("cardB").classList.remove("winner");
}
async function renderCurrent() {
  renderQueue();
  renderMemory();
  clearPair();
  const item = currentItem(session);
  if (!item) {
    $("review").classList.add("show");
    $("currentTitle").textContent = "✅ Lote terminado";
    $("original").removeAttribute("src");
    $("generate").disabled = true;
    $("retry").disabled = true;
    setReviewStatus("Todo revisado. Las elecciones quedan guardadas localmente y, cuando el Space nuevo está disponible, también en el bucket.", "ok");
    return;
  }
  const file = fileForCurrent();
  if (!file) {
    setReviewStatus("No encuentro el archivo local. Vuelve a enlazar la carpeta y pulsa Reanudar.", "err");
    return;
  }
  $("review").classList.add("show");
  $("currentTitle").textContent = `3 · Revisar ${item.index + 1}/${session.items.length} · ${item.name.split("/").pop()}`;
  $("original").src = URL.createObjectURL(file);
  $("generate").disabled = false;
  $("retry").disabled = false;
  setReviewStatus(item.attempts.length ? `${item.attempts.length} intento(s) guardados. Puedes reintentar o elegir.` : "Lista para generar A/B.");
  if (item.attempts.length) await restoreLatestPair(item);
}

async function restoreLatestPair(item) {
  const attempt = item.attempts[item.attempts.length - 1];
  if (!attempt) return;
  try {
    const blobA = attempt.aKey ? await dbGet("kv", attempt.aKey) : null;
    const blobB = attempt.bKey ? await dbGet("kv", attempt.bKey) : null;
    const urlA = blobA ? URL.createObjectURL(blobA) : attempt.a;
    const urlB = blobB ? URL.createObjectURL(blobB) : attempt.b;
    if (!urlA || !urlB) return;
    currentPair = {
      urlA, urlB, seedA: attempt.seedA, seedB: attempt.seedB,
      rawA: attempt.a, rawB: attempt.b, api: attempt.api || "restored",
    };
    renderPair();
  } catch (error) { console.info("Could not restore pair.", error); }
}

async function connectSpace() {
  try {
    client = await Client.connect(SPACE, { events: ["data", "status"] });
    $("conn").textContent = "GPU enlazada";
    setStatus("Conectado a tu Space Bashull.", "ok");
  } catch (error) {
    client = null;
    $("conn").textContent = "sin conexión";
    setStatus(`No pude conectar con Hugging Face: ${error.message}`, "err");
  }
}
async function tryServerSession() {
  if (!client || !session) return false;
  try {
    const profileResult = await client.predict("/studio_profile", { display_name: session.profile });
    const profileData = dataArray(profileResult);
    const profileId = profileData[0];
    const sources = selectedFiles.map((entry) => handle_file(entry.file));
    const runResult = await client.predict("/studio_start", {
      profile_id: profileId,
      prompt: session.prompt,
      sources,
      steps: session.steps,
    });
    session.serverRunId = dataArray(runResult)[0];
    await persistSession();
    return true;
  } catch (error) {
    console.info("Persistent Studio endpoints not ready yet; using local session.", error);
    session.serverRunId = null;
    await persistSession();
    return false;
  }
}

async function startSession() {
  if (!selectedFiles.length) return setStatus("Enlaza una carpeta o selecciona imágenes.", "err");
  const profile = $("profile").value.trim();
  const prompt = $("prompt").value.trim();
  if (!profile) return setStatus("Pon un nombre al perfil/persona.", "err");
  if (!prompt) return setStatus("Escribe el prompt maestro.", "err");
  session = createSession({
    profile,
    prompt,
    steps: Number($("steps").value) || 10,
    files: selectedFiles.map(({ key, name }) => ({ key, name })),
  });
  await persistSession();
  setStatus("Creando lote…", "");
  const synced = await tryServerSession();
  setStatus(synced ? "Lote enlazado al bucket de Kai AI Studio." : "Lote listo. Modo local hasta desplegar los endpoints nuevos.", "ok");
  await renderCurrent();
}
function fallbackSeeds(item) {
  const randomize = $("randomize").value === "true";
  const attempt = item.attempts.length;
  if (randomize) {
    let a = randomSeed();
    let b = randomSeed();
    while (b === a) b = randomSeed();
    return [a, b];
  }
  const base = Number($("seed").value) || 0;
  const a = (base + item.index * 1000 + attempt * 2) & 0x7fffffff;
  return [a, (a + 1) & 0x7fffffff];
}

async function cacheResult(raw, key) {
  const url = findImage(raw);
  if (!url) throw new Error("La GPU respondió pero no encontré una imagen en la salida.");
  try {
    const blob = await fetch(url).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.blob();
    });
    await dbPut("kv", key, blob);
    return { url: URL.createObjectURL(blob), key, blob };
  } catch (error) {
    console.info("No pude cachear resultado; uso URL remota.", error);
    return { url, key: null, blob: null };
  }
}

async function callPair(file, item) {
  const steps = session.steps;
  const randomize = $("randomize").value === "true";
  const baseSeed = Number($("seed").value) || 0;
  try {
    const result = await client.predict("/kai_edit_pair", {
      image_path: handle_file(file),
      prompt: session.prompt,
      seed: baseSeed,
      steps,
      randomize_seed: randomize,
    });
    const data = dataArray(result);
    if (data.length < 4) throw new Error("Respuesta A/B incompleta");
    return { rawA: rawImage(data[0]), rawB: rawImage(data[1]), seedA: Number(data[2]), seedB: Number(data[3]), api: "kai_edit_pair" };
  } catch (pairError) {
    console.info("Pair endpoint unavailable; falling back to two kai_edit calls.", pairError);
  }

  const [seedA, seedB] = fallbackSeeds(item);
  const callOne = async (seed) => {
    const result = await client.predict("/kai_edit", {
      image_path: handle_file(file),
      prompt: session.prompt,
      seed,
      steps,
    });
    return rawImage(dataArray(result)[0]);
  };
  const rawA = await callOne(seedA);
  const rawB = await callOne(seedB);
  return { rawA, rawB, seedA, seedB, api: "kai_edit×2" };
}
async function syncAttemptToServer(item, pair) {
  if (!session?.serverRunId) return;
  try {
    await client.predict("/studio_record", {
      run_id: session.serverRunId,
      index: item.index,
      candidate_a: pair.rawA,
      candidate_b: pair.rawB,
      seed_a: pair.seedA,
      seed_b: pair.seedB,
    });
  } catch (error) {
    console.info("Could not persist attempt on server.", error);
  }
}

async function generateCurrent() {
  if (busy) return;
  if (!client) return setReviewStatus("No hay conexión con Hugging Face.", "err");
  const item = currentItem(session);
  const file = fileForCurrent();
  if (!item || !file) return;
  busy = true;
  $("generate").disabled = true;
  $("retry").disabled = true;
  setReviewStatus("Generando dos alternativas… pueden entrar en cola ZeroGPU.");
  try {
    const pair = await callPair(file, item);
    const attemptNo = item.attempts.length + 1;
    const prefix = `result:${session.id}:${item.index}:${attemptNo}`;
    const a = await cacheResult(pair.rawA, `${prefix}:A`);
    const b = await cacheResult(pair.rawB, `${prefix}:B`);
    currentPair = { ...pair, urlA: a.url, urlB: b.url, keyA: a.key, keyB: b.key };
    recordAttempt(session, item.index, {
      seedA: pair.seedA, seedB: pair.seedB,
      a: a.url, b: b.url, aKey: a.key, bKey: b.key, api: pair.api,
    });
    await persistSession();
    await syncAttemptToServer(item, pair);
    renderPair();
    renderQueue();
    setReviewStatus(`Intento ${attemptNo} listo · ${pair.api}`, "ok");
  } catch (error) {
    setReviewStatus(error.message || String(error), "err");
  } finally {
    busy = false;
    $("generate").disabled = false;
    $("retry").disabled = false;
  }
}
function renderPair() {
  if (!currentPair) return;
  $("candidateA").src = currentPair.urlA;
  $("candidateB").src = currentPair.urlB;
  $("metaA").textContent = `Seed ${currentPair.seedA}`;
  $("metaB").textContent = `Seed ${currentPair.seedB}`;
  $("cardA").classList.remove("winner");
  $("cardB").classList.remove("winner");
}

async function syncChoiceToServer(item, choice, promote) {
  if (!session?.serverRunId) return false;
  try {
    await client.predict("/studio_choose", {
      run_id: session.serverRunId,
      index: item.index,
      choice,
      promote,
    });
    return true;
  } catch (error) {
    console.info("Could not persist choice on server.", error);
    return false;
  }
}

async function choose(choice, promote = false) {
  const item = currentItem(session);
  if (!item || !currentPair) return setReviewStatus("Genera A/B antes de elegir.", "err");
  const chosenUrl = choice === "A" ? currentPair.urlA : currentPair.urlB;
  $(choice === "A" ? "cardA" : "cardB").classList.add("winner");
  const synced = await syncChoiceToServer(item, choice, promote);
  chooseCandidate(session, item.index, choice, promote);
  item.winnerUrl = chosenUrl;
  await persistSession();
  await saveWinnerIfLinked(item, chosenUrl, choice);
  setReviewStatus(`❤️ ${choice} elegida${promote ? " · 📌 ancla" : ""}${synced ? " · bucket OK" : " · local"}`, "ok");
  setTimeout(() => renderCurrent(), 350);
}

async function skipCurrent() {
  const item = currentItem(session);
  if (!item) return;
  if (session.serverRunId) {
    try {
      await client.predict("/studio_skip", { run_id: session.serverRunId, index: item.index });
    } catch (error) { console.info("Could not persist skip.", error); }
  }
  skipItem(session, item.index);
  await persistSession();
  renderCurrent();
}
function safeName(value) {
  return String(value || "image").replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 120);
}
async function blobFromUrl(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`No pude leer el resultado (${response.status}).`);
  return response.blob();
}
async function ensureWritePermission(handle) {
  if (!handle) return false;
  if ((await handle.queryPermission?.({ mode: "readwrite" })) === "granted") return true;
  return (await handle.requestPermission?.({ mode: "readwrite" })) === "granted";
}
async function saveUrl(url, filename) {
  const blob = await blobFromUrl(url);
  if (outputDirectory && await ensureWritePermission(outputDirectory)) {
    const fileHandle = await outputDirectory.getFileHandle(filename, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(blob);
    await writable.close();
    return `Guardado en carpeta: ${filename}`;
  }
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
  return `Descargado: ${filename}`;
}
async function saveWinnerIfLinked(item, url, choice) {
  if (!outputDirectory) return;
  try {
    const base = safeName(item.name.split("/").pop().replace(/\.[^.]+$/, ""));
    await saveUrl(url, `${base}_winner_${choice}.png`);
  } catch (error) { console.info("Auto-save failed.", error); }
}
async function linkOutputDirectory() {
  if (!("showDirectoryPicker" in window)) {
    outputDirectory = null;
    $("outputDir").textContent = "💾 Tu navegador guardará en Descargas";
    setStatus("Android no ofrece escritura directa de carpeta en este navegador; usaré Descargas. La memoria canónica seguirá en el bucket.", "ok");
    return;
  }
  try {
    outputDirectory = await window.showDirectoryPicker({ mode: "readwrite" });
    await dbPut("kv", "outputDirectory", outputDirectory);
    $("outputDir").textContent = `💾 Salida: ${outputDirectory.name}`;
    setStatus(`Carpeta de salida enlazada: ${outputDirectory.name}`, "ok");
  } catch (error) {
    if (error.name !== "AbortError") setStatus(`No pude enlazar carpeta de salida: ${error.message}`, "err");
  }
}

async function saveCandidate(which) {
  if (!currentPair) return setReviewStatus("Primero genera A/B.", "err");
  const item = currentItem(session);
  const url = which === "A" ? currentPair.urlA : currentPair.urlB;
  const base = safeName(item.name.split("/").pop().replace(/\.[^.]+$/, ""));
  try {
    const msg = await saveUrl(url, `${base}_${which}.png`);
    setReviewStatus(msg, "ok");
  } catch (error) { setReviewStatus(error.message, "err"); }
}
async function saveBoth() {
  if (!currentPair) return setReviewStatus("Primero genera A/B.", "err");
  await saveCandidate("A");
  await saveCandidate("B");
}

async function resumeSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return setStatus("No hay una sesión local guardada.", "err");
  try {
    const saved = JSON.parse(raw);
    const loaded = await loadFilesForSession(saved);
    if (loaded.length !== (saved.items || []).length) {
      setStatus("La sesión existe, pero faltan archivos locales. Vuelve a enlazar la carpeta original.", "err");
      return;
    }
    session = saved;
    selectedFiles = loaded;
    $("profile").value = session.profile || "";
    $("prompt").value = session.prompt || "";
    $("steps").value = session.steps || 10;
    $("folderInfo").textContent = `${selectedFiles.length} imágenes restauradas desde el móvil.`;
    setStatus(`Sesión reanudada · ${session.serverRunId ? "bucket enlazado" : "local"}`, "ok");
    await renderCurrent();
  } catch (error) {
    setStatus(`No pude reanudar: ${error.message}`, "err");
  }
}

async function resetSession() {
  localStorage.removeItem(SESSION_KEY);
  await dbClear("files");
  session = null;
  selectedFiles = [];
  currentPair = null;
  $("folderInfo").textContent = "Sin imágenes.";
  $("review").classList.remove("show");
  renderQueue();
  renderMemory();
  setStatus("Sesión local borrada. El contenido ya persistido en el bucket no se elimina.", "ok");
}
async function handleSelection(event) {
  const files = [...(event.target.files || [])].filter(isImage);
  if (!files.length) return;
  setStatus(`Guardando ${files.length} imágenes en la memoria local…`);
  try {
    await storeSelectedFiles(files);
    setStatus(`${selectedFiles.length} imágenes listas.`, "ok");
  } catch (error) {
    setStatus(`No pude preparar la carpeta: ${error.message}`, "err");
  }
}

$("folder").addEventListener("change", handleSelection);
$("images").addEventListener("change", handleSelection);
$("outputDir").addEventListener("click", linkOutputDirectory);
$("start").addEventListener("click", startSession);
$("generate").addEventListener("click", generateCurrent);
$("retry").addEventListener("click", generateCurrent);
$("likeA").addEventListener("click", () => choose("A", false));
$("likeB").addEventListener("click", () => choose("B", false));
$("anchorA").addEventListener("click", () => choose("A", true));
$("anchorB").addEventListener("click", () => choose("B", true));
$("skip").addEventListener("click", skipCurrent);
$("saveA").addEventListener("click", () => saveCandidate("A"));
$("saveB").addEventListener("click", () => saveCandidate("B"));
$("saveBoth").addEventListener("click", saveBoth);
$("resume").addEventListener("click", resumeSession);
$("reset").addEventListener("click", resetSession);

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstall = event;
  $("install").classList.add("show");
});
$("install").addEventListener("click", async () => {
  if (!deferredInstall) return;
  deferredInstall.prompt();
  await deferredInstall.userChoice;
  deferredInstall = null;
  $("install").classList.remove("show");
});
async function boot() {
  renderQueue();
  renderMemory();
  try {
    outputDirectory = await dbGet("kv", "outputDirectory");
    if (outputDirectory?.name) $("outputDir").textContent = `💾 Salida: ${outputDirectory.name}`;
  } catch (error) { console.info("No stored output directory.", error); }

  const saved = localStorage.getItem(SESSION_KEY);
  if (saved) {
    try {
      const meta = JSON.parse(saved);
      $("memory").textContent = `Sesión guardada: ${meta.profile} · ${meta.items?.length || 0} imágenes. Pulsa Reanudar guardado.`;
    } catch {}
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch((error) => console.info("SW registration failed", error));
  }
  await connectSpace();
}

boot();
