"""Funkcje narzędziowe dla eksperymentu Testu Stroopa.

Moduł ten obsługuje ładowanie konfiguracji z pliku YAML, inicjalizację systemu
logowania PsychoPy, zbieranie danych demograficznych uczestnika przez GUI,
zapis wyników do plików CSV oraz ładowanie i walidację plików z bodźcami (trials).
"""

import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from psychopy import gui, logging


def load_config(file_path: str) -> Dict[str, Any]:
    """Wczytuje i waliduje plik konfiguracyjny YAML.

    Funkcja upewnia się, że plik istnieje oraz zawiera wszystkie niezbędne
    sekcje wymagane do prawidłowego działania eksperymentu (np. czasy, klawisze).

    Parametry:
        file_path: Bezwzględna lub względna ścieżka do pliku config.yaml.

    Zwraca:
        Słownik (Dict) zawierający wszystkie parametry konfiguracyjne.

    Wyjątki:
        FileNotFoundError: Jeśli plik konfiguracyjny nie istnieje.
        ValueError: Jeśli brakuje wymaganych sekcji w pliku.
    """
    # Sprawdzenie czy plik istnieje, by uniknąć błędu w trakcie odczytu
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Plik konfiguracyjny nie został znaleziony: {file_path}"
        )

    # Odczyt pliku YAML
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Lista głównych sekcji, które muszą znajdować się w pliku config.yaml
    required_sections = [
        "experiment", "gui", "timing", "keys", "thresholds", "paths", "messages"
    ]
    for section in required_sections:
        if section not in config:
            raise ValueError(
                f"Brak wymaganej sekcji '{section}' w pliku konfiguracyjnym."
            )

    # Walidacja szczegółowych parametrów czasowych (kluczowych dla eksperymentu)
    required_timing = [
        "fixation_cross", "stimulus_timeout", "isi_min", "isi_max",
        "feedback_duration"
    ]
    for key in required_timing:
        if key not in config["timing"]:
            raise ValueError(
                f"Brak wymaganego parametru timing.{key} w konfiguracji."
            )

    # Walidacja definicji klawiszy (mapowanie klawiszy na kolory)
    if "response_mapping" not in config["keys"]:
        raise ValueError(
            "Brak wymaganego parametru keys.response_mapping w konfiguracji."
        )

    return config


def setup_logging(config: Dict[str, Any]) -> None:
    """Konfiguruje system logowania z biblioteki PsychoPy.

    Tworzy plik logów w katalogu results z unikalną nazwą opartą o datę i czas.
    Ustawia poziom logowania w konsoli zgodnie z ustawieniami z konfiguracji.

    Parametry:
        config: Pełny słownik konfiguracyjny wczytany z config.yaml.
    """
    # Odczyt poziomu logowania z konfiguracji (domyślnie INFO)
    log_level_str = config["experiment"].get("log_level", "info").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(log_level_str, logging.INFO)

    # Ustalenie ścieżki do katalogu z wynikami i utworzenie go, jeśli nie istnieje
    project_root = _get_project_root()
    results_dir = os.path.join(project_root, config["paths"]["results_dir"])
    os.makedirs(results_dir, exist_ok=True)

    # Wygenerowanie unikalnej nazwy pliku log (np. stroop_log_20240101_120000.log)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(results_dir, f"stroop_log_{timestamp}.log")

    # Ustawienie pliku logującego i globalnego poziomu w konsoli
    logging.LogFile(log_filename, level=log_level, filemode="w")
    logging.console.setLevel(log_level)

    logging.info(
        f"Logowanie zainicjowane. Plik: {log_filename}, "
        f"Poziom: {log_level_str}"
    )


