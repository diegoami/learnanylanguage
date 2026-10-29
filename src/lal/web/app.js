// The lesson client's page: choose a lesson, choose the teacher, run it, save the transcript.
// Keys live in this browser's localStorage and are sent only to their own provider.
import * as core from "./core.js";

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const SETTINGS = "lal.web.settings";

let settings = { provider: "openrouter", model: "", openrouterKey: "", geminiKey: "", elevenlabsKey: "", voice: core.ELEVENLABS.voice };
let server = false;      // served by `lal web`, with the learner data behind it
let lesson = null;       // { package, info, track?, folder?, recorded? }
let teacher = "chatgpt"; // chatgpt | typed | voice
let turns = [], models = new Set(), started = "", busy = false, recorder = null, chunks = [];
const audioCache = new Map();
let lastAudio = null;

// --- settings ------------------------------------------------------------------
function loadSettings() {
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS) || "{}")); } catch { /* private mode */ }
}
function saveSettings() {
  try { localStorage.setItem(SETTINGS, JSON.stringify(settings)); } catch { /* private mode */ }
}
function renderSettings() {
  $("provider").value = settings.provider;
  $("model").value = settings.model;
  $("model").placeholder = core.PROVIDERS[settings.provider].model;
  for (const k of ["openrouterKey", "geminiKey", "elevenlabsKey", "voice"]) $(k).value = settings[k];
}
function bindSettings() {
  for (const k of ["provider", "model", "openrouterKey", "geminiKey", "elevenlabsKey", "voice"]) {
    $(k).addEventListener("change", () => { settings[k] = $(k).value.trim(); saveSettings(); renderSettings(); renderTeacher(); });
  }
  $("forget").addEventListener("click", () => {
    Object.assign(settings, { openrouterKey: "", geminiKey: "", elevenlabsKey: "" });
    saveSettings(); renderSettings(); renderTeacher();
  });
}
const chatKey = () => settings.provider === "gemini" ? settings.geminiKey : settings.openrouterKey;
const chatModel = () => settings.model || core.PROVIDERS[settings.provider].model;

// --- choosing a lesson --------------------------------------------------------------
async function loadLessons() {
  try {
    const info = await (await fetch("/api/info")).json();
    server = info.server === "lal";
    $("dataPath").textContent = info.data;
  } catch { server = false; }
  $("serverLessons").hidden = !server;
  if (!server) return;
  const list = await (await fetch("/api/lessons")).json();
  $("lessonList").innerHTML = list.length ? list.map((l, i) => `<button class="lesson ${l.recorded ? "done" : ""}" data-i="${i}">
      <span><b>${esc(l.track)}</b> · session ${l.session}${esc(l.part)} · ${esc(l.mode)}${l.channel === "text" ? " (text)" : ""}</span>
      <small>${esc(l.date)}${l.recorded ? " · recorded" : ""}</small></button>`).join("")
    : '<p class="muted">No prepared lessons in the learner data. Ask the agent to prepare one, or paste a package below.</p>';
  $("lessonList").querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
    const l = list[+b.dataset.i];
    const data = await (await fetch(`/api/lesson?track=${encodeURIComponent(l.track)}&folder=${encodeURIComponent(l.folder)}`)).json();
    useLesson(data.package, { track: l.track, folder: l.folder, recorded: data.recorded });
  }));
}

function useLesson(text, place = {}) {
  const info = core.parsePackage(text);
  if (!info.kind) { showError("That is not a lesson package (it must start with VOICE_SESSION_PACKAGE or TEXT_SESSION_PACKAGE)."); return; }
  lesson = { package: text, info, ...place };
  turns = []; models = new Set(); started = "";
  if (info.kind === "text" && teacher === "voice") teacher = "typed";
  $("lessonInfo").innerHTML = `<b>${esc(info.track)}</b> · ${esc(info.session)}<br>${esc(info.mode)} · ${esc(info.channel)} · ${esc(info.languageName || info.language || "language not stated")} · prompt ${esc(info.version)}`
    + (place.folder ? `<br><span class="muted">${esc(place.track)}/${esc(place.folder)}</span>` : "<br><span class=\"muted\">pasted or opened: the transcript will be downloaded</span>")
    + (info.complete ? "" : '<br><span class="warn">The package still has &lt;&lt;FILL&gt;&gt; fields: let the agent finish it first.</span>')
    + (place.recorded ? '<br><span class="warn">This lesson is already recorded; a new run cannot be saved over it.</span>' : "");
  $("teacherCard").hidden = false;
  renderTeacher();
  renderLog();
}

