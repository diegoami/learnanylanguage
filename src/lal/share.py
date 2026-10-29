"""Read a ChatGPT share link and print the conversation as a voice-session transcript.

The share page embeds the conversation as React Router "turbo-stream" data: a
flat JSON array in which objects refer to their keys and values by index. This
tool decodes it and prints one line per message, with the learner and teacher
turns labelled the way `transcript.md` files are. Voice turns carry ChatGPT's
own transcription of the audio.

Usage:
    lal share https://chatgpt.com/share/<id>
    lal share <url> --package-out package.md
    lal share --html saved_page.html
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
TAGS = ("D", "P", "S", "E", "Y", "U", "R", "M", "B", "Z")
PACKAGES = ("VOICE_SESSION_PACKAGE", "TEXT_SESSION_PACKAGE")


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def decode(html: str) -> object:
    chunks = re.findall(r'streamController\.enqueue\((".*?")\);', html, re.S)
    if not chunks:
        raise ValueError("no embedded conversation data found (not a ChatGPT share page?)")
    flat = json.loads("".join(json.loads(c) for c in chunks).split("\n")[0])
    memo: dict[int, object] = {}
    sys.setrecursionlimit(max(10000, 4 * len(flat)))

    def resolve(i: int) -> object:
        if i < 0:
            return None
        if i in memo:
            return memo[i]
        value = flat[i]
        if isinstance(value, dict):
            out: dict = {}
            memo[i] = out
            for key, ref in value.items():
                out[flat[int(key[1:])]] = resolve(ref) if isinstance(ref, int) else ref
            return out
        if isinstance(value, list) and not (value and isinstance(value[0], str) and value[0] in TAGS):
            items: list = []
            memo[i] = items
            items.extend(resolve(x) if isinstance(x, int) else x for x in value)
            return items
        memo[i] = value
        return value

    return resolve(0)


def find(obj: object, key: str, depth: int = 0) -> object:
    if depth > 14:
        return None
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        children = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return None
    for child in children:
        found = find(child, key, depth + 1)
        if found is not None:
            return found
    return None


def messages(root: object) -> list[dict]:
    nodes = find(root, "linear_conversation") or []
    out = []
    for node in nodes:
        message = node.get("message") if isinstance(node, dict) else None
        if not message:
            continue
        role = (message.get("author") or {}).get("role")
        content = message.get("content") or {}
        if role not in ("user", "assistant") or content.get("content_type") not in ("text", "multimodal_text"):
            continue
        texts = []
        for part in content.get("parts") or []:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
        text = "\n".join(t.strip() for t in texts if t and t.strip())
        if not text:
            continue
        meta = message.get("metadata") or {}
        out.append({
            "role": role,
            "text": text,
            "voice": content.get("content_type") == "multimodal_text",
            "model": meta.get("model_slug") or meta.get("default_model_slug"),
            "time": message.get("create_time"),
        })
    return out


def transcript(msgs: list[dict]) -> str:
    lines = []
    for m in msgs:
        who = "Learner" if m["role"] == "user" else "Teacher"
        text = m["text"]
        if who == "Learner" and text.startswith(PACKAGES):
            version = re.search(r"^Prompt version: (\S+)", text, re.M)
            text = f"[{text.split(chr(10))[0]}, prompt {version.group(1) if version else '?'} — see package.md]"
        mode = "voice" if m["voice"] else "text"
        lines.append(f"**{who}** ({mode}): {text}")
    return "\n\n".join(lines)


def summary(msgs: list[dict]) -> str:
    voice = [m for m in msgs if m["voice"]]
    times = [m["time"] for m in (voice or msgs) if m["time"]]
    models = sorted({m["model"] for m in msgs if m["model"]})
    span = ""
    if times:
        start = dt.datetime.fromtimestamp(min(times), dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        end = dt.datetime.fromtimestamp(max(times), dt.timezone.utc).strftime("%H:%M")
        span = f"{'voice' if voice else 'text'} from {start} to {end} UTC; "
    return (f"{len(msgs)} messages ({len(voice)} in voice: "
            f"{sum(m['role'] == 'user' for m in voice)} learner, {sum(m['role'] == 'assistant' for m in voice)} teacher); "
            f"{span}models: {', '.join(models) or 'not shown'}")


def read(url: str | None, html_file: Path | None, package_out: Path | None) -> str:
    """The transcript text for a share link or saved page; optionally save the pasted package."""
    html = html_file.read_text(encoding="utf-8") if html_file else fetch(url)
    msgs = messages(decode(html))
    if package_out:
        pasted = next((m["text"] for m in msgs
                       if m["role"] == "user" and m["text"].startswith(PACKAGES)), None)
        if pasted is None:
            print("No lesson package in the conversation.", file=sys.stderr)
        else:
            package_out.write_text(pasted.rstrip() + "\n", encoding="utf-8", newline="\n")
    return f"<!-- {summary(msgs)} -->\n\n{transcript(msgs)}"
