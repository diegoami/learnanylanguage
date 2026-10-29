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

const escapeHtml = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, href) => /^https?:/.test(href)
      ? `<a href="${href}" target="_blank" rel="noopener">${label}</a>`
      : `<a href="#" data-file="${href}">${label}</a>`);
}

/** A small Markdown renderer for the companion and transcripts: headings, tables, lists, paragraphs, links. */
export function markdownToHtml(text) {
  const out = [], lines = text.replace(/\r/g, "").split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^<!--.*-->$/.test(line.trim())) continue;
    if (/^#{1,6} /.test(line)) {
      const n = line.match(/^#+/)[0].length;
      out.push(`<h${n}>${inline(line.slice(n + 1))}</h${n}>`);
    } else if (line.trim().startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(lines[i++]);
      i--;
      const cells = r => r.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, "|"));
      out.push(`<div class="scroll"><table><tr>${cells(rows[0]).map(c => `<th>${inline(c)}</th>`).join("")}</tr>${
        rows.slice(2).map(r => `<tr>${cells(r).map(c => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</table></div>`);
    } else if (/^\s*- /.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*- /.test(lines[i])) items.push(lines[i++].replace(/^\s*- (\[[ x]\] )?/, ""));
      i--;
      out.push(`<ul>${items.map(x => `<li>${inline(x)}</li>`).join("")}</ul>`);
    } else if (/^---+\s*$/.test(line)) {
      out.push("<hr>");
    } else if (line.trim()) {
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  return out.join("\n");
}
