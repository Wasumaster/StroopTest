"""Funkcje narzędziowe dla eksperymentu Testu Stroopa.

Moduł ten pełni rolę warstwy infrastrukturalnej projektu. Odpowiada za:
  - wczytywanie i walidację pliku konfiguracyjnego (config.yaml),
  - konfigurację systemu logowania PsychoPy,
  - zbieranie danych demograficznych uczestnika przez systemowe okno GUI,
  - zapis zebranych wyników do pliku CSV,
  - ładowanie i walidację plików z bodźcami (stimulus CSV),
  - budowanie bezpiecznych, niezależnych od platformy ścieżek do plików projektu.

Wszystkie funkcje tego modułu są importowane i używane przez main.py.
Moduł ten nie zawiera żadnej logiki eksperymentalnej — jest wyłącznie pomocniczy.
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
    sekcje wymagane do prawidłowego działania eksperymentu. Walidowane są
    zarówno główne sekcje (experiment, gui, timing itd.) jak i ich
    szczegółowe klucze (np. wszystkie parametry czasowe).

    Parametry:
        file_path: Bezwzględna lub względna ścieżka do pliku config.yaml.

    Zwraca:
        Słownik (Dict) zawierający wszystkie parametry konfiguracyjne.

    Wyjątki:
        FileNotFoundError: Jeśli plik konfiguracyjny nie istnieje.
        ValueError: Jeśli brakuje wymaganych sekcji w pliku.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Plik konfiguracyjny nie został znaleziony: {file_path}"
        )

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

    # Walidacja szczegółowych parametrów czasowych (kluczowych dla poprawności eksperymentu)
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
    Katalog wynikowy jest tworzony automatycznie, jeśli jeszcze nie istnieje.

    Parametry:
        config: Pełny słownik konfiguracyjny wczytany z config.yaml.
    """
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

    # Wygenerowanie unikalnej nazwy pliku logu (np. stroop_log_20240101_120000.log)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(results_dir, f"stroop_log_{timestamp}.log")

    logging.LogFile(log_filename, level=log_level, filemode="w")
    logging.console.setLevel(log_level)

    logging.info(
        f"Logowanie zainicjowane. Plik: {log_filename}, "
        f"Poziom: {log_level_str}"
    )


