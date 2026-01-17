import requests
import json

URL = "http://127.0.0.1:8000/run_tests_docker"


def run_scenario(name, class_code, test_code, expected_result):
    print(f"\n{'=' * 20}\nSCENARIUSZ: {name}\n{'=' * 20}")
    payload = {
        "class_code": class_code,
        "test_code": test_code
    }

    try:
        response = requests.post(URL, json=payload)
        result = response.json()

        print(f"Oczekiwany wynik: {expected_result}")
        print(f"Otrzymany status: {result['status']}")
        print(f"Exit Code: {result['exit_code']}")

        if result['exit_code'] == 0:
            print(">>> WYNIK: [Ścieżka A] Sukces. Kod trafia do pamięci.")
        else:
            print(">>> WYNIK: [Ścieżka B] Błąd. Logi wysyłane do AI Reviewera.")
            # Pokazujemy ostatnią linię logów (zazwyczaj opis błędu w pytest)
            error_line = [l for l in result['logs'].split('\n') if 'E   ' in l]
            if error_line:
                print(f"Szczegóły błędu: {error_line[0]}")

    except Exception as e:
        print(f"Błąd połączenia z Maszyną Testującą: {e}")


# --- 1. SCENARIUSZ: SUKCES (Path A) ---
run_scenario(
    "Pełny sukces - Logika poprawna",
    "class AuthService:\n    def check_pass(self, p):\n        return p == 'secret123'",
    "from class_to_test import AuthService\ndef test_auth():\n    a = AuthService()\n    assert a.check_pass('secret123') is True",
    "SUCCESS (Exit Code 0)"
)

# --- 2. SCENARIUSZ: BŁĄD LOGICZNY (Path B) ---
run_scenario(
    "Błąd logiczny - Test zawodzi",
    "class Wallet:\n    def __init__(self):\n        self.balance = 100\n    def spend(self, amt):\n        self.balance += amt  # BŁĄD: dodaje zamiast odejmować",
    "from class_to_test import Wallet\ndef test_spend():\n    w = Wallet()\n    w.spend(50)\n    assert w.balance == 50",
    "FAILURE (Exit Code 1)"
)

# --- 3. SCENARIUSZ: CRASH KODU (Path B) ---
run_scenario(
    "Błąd wykonania - ZeroDivisionError",
    "class MathOps:\n    def divide(self, a, b):\n        return a / b",
    "from class_to_test import MathOps\ndef test_div_zero():\n    m = MathOps()\n    m.divide(10, 0)",
    "FAILURE (Exit Code 1)"
)

# --- 4. SCENARIUSZ: BŁĄD SKŁADNI (Path B) ---
run_scenario(
    "Błąd składni AI Deva",
    "class Broken\n    def __init__(self): pass",  # Brak dwukropka
    "from class_to_test import Broken\ndef test_init():\n    b = Broken()",
    "FAILURE (Exit Code 2/4)"
)

# # --- 5. SCENARIUSZ: TIMEOUT / PĘTLA (Path B) ---
# run_scenario(
#     "Zabezpieczenie - Nieskończona pętla",
#     "class Loop:\n    def hang(self):\n        while True: pass",
#     "from class_to_test import Loop\ndef test_hang():\n    l = Loop()\n    l.hang()",
#     "FAILURE (Exit Code 999 - Timeout)"
# )