// --- the teacher ------------------------------------------------------------------
function renderTeacher() {
  if (!lesson) return;
  const textOnly = lesson.info.kind === "text";
  document.querySelectorAll('input[name="teacher"]').forEach(r => {
    r.checked = r.value === teacher;
    r.disabled = r.value === "voice" && textOnly;
  });
  $("voiceNote").textContent = textOnly ? "This is a typed lesson: no voice." : "";
  $("chatgptPanel").hidden = teacher !== "chatgpt";
  $("ownPanel").hidden = teacher === "chatgpt";
  $("typeRow").hidden = teacher !== "typed";
  $("voiceRow").hidden = teacher !== "voice";
  const missing = [];
  if (teacher !== "chatgpt" && !chatKey()) missing.push(`${core.PROVIDERS[settings.provider].label} key`);
  if (teacher === "voice" && !settings.elevenlabsKey) missing.push("ElevenLabs key");
  if (teacher === "voice" && !lesson.info.language) missing.push("a Language line in the package (rebuild it with the current lal)");
  $("ownMissing").textContent = missing.length ? `Missing in Settings: ${missing.join(", ")}.` : "";
  $("startBtn").disabled = Boolean(missing.length) || busy || turns.length > 0 || !lesson.info.complete;
  $("startCmd").textContent = lesson.info.start ? `Start command: «${lesson.info.start}»` : "";
}

function renderLog() {
  const done = turns.some(t => t.who === "teacher" && core.isClose(t.text, lesson?.info.close));
  $("log").innerHTML = turns.map(t => `<div class="turn ${t.who}${t.ready ? " ready" : ""}"><span>${t.who === "teacher" ? "Teacher" : "You"}${t.channel === "voice" ? " 🎙" : ""}</span>${esc(t.text)}</div>`).join("");
  $("log").scrollTop = $("log").scrollHeight;
  $("afterRow").hidden = !turns.length;
  $("reportBtn").hidden = !done || !/drill|writing/.test(lesson?.info.mode || "") || turns.some(t => t.text.trim() === "REPORT");
  $("saveBtn").textContent = lesson?.folder ? "Save the transcript in the lesson folder" : "Download the transcript";
}

function setStatus(text) { $("status").textContent = text; }
function showError(text) { $("error").textContent = text; $("error").hidden = !text; }

