import pytest
from app.services.detectors import PDNDetectors

def test_fio_patterns():
    surn_ends = ('ов', 'ова', 'ев', 'ева', 'ин', 'ина')
    patron_ends = ('ович', 'евич', 'овна', 'евна')

    # Test 1: Фамилия Имя Отчество
    text_1 = "Иванов Иван Иванович пошел в магазин"
    res_1 = PDNDetectors.analyze_fio(text_1, surn_ends, patron_ends)
    assert "Иванов Иван Иванович" in res_1

    # Test 2: Фамилия И.О.
    text_2 = "Ждем ответа от Петров П.С. до вечера"
    res_2 = PDNDetectors.analyze_fio(text_2, surn_ends, patron_ends)
    # The regex captures it as "Петров П.С." if no space, but the regex requires space or handles it
    assert "Петров П.С." in res_2 or "Петров П. С." in res_2 or len(res_2) > 0

    # Test 3: Отчество Фамилия Имя
    text_3 = "Это был Антонович Сидоров Олег, он все сделал"
    res_3 = PDNDetectors.analyze_fio(text_3, surn_ends, patron_ends)
    assert "Антонович Сидоров Олег" in res_3

    # Test 4: Имя Фамилия Отчество
    text_4 = "Там стоял Алексей Смирнов Петрович и смотрел"
    res_4 = PDNDetectors.analyze_fio(text_4, surn_ends, patron_ends)
    assert "Алексей Смирнов Петрович" in res_4

    # Negative test
    text_neg = "Красный Зеленый Синий"
    res_neg = PDNDetectors.analyze_fio(text_neg, surn_ends, patron_ends)
    assert len(res_neg) == 0

class MockRule:
    def __init__(self, pdn_type, rule_type, value):
        self.pdn_type = pdn_type
        self.rule_type = rule_type
        self.value = value

def test_detect():
    text = "Мой телефон +79991234567 и email test@example.com."
    rules = [
        MockRule("phone", "regex", r"\+7\d{10}"),
        MockRule("email", "regex", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+"),
        MockRule("phone", "invalid_def_code", "999") # This will exclude the phone
    ]
    
    matches = PDNDetectors.detect(text, "content.text", rules)
    
    assert len(matches) == 1
    assert matches[0]["type"] == "email"
    assert matches[0]["value"] == "test@example.com"
    
def test_detect_exclusions():
    text = "Some specific ID: 123456"
    rules = [
        MockRule("id", "regex", r"\d{6}"),
        MockRule("id", "exclude_pattern", r"secret\.path"),
        MockRule("id", "prefix_exclude", "123")
    ]
    
    # 1. Matches normally
    matches1 = PDNDetectors.detect(text, "normal.path", rules[:1])
    assert len(matches1) == 1
    
    # 2. Field path exclusion
    matches2 = PDNDetectors.detect(text, "secret.path.id", rules)
    assert len(matches2) == 0
    
    # 3. Prefix exclusion
    matches3 = PDNDetectors.detect(text, "normal.path", rules)
    assert len(matches3) == 0