def get_subject_data(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Wyświetla okno dialogowe i pobiera dane demograficzne od uczestnika.

    ID uczestnika jest generowane automatycznie w formacie: SUB_YYYYMMDD_HHMMSS,
    co zapewnia unikalność identyfikatora nawet dla badań przeprowadzanych tego
    samego dnia. Okno dialogowe prosi jedynie o podanie Wieku oraz wybór Płci
    z listy rozwijanej. Wiek jest walidowany (musi być dodatnią liczbą całkowitą).

    Parametry:
        config: Pełny słownik konfiguracyjny (używany do pobrania tytułu okna).

    Zwraca:
        Słownik z kluczami 'ID', 'Wiek', 'Płeć', lub None jeśli uczestnik
        kliknął Anuluj lub zamknął okno.
    """
    auto_id = "SUB_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    subject_info = {
        "Wiek": "",
        "Płeć": ["K", "M"],
    }

    dlg = gui.DlgFromDict(
        dictionary=subject_info,
        title=config["experiment"]["name"],
        order=["Wiek", "Płeć"],
    )

    if not dlg.OK:
        logging.warning("Uczestnik anulował dialog danych demograficznych.")
        return None

    # Walidacja wprowadzonego wieku — musi być liczbą całkowitą w przedziale 1–120
    try:
        age = int(subject_info["Wiek"])
        if age <= 0 or age > 120:
            raise ValueError()
    except (ValueError, TypeError):
        logging.error(f"Nieprawidłowy wiek: {subject_info['Wiek']}")
        raise ValueError(
            f"Wiek musi być liczbą całkowitą dodatnią (podano: "
            f"'{subject_info['Wiek']}')."
        )

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

    Funkcja jest wywoływana zarówno po zakończeniu eksperymentu (zapis finalny),
    jak i awaryjnie podczas naciśnięcia ESC lub wystąpienia wyjątku. Zawsze
    nadpisuje plik o tej samej nazwie — dzięki temu każde kolejne wywołanie
    (np. awaryjne) aktualizuje istniejący plik zamiast tworzyć nowy.

    Parametry:
        data: Lista słowników — każdy słownik zawiera wyniki jednej próby.
        filename: Podstawowa nazwa pliku wynikowego (bez ścieżki katalogu).
        config: Pełny słownik konfiguracyjny (do pobrania ścieżki katalogu).

    Zwraca:
        Pełną ścieżkę absolutną do zapisanego pliku CSV.
    """
    project_root = _get_project_root()
    results_dir = os.path.join(project_root, config["paths"]["results_dir"])
    os.makedirs(results_dir, exist_ok=True)

    filepath = os.path.join(results_dir, filename)

    # Definicja wszystkich kolumn w pliku wyjściowym CSV (kolejność zgodna ze standardem)
    fieldnames = [
        "subject_id", "age", "gender", "block", "trial_idx",
        "word", "color", "congruency", "expected_key", "pressed_key",
        "is_correct", "rt", "timestamp",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    logging.info(f"Wyniki zapisane do: {filepath} ({len(data)} prób)")
    return filepath


def load_trials(csv_path: str) -> List[Dict[str, str]]:
    """Ładuje i waliduje definicje prób z pliku CSV z bodźcami (stimulus).

    Upewnia się, że wejściowy plik CSV posiada wszystkie kolumny wymagane
    do poprawnego przeprowadzenia eksperymentu: word, color, congruency, corr_ans.
    Walidacja jest wykonywana przez porównanie zbiorów nagłówków.

    Parametry:
        csv_path: Ścieżka do pliku CSV z definicjami bodźców.

    Zwraca:
        Listę słowników, gdzie każdy słownik to jedna próba eksperymentalna.

    Wyjątki:
        FileNotFoundError: Jeśli plik CSV nie istnieje.
        ValueError: Jeśli brakuje wymaganych kolumn lub plik jest pusty.
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
    """Generuje unikalną nazwę pliku wynikowego z dokładnym znacznikiem czasu.

    Użycie znacznika czasu zabezpiecza przed przypadkowym nadpisaniem pliku,
    nawet jeśli ten sam uczestnik uruchomi eksperyment wielokrotnie tego samego dnia.

    Parametry:
        subject_id: Unikalne ID badanego (np. SUB_20240101_120000).

    Zwraca:
        Złożona nazwa pliku, np. SUB_20240101_120000_Stroop_20240101_1200.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{subject_id}_Stroop_{timestamp}.csv"


def build_trial_path(config: Dict[str, Any], filename_key: str) -> str:
    """Buduje absolutną ścieżkę do pliku z definicjami bodźców (stimulus CSV).

    Używa funkcji _get_project_root(), dzięki czemu ścieżka jest zawsze poprawna
    niezależnie od katalogu roboczego, z którego uruchomiono skrypt.

    Parametry:
        config: Pełna konfiguracja systemu.
        filename_key: Klucz z sekcji 'paths' wskazujący na konkretny plik
                      (np. 'main_trials_file' lub 'training_trials_file').

    Zwraca:
        Pełna, bezwzględna ścieżka do pliku CSV z bodźcami.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["stimulus_dir"],
        config["paths"][filename_key],
    )


def build_instruction_image_path(config: Dict[str, Any], image_filename: str) -> str:
    """Buduje absolutną ścieżkę do pliku graficznego z instrukcją.

    Instrukcje eksperymentu są przechowywane jako pliki graficzne (JPG) w katalogu
    wskazanym przez klucz 'instructions_dir' w konfiguracji. Funkcja łączy katalog
    główny projektu, katalog instrukcji i podaną nazwę pliku w jedną ścieżkę.

    Parametry:
        config: Pełna konfiguracja systemu.
        image_filename: Nazwa pliku graficznego (np. 'instrukcja_1.jpg').

    Zwraca:
        Pełna, bezwzględna ścieżka do pliku graficznego instrukcji.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["instructions_dir"],
        image_filename,
    )


def _get_project_root() -> str:
    """Ustala absolutną ścieżkę do głównego katalogu projektu.

    Zakłada, że skrypt (utils.py) zawsze znajduje się wewnątrz folderu 'src/',
    dlatego korzeń projektu to katalog nadrzędny względem 'src/'.
    Funkcja ta zapewnia przenośność projektu — działa poprawnie niezależnie
    od systemu operacyjnego i lokalizacji projektu na dysku.

    Zwraca:
        Absolutną ścieżkę do katalogu głównego projektu (np. StroopTest-1/).
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
