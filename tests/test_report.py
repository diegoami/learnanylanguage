from lal import report

TRANSCRIPT = """\
**Teacher** (voice): Lekcja skończona.

**Learner** (text): REPORT

**Teacher** (text): **LESSON_REPORT**
Mode: grammar drill
**Items:**
- 1: independent — Czytałem książkę.
- 2: after a cue — Byłem w domu.
- 3: corrected — Piłem kawę.
- 4: not reached — 
Corrections:
- «Piłam kawę» → «Piłem kawę» — masculine past tense ending
Words given by the teacher:
- None
END_LESSON_REPORT
"""


def test_report_is_parsed_with_evidence_labels():
    found, errors, warnings = report.parse(report.extract(TRANSCRIPT))
    assert errors == [] and warnings == []
    assert found.mode == "grammar drill"
    assert [o for _, o, _ in found.items] == ["independent", "after a cue", "corrected", "not reached"]
    assert found.words == []
    table = report.render(found)
    assert "| 2 | after a cue | cued | Byłem w domu. |" in table


def test_report_flags_scores_and_missing_sections():
    body = "Mode: writing\nItems:\n- Text: independent — 8/10, great job\n- Follow-up: excellent\n"
    found, errors, warnings = report.parse(body)
    assert any("allowed outcome" in e for e in errors)
    assert any("Corrections:" in e for e in errors)
    assert any("forbidden" in w for w in warnings)


def test_the_template_in_a_package_is_not_a_report():
    template = "LESSON_REPORT\nItems:\n- <Item number, word, or text>: …\nEND_LESSON_REPORT\n"
    assert report.extract(template) is None
