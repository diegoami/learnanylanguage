"""Check the stress marks in Ukrainian lesson text against dictionaries.

Every word carrying an acute accent (U+0301) is looked up on goroh.pp.ua
(«Словозміна», which lists the stressed paradigm of the word's lemma, so
inflected forms can be checked) and, when goroh has nothing, in the Academic
Dictionary СУМ-20 on slovnyk.me. A dictionary token with two accents
(«ко́шту́є») means both stresses are allowed.

Results per word: confirmed, variant (ours is one of two allowed stresses),
differs (the dictionary has only other stresses), unconfirmed (not found).
A confirmed word can still be wrong in context when the page mixes lemmas or
cases (goroh's «мене» page includes «Мен», Maine); words with several allowed
stresses are listed so that they can be checked in context.

Run it with `lal audit <file>...` (it is the Ukrainian profile's check).
Pages are cached in ~/.cache/stress-audit; the first run takes several minutes.
"""

from __future__ import annotations

import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ACUTE = "́"
TOK = re.compile(r"[А-Яа-яІіЇїЄєҐґ’'ʼ́]+")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
DESCRIPTION = "Ukrainian stress marks against goroh.pp.ua and СУМ-20 (network, cached)"
CACHE = Path.home() / ".cache" / "stress-audit"


def norm(word: str) -> str:
    return re.sub(r"[’ʼ]", "'", word.lower())


def plain(word: str) -> str:
    return word.replace(ACUTE, "")


def variants(token: str) -> set[str]:
    """«ко́шту́є» → {«ко́штує», «кошту́є»}; a single-accent token maps to itself."""
    positions = [i for i, ch in enumerate(token) if ch == ACUTE]
    if len(positions) <= 1:
        return {token}
    bare = plain(token)
    out = set()
    for n, pos in enumerate(positions):
        index = pos - n  # position of the accent in the bare word
        out.add(bare[:index] + ACUTE + bare[index:])
    return out


def fetch(url: str, name: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = f"HTTP {error.code}"
    path.write_text(body, encoding="utf-8")
    time.sleep(0.4)
    return body


def forms_on(page: str) -> dict[str, set[str]]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    forms: dict[str, set[str]] = defaultdict(set)
    for token in TOK.findall(text):
        if ACUTE in token:
            for form in variants(norm(token)):
                forms[plain(form)].add(form)
    return forms


def lookup(word: str) -> tuple[set[str], str | None]:
    quote = urllib.parse.quote
    typographic = word.replace("'", "’")
    for site, query in (("goroh", typographic), ("goroh", word), ("СУМ-20", word)):
        base = f"https://goroh.pp.ua/{quote('Словозміна')}/" if site == "goroh" else "https://slovnyk.me/dict/newsum/"
        forms = forms_on(fetch(base + quote(query), f"{site}_{quote(query, safe='')}.html")).get(word, set())
        if forms:
            return forms, site
    return set(), None


def run(paths: list[Path], show_confirmed: bool = False) -> tuple[list[str], bool]:
    counts: Counter[str] = Counter()
    for path in paths:
        counts.update(norm(w) for w in TOK.findall(path.read_text(encoding="utf-8")) if ACUTE in w)
    results: dict[str, list[str]] = defaultdict(list)
    for i, word in enumerate(sorted(counts), 1):
        forms, source = lookup(plain(word))
        if not forms:
            status = "unconfirmed"
        elif word not in forms:
            status = "differs"
        elif len(forms) > 1:
            status = "several allowed"
        else:
            status = "confirmed"
        results[status].append(f"{word} ×{counts[word]}" + (f" — {source}: {', '.join(sorted(forms))}" if forms else ""))
        if i % 100 == 0:
            print(f"{i}/{len(counts)} checked", file=sys.stderr)

    report = [f"{len(counts)} stressed words: " + ", ".join(f"{len(v)} {k}" for k, v in results.items())]
    for status in ("differs", "unconfirmed", "several allowed") + (("confirmed",) if show_confirmed else ()):
        if results.get(status):
            report.append(f"{status} (check in context):" if status == "several allowed" else f"{status}:")
            report.extend(f"  {line}" for line in results[status])
    return report, bool(results.get("differs"))
