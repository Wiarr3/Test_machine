# 1. BASE IMAGE: Używamy minimalnego obrazu Pythona.
# Alpine jest bardzo małe, ale często wymaga instalacji dodatkowych pakietów.
# Zamiast tego, użyjemy obrazu 'slim' dla lepszej kompatybilności z PyPI.
FROM python:3.11-slim

# 2. KONFIGURACJA ŚRODOWISKA: Ustawienie zmiennej środowiskowej dla Pythona.
ENV PYTHONUNBUFFERED 1

# 3. ZABEZPIECZENIA: Tworzenie nieuprzywilejowanego użytkownika.
# Jest to kluczowy krok w minimalizacji szkód, jeśli kod się "wydostanie".
RUN useradd --create-home appuser
USER appuser

# 4. KOD PROJEKTU: Ustawienie katalogu roboczego.
# W tym katalogu Twój serwis FastAPI zamontuje kod do przetestowania.
WORKDIR /app/code

# 5. ZALEŻNOŚCI: Instalacja jedynej wymaganej biblioteki - pytest.
# Całe środowisko jest celowo minimalistyczne.
RUN pip install pytest

# 6. DOMYŚLNA KOMENDA: Definiowanie domyślnej komendy dla kontenera.
# Kontener jest przeznaczony do uruchamiania testów.
# Gdy serwis FastAPI wywoła Dockera, użyje komendy 'pytest' wraz z ścieżką do pliku.
CMD ["pytest"]