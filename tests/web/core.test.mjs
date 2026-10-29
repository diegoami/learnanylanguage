// Run with: node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import * as core from "../../src/lal/web/core.js";

function render(args) {
  const env = { ...process.env, LAL_TRACK_PATH: "tracks", LAL_DATA: "/nonexistent-lal-test" };
  return execFileSync("uv", ["run", "lal", "lesson", "new", "--stdout", ...args], { env, encoding: "utf-8" });
}

test("parses a voice package rendered by lal", () => {
  const info = core.parsePackage(render(["--track", "uk-advanced", "--mode", "grammar", "--session", "1"]));
  assert.equal(info.kind, "voice");
  assert.equal(info.mode, "grammar drill");
  assert.equal(info.channel, "voice");
  assert.equal(info.language, "uk");
  assert.equal(info.languageName, "Ukrainian");
  assert.equal(info.track, "uk-advanced");
  assert.equal(info.start, "Почнімо");
  assert.equal(info.close, "Заняття закінчено.");
  assert.equal(info.complete, false); // still has <<FILL>> fields
});

test("parses a text package", () => {
  const info = core.parsePackage(render(["--track", "ja-first-steps", "--mode", "writing", "--session", "2"]));
  assert.equal(info.kind, "text");
  assert.equal(info.channel, "text");
  assert.equal(info.language, "ja");
  assert.equal(info.start, "はじめましょう");
  assert.equal(info.close, "今日のレッスンはこれで終わりです。");
});

test("the package is the first message, then the turns", () => {
  const turns = [{ who: "teacher", text: "Ready" }, { who: "learner", text: "Почнімо" }];
  const msgs = core.chatMessages("PKG", turns);
  assert.deepEqual(msgs.map(m => m.role), ["user", "assistant", "user"]);
  const g = JSON.parse(core.geminiRequest("k", "gemini-3.8-flash", "PKG", turns).init.body);
  assert.deepEqual(g.contents.map(c => c.role), ["user", "model", "user"]);
  const o = core.openrouterRequest("k", "google/gemini-3.8-flash", "PKG", turns);
  assert.equal(o.init.headers.Authorization, "Bearer k");
  assert.equal(o.reply({ choices: [{ message: { content: "Добре." } }] }), "Добре.");
});

test("speech keeps stress marks and drops Markdown", () => {
  assert.equal(core.speakable("**Ви́правлення:** до це́нтру\n- next"), "Ви́правлення: до це́нтру next");
});

test("the close is recognised loosely", () => {
  assert.ok(core.isClose("«Lekcja skończona.»", "Lekcja skończona."));
  assert.ok(!core.isClose("Proszę powtórzyć.", "Lekcja skończona."));
});

test("the transcript uses lal share's format, so lal report reads it", () => {
  const info = { kind: "voice", version: "g3" };
  const turns = [
    { who: "teacher", text: "Ready for voice.", channel: "text" },
    { who: "learner", text: "Zaczynamy", channel: "text" },
    { who: "teacher", text: "Czytam. → ?", channel: "voice" },
    { who: "learner", text: "Czytałem.", channel: "voice" },
  ];
  const out = core.transcript(info, turns, { teacher: "own keys", models: ["m"], started: "2026-10-29 10:00" });
  assert.match(out, /^<!-- 5 messages \(2 in voice: 1 learner, 1 teacher\); from 2026-10-29 10:00/);
  assert.match(out, /\*\*Learner\*\* \(text\): \[VOICE_SESSION_PACKAGE, prompt g3 — see package.md\]/);
  assert.match(out, /\*\*Learner\*\* \(voice\): Czytałem\./);
});

test("the page loads no third-party scripts", () => {
  const html = readFileSync(new URL("../../src/lal/web/index.html", import.meta.url), "utf-8");
  assert.deepEqual([...html.matchAll(/<script[^>]*src="([^"]+)"/g)].map(m => m[1]), ["app.js"]);
});

test("romaji is asked of the same provider, and only for Japanese text", () => {
  const o = core.romanizeRequest("openrouter", "k", "google/gemini-3.8-flash", "駅はどこですか。");
  const body = JSON.parse(o.init.body);
  assert.equal(body.messages.length, 1);
  assert.match(body.messages[0].content, /Hepburn romaji[\s\S]*駅はどこですか。$/);
  const g = core.romanizeRequest("gemini", "k", "gemini-3.8-flash", "はい");
  assert.match(g.url, /generativelanguage/);
  assert.ok(core.hasJapanese("コーヒーを一つください") && core.hasJapanese("駅"));
  assert.ok(!core.hasJapanese("Kōhī o hitotsu kudasai") && !core.hasJapanese("Добрий день"));
});
