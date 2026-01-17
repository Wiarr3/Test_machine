import requests
import json

URL = "http://127.0.0.1:8000/run_tests_local"


def run_test_case(name, class_code, test_code, expected_status):
    print(f"\n--- SCENARIUSZ: {name} ---")
    payload = {
        "class_code": class_code,
        "test_code": test_code
    }

    try:
        response = requests.post(URL, json=payload)
        result = response.json()

        print(f"Przewidywany status: {expected_status}")
        print(f"Otrzymany status: {result['status']}")
        print(f"Exit Code: {result['exit_code']}")

        if result['status'] == "SUCCESS":
            print("Wynik: [Ścieżka A] Kod zostanie zapisany w pamięci.")
        else:
            print("Wynik: [Ścieżka B] Logi zostaną wysłane do AI Reviewera.")
            # Wyświetlamy tylko kawałek logów dla czytelności
            print(f"Logi (skrócone): {result['logs'].splitlines()[-1]}")

    except Exception as e:
        print(f"Błąd połączenia: {e}")


# --- DEFINICJE PAYLOADÓW ---

# 1. PEŁNY SUKCES (Path A)
run_test_case(
    "Poprawny kod",
    "class Greeter:\n    def say_hi(self, name):\n        return f'Hello {name}'",
    "from class_to_test import Greeter\ndef test_hi():\n    g = Greeter()\n    assert g.say_hi('User') == 'Hello User'",
    "SUCCESS"
)

# 2. BŁĄD LOGICZNY (Path B)
# Kod działa, ale test zawodzi (np. zły wynik dodawania)
run_test_case(
    "Błąd logiczny (AssertionError)",
    "class Calc:\n    def add(self, a, b):\n        return a * b  # Błąd: mnożenie zamiast dodawania",
    "from class_to_test import Calc\ndef test_add():\n    c = Calc()\n    assert c.add(2, 2) == 4",
    # Ten test akurat przejdzie (2*2=4), ale 2+3=5 już nie
    "SUCCESS"  # Musimy dać test, który na pewno padnie:
)

run_test_case(
    "Błąd logiczny - Fałszywy wynik",
    "class Calc:\n    def add(self, a, b):\n        return a - b",
    "from class_to_test import Calc\ndef test_add():\n    c = Calc()\n    assert c.add(5, 5) == 10",
    "FAILURE"
)

# 3. BŁĄD SKŁADNI (Path B)
# AI Dev wygenerował kod z błędem składni (brak dwukropka)
run_test_case(
    "Błąd składni (SyntaxError)",
    "class Error\n    pass  # Brak dwukropka po nazwie klasy",
    "from class_to_test import Error\ndef test_err():\n    assert True",
    "FAILURE"
)

# 4. BRAKUJĄCA METODA (Path B)
# Test próbuje wywołać metodę, której AI Dev nie napisał
run_test_case(
    "Błąd atrybutu (AttributeError)",
    "class Empty:\n    pass",
    "from class_to_test import Empty\ndef test_method():\n    e = Empty()\n    e.run()  # Metoda 'run' nie istnieje",
    "FAILURE"
)