async function askTeacher() {
  const request = settings.provider === "gemini"
    ? core.geminiRequest(chatKey(), chatModel(), lesson.package, turns)
    : core.openrouterRequest(chatKey(), chatModel(), lesson.package, turns);
  const response = await fetch(request.url, request.init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${core.PROVIDERS[settings.provider].label}: ${data?.error?.message || response.status}`);
  models.add(data.model || chatModel());
  return request.reply(data).trim();
}

async function say(text) {
  if (teacher !== "voice") return;
  const words = core.speakable(text);
  if (!words) return;
  let url = audioCache.get(words);
  if (!url) {
    const response = await fetch(core.ELEVENLABS.tts(settings.voice || core.ELEVENLABS.voice), {
      method: "POST",
      headers: { "xi-api-key": settings.elevenlabsKey, "Content-Type": "application/json" },
      body: JSON.stringify({ text: words, model_id: core.ELEVENLABS.ttsModel, seed: 1 }),
    });
    if (!response.ok) throw new Error(`ElevenLabs voice: ${(await response.json().catch(() => ({})))?.detail?.message || response.status}`);
    url = URL.createObjectURL(await response.blob());
    audioCache.set(words, url);
  }
  lastAudio = url;
  await play(url);
}

function play(url) {
  return new Promise(resolve => {
    const audio = new Audio(url);
    audio.onended = audio.onerror = resolve;
    audio.play().catch(resolve);
  });
}

async function teacherTurn(ready = false) {
  setStatus("The teacher is thinking…");
  const text = await askTeacher();
  turns.push({ who: "teacher", text, channel: teacher === "voice" && !ready ? "voice" : "text", ready });
  keepDraft();
  renderLog();
  const askedReport = turns.length > 1 && turns[turns.length - 2].text.trim() === "REPORT";
  const finished = core.isClose(text, lesson.info.close) && !/drill|writing/.test(lesson.info.mode);
  if (!ready && (finished || askedReport) && lesson.folder && server && !lesson.recorded) {
    await say(text);
    await save(); // the transcript is never left only in the page
    return;
  }
  if (!ready) { setStatus(teacher === "voice" ? "The teacher is speaking…" : ""); await say(text); }
  setStatus(teacher === "voice" ? "Your turn: tap to talk." : "Your turn.");
}

async function learnerTurn(text, channel) {
  turns.push({ who: "learner", text, channel });
  keepDraft();
  renderLog();
  await teacherTurn();
}

async function guarded(action) {
  if (busy) return;
  busy = true; showError(""); renderTeacher(); toggleControls();
  try { await action(); } catch (e) { showError(e.message); setStatus(""); }
  busy = false; renderTeacher(); toggleControls();
}

function toggleControls() {
  $("sendBtn").disabled = busy || !turns.length;
  $("talkBtn").disabled = (busy && !recorder) || !turns.length;
  $("againBtn").disabled = busy || !lastAudio;
}

async function start() {
  started = core.utc();
  await teacherTurn(true); // the "Ready …" reply to the package
  await learnerTurn(lesson.info.start || "Start", "text");
}

// --- voice: tap to talk -----------------------------------------------------------
async function talk() {
  if (recorder) { recorder.stop(); return; }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find(t => MediaRecorder.isTypeSupported(t)) || "";
  recorder = new MediaRecorder(stream, type ? { mimeType: type } : {});
  chunks = [];
  recorder.ondataavailable = e => chunks.push(e.data);
  recorder.onstop = () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
    recorder = null;
    $("talkBtn").textContent = "Tap to talk";
    if (blob.size < 2000) { setStatus("Too short: tap, speak, tap again."); toggleControls(); return; }
    guarded(async () => {
      setStatus("Listening to your answer…");
      const form = new FormData();
      form.append("model_id", core.ELEVENLABS.sttModel);
      form.append("language_code", lesson.info.language);
      form.append("tag_audio_events", "false");
      form.append("diarize", "false");
      form.append("file", blob, blob.type.includes("mp4") ? "turn.mp4" : "turn.webm");
      const response = await fetch(core.ELEVENLABS.stt, { method: "POST", headers: { "xi-api-key": settings.elevenlabsKey }, body: form });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`ElevenLabs recognition: ${data?.detail?.message || response.status}`);
      const heard = (data.text || "").trim();
      if (!heard) { setStatus("Nothing heard: tap and try again."); return; }
      await learnerTurn(heard, "voice");
    });
  };
  recorder.start();
  $("talkBtn").textContent = "Tap to stop";
  setStatus("Recording… tap again when you have finished.");
  toggleControls();
}

// --- ChatGPT: copy, paste, share ------------------------------------------------------
async function copyPackage() {
  try { await navigator.clipboard.writeText(lesson.package); setStatus("Package copied. Paste it into a new ChatGPT chat."); }
  catch { showError("Copying failed: select the package text yourself."); }
}

async function readShare() {
  const url = $("shareUrl").value.trim();
  if (!server) { showError("Reading a share link needs `lal web` (the browser cannot read ChatGPT pages): run `lal share <link>` instead."); return; }
  await guarded(async () => {
    setStatus("Reading the shared chat…");
    const response = await fetch("/api/share", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, track: lesson.track || "", folder: lesson.folder || "" }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    $("shareResult").textContent = data.transcript;
    setStatus(data.saved ? `Saved in ${data.saved}. Hand it to the agent to record.` : "Read; this lesson has no folder, so nothing was saved.");
    if (lesson.folder) { lesson.recorded = true; loadLessons(); }
  });
}

// --- the companion and the transcript viewer ------------------------------------------
async function loadCompanion() {
  if (!server) { $("companion").innerHTML = '<p class="muted">The companion needs <code>lal web</code> (it reads the learner data). Otherwise open COMPANION.md in the learner data.</p>'; return; }
  const data = await (await fetch("/api/companion")).json();
  $("companion").innerHTML = core.markdownToHtml(data.markdown);
}

async function openFile(path) {
  const response = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
  const text = await response.text();
  $("viewerTitle").textContent = path;
  $("viewerDoc").innerHTML = response.ok ? core.markdownToHtml(text) : `<p class="warn">${esc(text)}</p>`;
  $("viewer").hidden = false;
}

async function openInEditor(path) {
  const response = await fetch("/api/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) });
  const data = await response.json();
  if (!response.ok) showError(data.error); else setStatus(`Opened ${path} with ${data.opened[0]}.`);
}

async function savePasted() {
  const text = $("pastedChat").value.trim();
  if (!text) return;
  const body = `Pasted conversation (not from a share link: check for lost turns)\n\n${text}`;
  if (!(lesson.folder && server)) { download(body); return; }
  await guarded(async () => {
    const response = await fetch("/api/transcript", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track: lesson.track, folder: lesson.folder, body, model: "ChatGPT (pasted conversation)" }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    setStatus(`Saved in ${data.saved}. Hand it to the agent to record.`);
    lesson.recorded = true; loadLessons();
  });
}

// --- saving -----------------------------------------------------------------------
const draftKey = () => lesson?.folder ? `lal.web.draft.${lesson.track}/${lesson.folder}` : "lal.web.draft.pasted";
function keepDraft() {
  try { localStorage.setItem(draftKey(), JSON.stringify({ turns, models: [...models], started, teacher })); } catch { /* private mode */ }
}
function dropDraft() { try { localStorage.removeItem(draftKey()); } catch { /* private mode */ } }

function download(body) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([body + "\n"], { type: "text/markdown" }));
  link.download = "transcript.md";
  link.click();
}

async function save() {
  const body = core.transcript(lesson.info, turns, {
    teacher: teacher === "voice" ? `own keys, voice (ElevenLabs + ${core.PROVIDERS[settings.provider].label})` : `own keys, typed (${core.PROVIDERS[settings.provider].label})`,
    models: [...models], started, ended: core.utc(),
  });
  if (lesson.folder && server && !lesson.recorded) {
    const response = await fetch("/api/transcript", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track: lesson.track, folder: lesson.folder, body, model: [...models].join(", ") }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    setStatus(`Saved in ${data.saved}. Hand it to the agent to record.`);
    lesson.recorded = true; dropDraft(); loadLessons();
  } else {
    download(body);
  }
}

// --- wiring -------------------------------------------------------------------------
function init() {
  loadSettings(); renderSettings(); bindSettings();
  document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach(x => x.classList.toggle("on", x === b));
    $("lessonView").hidden = b.dataset.view !== "lesson";
    $("companionView").hidden = b.dataset.view !== "companion";
    $("settingsView").hidden = b.dataset.view !== "settings";
    if (b.dataset.view === "companion") loadCompanion();
  }));
  $("pasteBtn").addEventListener("click", () => useLesson($("pasteBox").value));
  $("fileInput").addEventListener("change", async e => { const f = e.target.files[0]; if (f) useLesson(await f.text()); });
  document.querySelectorAll('input[name="teacher"]').forEach(r => r.addEventListener("change", () => { teacher = r.value; renderTeacher(); }));
  $("copyBtn").addEventListener("click", copyPackage);
  $("shareBtn").addEventListener("click", readShare);
  $("startBtn").addEventListener("click", () => guarded(start));
  $("sendBtn").addEventListener("click", () => { const t = $("typeBox").value.trim(); if (t) { $("typeBox").value = ""; guarded(() => learnerTurn(t, "text")); } });
  $("typeBox").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("sendBtn").click(); } });
  $("talkBtn").addEventListener("click", () => talk().catch(e => showError(`Microphone: ${e.message}`)));
  $("againBtn").addEventListener("click", () => lastAudio && play(lastAudio));
  $("reportBtn").addEventListener("click", () => guarded(() => learnerTurn("REPORT", "text")));
  $("saveBtn").addEventListener("click", () => guarded(save));
  $("pastedBtn").addEventListener("click", savePasted);
  $("companionRefresh").addEventListener("click", loadCompanion);
  $("viewerClose").addEventListener("click", () => { $("viewer").hidden = true; });
  $("viewerEdit").addEventListener("click", () => openInEditor($("viewerTitle").textContent));
  $("companionEdit").addEventListener("click", () => openInEditor("COMPANION.md"));
  document.addEventListener("click", e => {
    const a = e.target.closest("a[data-file]");
    if (a) { e.preventDefault(); openFile(a.dataset.file); }
  });
  toggleControls();
  loadLessons();
}
init();