def get_subject_data(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Wyświetla okno dialogowe i pobiera dane demograficzne od uczestnika.

    ID uczestnika jest generowane w tle automatycznie w formacie: SUB_YYYYMMDD_HHMMSS.
    Okno dialogowe prosi jedynie o podanie Wieku oraz wybór Płci z listy.
    Dane są dodatkowo walidowane (np. sprawdzane jest czy wiek to liczba dodatnia).

    Parametry:
        config: Pełny słownik konfiguracyjny (wykorzystywany do pobrania nazwy w tytule okna).

    Zwraca:
        Słownik z kluczami 'ID', 'Wiek', 'Płeć' lub None, jeśli uczestnik kliknął Anuluj.
    """
    # Automatyczne generowanie bezpiecznego i unikalnego identyfikatora badanego
    auto_id = "SUB_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    # Struktura danych dla okna dialogowego PsychoPy
    subject_info = {
        "Wiek": "",
        "Płeć": ["K", "M"], # Lista rozwijana do wyboru płci
    }

    # Uruchomienie okna dialogowego
    dlg = gui.DlgFromDict(
        dictionary=subject_info,
        title=config["experiment"]["name"],
        order=["Wiek", "Płeć"],
    )

    # Jeśli użytkownik kliknął Anuluj lub nacisnął ESC w oknie
    if not dlg.OK:
        logging.warning("Uczestnik anulował dialog danych demograficznych.")
        return None

    # Walidacja wprowadzonego wieku
    try:
        age = int(subject_info["Wiek"])
        if age <= 0 or age > 120:
            raise ValueError()
    except (ValueError, TypeError):
        logging.error(f"Nieprawidłowy wiek: {subject_info['Wiek']}")
        # Rzuca błąd widoczny w konsoli, co uniemożliwia uruchomienie błędnego badania
        raise ValueError(
            f"Wiek musi być liczbą całkowitą dodatnią (podano: "
            f"'{subject_info['Wiek']}')."
        )

    # Zapis danych poprawnie zwalidowanych
    subject_info["Wiek"] = str(age)
    subject_info["ID"] = auto_id

    logging.info(
        f"Dane uczestnika — ID: {auto_id}, "
        f"Wiek: {subject_info['Wiek']}, Płeć: {subject_info['Płeć']}"
    )

    return subject_info


def save_results(
    data: List[Dict[str, Any]],
    filename: str,
    config: Dict[str, Any],
) -> str:
    """Zapisuje zebrane dane z prób do pliku CSV w katalogu wyników.

    Tworzy katalog wynikowy jeśli ten nie istnieje. Nadpisuje plik o tej samej
    nazwie (co jest kluczowe przy awaryjnym zapisywaniu danych przez ESC).

    Parametry:
        data: Lista słowników, z których każdy reprezentuje wyniki z jednej próby.
        filename: Podstawowa nazwa pliku (bez ścieżki do katalogu).
        config: Pełny słownik konfiguracyjny (do pobrania ścieżki katalogu).

    Zwraca:
        Pełną ścieżkę absolutną do zapisanego pliku CSV.
    """
    project_root = _get_project_root()
    results_dir = os.path.join(project_root, config["paths"]["results_dir"])
    os.makedirs(results_dir, exist_ok=True) # Zabezpieczenie przed brakiem folderu

    filepath = os.path.join(results_dir, filename)

    # Definicja wszystkich wymaganych kolumn w pliku wyjściowym CSV
    fieldnames = [
        "subject_id", "age", "gender", "block", "trial_idx",
        "word", "color", "congruency", "expected_key", "pressed_key",
        "is_correct", "rt", "timestamp",
    ]

    # Zapis danych korzystając z wbudowanego modułu csv
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader() # Zapisuje nazwy kolumn
        for row in data:
            writer.writerow(row) # Zapisuje poszczególne próby

    logging.info(f"Wyniki zapisane do: {filepath} ({len(data)} prób)")
    return filepath


def load_trials(csv_path: str) -> List[Dict[str, str]]:
    """Ładuje i waliduje definicje prób z pliku CSV z bodźcami (stimulus).

    Upewnia się, że wejściowy plik CSV posiada wszystkie kolumny wymagane
    do poprawnego przeprowadzenia eksperymentu: word, color, congruency, corr_ans.

    Parametry:
        csv_path: Ścieżka do pliku CSV z definicjami bodźców.

    Zwraca:
        Listę słowników, gdzie każdy słownik to jedna próba eksperymentalna.

    Wyjątki:
        FileNotFoundError: Jeśli plik CSV nie istnieje.
        ValueError: Jeśli brakuje wymaganych kolumn w pliku.
    """
    if not os.path.isfile(csv_path):
        logging.error(f"Plik bodźców nie istnieje: {csv_path}")
        raise FileNotFoundError(
            f"Plik bodźców nie został znaleziony: {csv_path}"
        )

    required_columns = {"word", "color", "congruency", "corr_ans"}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            logging.error(f"Plik bodźców jest pusty: {csv_path}")
            raise ValueError(f"Plik bodźców jest pusty: {csv_path}")

        # Weryfikacja nagłówków CSV za pomocą porównania zbiorów (set)
        actual_columns = set(reader.fieldnames)
        missing = required_columns - actual_columns
        if missing:
            logging.error(
                f"Brak wymaganych kolumn w {csv_path}: {missing}"
            )
            raise ValueError(
                f"Brak wymaganych kolumn w pliku {csv_path}: "
                f"{', '.join(sorted(missing))}"
            )

        trials = list(reader)

    if not trials:
        logging.error(f"Plik bodźców nie zawiera prób: {csv_path}")
        raise ValueError(
            f"Plik bodźców nie zawiera żadnych prób: {csv_path}"
        )

    logging.info(f"Załadowano {len(trials)} prób z: {csv_path}")
    return trials


def generate_results_filename(subject_id: str) -> str:
    """Generuje nazwę pliku wynikowego z dokładnym timestampem.

    Zabezpiecza to przed przypadkowym nadpisaniem plików, nawet przy tym samym ID.

    Parametry:
        subject_id: Unikalne ID badanego.

    Zwraca:
        Złożona nazwa pliku: np. SUB_2026..._Stroop_2026..._HHMM.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{subject_id}_Stroop_{timestamp}.csv"


def build_trial_path(config: Dict[str, Any], filename_key: str) -> str:
    """Buduje absolutną ścieżkę do pliku z warunkami badawczymi (stimulus).

    Odwołuje się dynamicznie do katalogu nadrzędnego projektu, zapewniając
    że skrypt zadziała na każdym komputerze, niezależnie od miejsca rozpakowania.

    Parametry:
        config: Pełna konfiguracja systemu.
        filename_key: Klucz z sekcji 'paths' wskazujący na konkretny plik (np. 'main_trials_file').

    Zwraca:
        Pełna, bezwzględna ścieżka do pliku.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["stimulus_dir"],
        config["paths"][filename_key],
    )


def build_instruction_path(config: Dict[str, Any], filename_key: str) -> str:
    """Buduje absolutną ścieżkę do pliku tekstowego z instrukcją.

    Parametry:
        config: Pełna konfiguracja systemu.
        filename_key: Klucz z sekcji 'paths' wskazujący na instrukcję (np. 'welcome_file').

    Zwraca:
        Pełna, bezwzględna ścieżka do pliku instrukcji.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["instructions_dir"],
        config["paths"][filename_key],
    )


def load_instruction_text(file_path: str) -> str:
    """Wczytuje treść instrukcji z pliku tekstowego do zmiennej.

    Parametry:
        file_path: Bezwzględna ścieżka do pliku instrukcji .txt.

    Zwraca:
        Pełną treść pliku jako jeden łańcuch znaków (string).

    Wyjątki:
        FileNotFoundError: Jeśli plik instrukcji nie istnieje.
    """
    if not os.path.isfile(file_path):
        logging.error(f"Plik instrukcji nie istnieje: {file_path}")
        raise FileNotFoundError(
            f"Plik instrukcji nie został znaleziony: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    logging.info(f"Załadowano instrukcję z: {file_path}")
    return text


def _get_project_root() -> str:
    """Ustalanie absolutnej ścieżki do głównego katalogu projektu.

    Zakłada, że skrypty uruchomieniowe (w tym utils.py) zawsze znajdują się 
    wewnątrz folderu `src/`, dlatego wykonuje dwukrotne pobranie katalogu rodzica.

    Zwraca:
        Absolutną ścieżkę do katalogu `StroopTest-1`.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
