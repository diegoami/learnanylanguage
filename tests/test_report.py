from lal import lesson, report

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


def test_a_report_inside_the_generated_transcript_reads_as_a_bare_one():
    """Issue #2: the template's note mentions LESSON_REPORT and must not start a block."""
    header = lesson.TRANSCRIPT_TEMPLATE.format(
        track="pl-first-steps", label="1", mode="grammar drill", version="g3",
        language="Polish", channel="text", report=lesson.REPORT_NOTE)
    assert "LESSON_REPORT" in header
    turns = "**Teacher** (text): Proszę powiedzieć to w czasie przeszłym.\n\n**Learner** (text): Czytałem.\n\n"
    bare = report.parse(report.extract(TRANSCRIPT))
    wrapped = report.parse(report.extract(header + turns + TRANSCRIPT))
    assert wrapped[1:] == bare[1:] == ([], [])
    assert wrapped[0] == bare[0]


def test_the_last_of_several_reports_wins():
    second = TRANSCRIPT.replace("Mode: grammar drill", "Mode: vocabulary drill")
    assert report.parse(report.extract(TRANSCRIPT + second))[0].mode == "vocabulary drill"
