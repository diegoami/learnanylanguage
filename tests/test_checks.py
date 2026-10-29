from lal.checks import es_punctuation, uk_stress


def test_spanish_punctuation():
    problems = es_punctuation.scan("Donde esta la estacion?\n¿Que desea?\n¿Dónde está?\n"
                                   "- ¿Cuánto es? — How much is it?\n")
    assert len(problems) == 2
    assert "missing «¿»" in problems[0] and "«¿Qué»" in problems[1]


def test_ukrainian_stress_variants():
    assert uk_stress.variants("ко́шту́є") == {"ко́штує", "кошту́є"}
    assert uk_stress.plain("ка́ва") == "кава"
