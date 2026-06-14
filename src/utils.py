"""Utility functions for the Stroop Task experiment.

Handles configuration loading, logging setup, participant data collection,
results saving, and trial loading with validation.
"""

import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from psychopy import gui, logging


def load_config(file_path: str) -> Dict[str, Any]:
    """Load and validate the YAML configuration file.

    Args:
        file_path: Absolute or relative path to the config.yaml file.

    Returns:
        Dictionary containing all configuration parameters.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required configuration sections are missing.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Plik konfiguracyjny nie został znaleziony: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    required_sections = [
        "experiment", "gui", "timing", "keys", "thresholds", "paths", "messages"
    ]
    for section in required_sections:
        if section not in config:
            raise ValueError(
                f"Brak wymaganej sekcji '{section}' w pliku konfiguracyjnym."
            )

    required_timing = [
        "fixation_cross", "stimulus_timeout", "isi_min", "isi_max",
        "feedback_duration"
    ]
    for key in required_timing:
        if key not in config["timing"]:
            raise ValueError(
                f"Brak wymaganego parametru timing.{key} w konfiguracji."
            )

    if "response_mapping" not in config["keys"]:
        raise ValueError(
            "Brak wymaganego parametru keys.response_mapping w konfiguracji."
        )

    return config


def setup_logging(config: Dict[str, Any]) -> None:
    """Configure PsychoPy logging based on experiment settings.

    Creates a log file in the results directory with a timestamped name
    and sets the console log level.

    Args:
        config: Full configuration dictionary loaded from config.yaml.
    """
    log_level_str = config["experiment"].get("log_level", "info").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(log_level_str, logging.INFO)

    project_root = _get_project_root()
    results_dir = os.path.join(project_root, config["paths"]["results_dir"])
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(results_dir, f"stroop_log_{timestamp}.log")

    logging.LogFile(log_filename, level=log_level, filemode="w")
    logging.console.setLevel(log_level)

    logging.info(
        f"Logowanie zainicjowane. Plik: {log_filename}, "
        f"Poziom: {log_level_str}"
    )


def get_subject_data(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Collect and validate participant demographic data via a GUI dialog.

    ID is generated automatically (SUB_YYYYMMDD_HHMMSS).
    The dialog asks only for age and gender.

    Args:
        config: Full configuration dictionary (reserved for future GUI params).

    Returns:
        Dictionary with keys 'ID', 'Wiek', 'Płeć', or None if cancelled.
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
    """Save collected trial data to a CSV file in the results directory.

    Creates the results directory if it doesn't exist. Uses the filename
    format: {ID}_Stroop_YYYYMMDD_HHMM.csv

    Args:
        data: List of dictionaries, each representing one trial's results.
        filename: Base filename (without directory path).
        config: Full configuration dictionary for paths.

    Returns:
        The full path to the saved CSV file.
    """
    project_root = _get_project_root()
    results_dir = os.path.join(project_root, config["paths"]["results_dir"])
    os.makedirs(results_dir, exist_ok=True)

    filepath = os.path.join(results_dir, filename)

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
    """Load and validate trial definitions from a CSV file.

    Verifies that the CSV contains all required columns:
    word, color, congruency, corr_ans.

    Args:
        csv_path: Path to the CSV file with trial definitions.

    Returns:
        List of dictionaries, each representing one trial row.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns are missing or file is empty.
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
    """Generate a timestamped results filename for the given subject.

    Args:
        subject_id: Participant's ID string.

    Returns:
        Filename in format: {ID}_Stroop_YYYYMMDD_HHMM.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{subject_id}_Stroop_{timestamp}.csv"


def build_trial_path(config: Dict[str, Any], filename_key: str) -> str:
    """Build absolute path to a stimulus CSV file.

    Args:
        config: Full configuration dictionary.
        filename_key: Key in config['paths'] for the target file.

    Returns:
        Absolute path to the stimulus CSV file.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["stimulus_dir"],
        config["paths"][filename_key],
    )


def build_instruction_path(config: Dict[str, Any], filename_key: str) -> str:
    """Build absolute path to an instruction text file.

    Args:
        config: Full configuration dictionary.
        filename_key: Key in config['paths'] for the target file.

    Returns:
        Absolute path to the instruction text file.
    """
    project_root = _get_project_root()
    return os.path.join(
        project_root,
        config["paths"]["instructions_dir"],
        config["paths"][filename_key],
    )


def load_instruction_text(file_path: str) -> str:
    """Load instruction text content from a file.

    Args:
        file_path: Path to the instruction .txt file.

    Returns:
        The text content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
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
    """Determine the project root directory.

    Assumes the src/ directory is directly under the project root.

    Returns:
        Absolute path to the project root.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
