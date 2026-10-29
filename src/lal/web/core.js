// Pure logic of the lesson client: reading a package, building provider
// requests, and writing the transcript in the format `lal share` writes.
// No DOM, no network: app.js does those, and tests/web/core.test.mjs tests this.

export const PROVIDERS = {
  openrouter: { label: "OpenRouter", model: "google/gemini-3.8-flash" },
  gemini: { label: "Gemini", model: "gemini-3.8-flash" },
};
export const ELEVENLABS = {
  stt: "https://api.elevenlabs.io/v1/speech-to-text",
  sttModel: "scribe_v2",
  tts: voice => `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(voice)}?output_format=mp3_44100_128`,
  ttsModel: "eleven_multilingual_v2",
  voice: "JBFqnCBsd6RMkjVDRZzb", // voice-teacher's measured default
};

/** What the client needs to know about a package. */
export function parsePackage(text) {
  const line = name => (text.match(new RegExp(`^${name}: (.+)$`, "m")) || [])[1]?.trim() || "";
  const brief = text.slice(Math.max(0, text.search(/^SESSION_BRIEF$/m)));
  const briefLine = name => (brief.match(new RegExp(`^${name}: (.+)$`, "m")) || [])[1]?.trim() || "";
  const kind = text.startsWith("TEXT_SESSION_PACKAGE") ? "text" : text.startsWith("VOICE_SESSION_PACKAGE") ? "voice" : "";
  const ready = text.match(/^Ready for (?:voice|text)\..*?«(.+?)»/m);
  const close = text.match(/^CLOSE\n\n(?:Say|Write) only[^\n]*\n\n«(.+?)»/m);
  const language = briefLine("Language").split(/\s+—\s+/);
  return {
    kind,
    version: line("Prompt version"),
    mode: briefLine("Mode"),
    channel: briefLine("Channel") || (kind === "text" ? "text" : "voice"),
    track: briefLine("Track").split(/\s+/)[0] || "",
    session: briefLine("Session"),
    language: language[0] || "",
    languageName: language[1] || "",
    start: ready ? ready[1] : "",
    close: close ? close[1] : "",
    complete: Boolean(kind) && !text.includes("<<FILL") && /END_SESSION_BRIEF/.test(text),
  };
}

/** The lesson so far as provider messages: the package is the learner's first message, as in ChatGPT. */
export function chatMessages(packageText, turns) {
  return [{ role: "user", content: packageText },
    ...turns.map(t => ({ role: t.who === "teacher" ? "assistant" : "user", content: t.text }))];
}

export function openrouterRequest(key, model, packageText, turns) {
  return {
    url: "https://openrouter.ai/api/v1/chat/completions",
    init: {
      method: "POST",
      headers: { "Authorization": `Bearer ${key}`, "Content-Type": "application/json", "X-Title": "learnanylanguage" },
      body: JSON.stringify({ model, messages: chatMessages(packageText, turns) }),
    },
    reply: data => data?.choices?.[0]?.message?.content ?? "",
  };
}

export function geminiRequest(key, model, packageText, turns) {
  const contents = chatMessages(packageText, turns)
    .map(m => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.content }] }));
  return {
    url: `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`,
    init: {
      method: "POST",
      headers: { "x-goog-api-key": key, "Content-Type": "application/json" },
      body: JSON.stringify({ contents }),
    },
    reply: data => (data?.candidates?.[0]?.content?.parts || []).map(p => p.text || "").join(""),
  };
}

/** Text a voice should say: no Markdown symbols; stress marks (U+0301) are kept on purpose. */
export function speakable(text) {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/[*_`#>]+/g, "")
    .replace(/^\s*[-•]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function isClose(text, close) {
  const norm = s => s.replace(/[«»"“”.!\s]+/g, " ").trim().toLowerCase();
  return Boolean(close) && norm(text).includes(norm(close));
}

/** The transcript in `lal share`'s format, so `lal report` and the record workflow read it unchanged. */
export function transcript(info, turns, meta) {
  const voice = turns.filter(t => t.channel === "voice");
  const head = `<!-- ${turns.length + 1} messages (${voice.length} in voice: ` +
    `${voice.filter(t => t.who === "learner").length} learner, ${voice.filter(t => t.who === "teacher").length} teacher); ` +
    `${meta.started ? `from ${meta.started} to ${meta.ended || meta.started} UTC; ` : ""}` +
    `teacher: ${meta.teacher}; models: ${meta.models.join(", ") || "not shown"} -->`;
  const lines = [`**Learner** (text): [${info.kind === "text" ? "TEXT" : "VOICE"}_SESSION_PACKAGE, prompt ${info.version || "?"} — see package.md]`];
  for (const t of turns) lines.push(`**${t.who === "teacher" ? "Teacher" : "Learner"}** (${t.channel}): ${t.text}`);
  return `${head}\n\n${lines.join("\n\n")}`;
}

export function utc(date = new Date()) {
  return date.toISOString().slice(0, 16).replace("T", " ");
}
