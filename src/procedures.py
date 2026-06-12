"""Experimental procedures for the Stroop Task.

Contains all trial-level and block-level logic: stimulus display, response
collection, pseudorandomization, feedback, and the training loop with
accuracy gating.
"""

import copy
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from psychopy import core, event, logging, visual


# ---------------------------------------------------------------------------
# Color name-to-RGB mapping for PsychoPy color space [-1, 1]
# ---------------------------------------------------------------------------
COLOR_MAP: Dict[str, List[float]] = {
    "red": [1.0, -1.0, -1.0],
    "green": [-1.0, 0.6, -1.0],
    "blue": [-1.0, -1.0, 1.0],
}


def _check_quit(
    keys: List[str],
    quit_key: str,
    window: visual.Window,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Check if the quit key was pressed and handle graceful shutdown.

    Args:
        keys: List of key names that were pressed.
        quit_key: The configured quit key (e.g. 'escape').
        window: The PsychoPy Window to close.
        results: Collected results to save before exiting.
        save_fn: Reference to save_results function.
        save_args: Tuple of (filename, config) for save_fn.
    """
    if quit_key in keys:
        logging.warning("Klawisz ESC wykryty — przerywanie eksperymentu.")
        if results is not None and save_fn is not None and save_args is not None:
            try:
                save_fn(results, *save_args)
                logging.info("Wyniki awaryjne zapisane pomyślnie.")
            except Exception as e:
                logging.error(f"Błąd zapisu awaryjnego: {e}")
        window.close()
        core.quit()


def show_screen(
    window: visual.Window,
    text_content: str,
    wait_key: str,
    config: Dict[str, Any],
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Display a full-screen text and wait for a specific key to continue.

    Continuously checks for the quit key (ESC) while waiting.

    Args:
        window: The PsychoPy Window instance.
        text_content: The text string to display.
        wait_key: Key name that advances to the next screen.
        config: Full configuration dictionary.
        results: Collected results (for emergency save on ESC).
        save_fn: Reference to the save_results function.
        save_args: Tuple of (filename, config) for save_fn.
    """
    quit_key = config["keys"]["quit"]
    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]

    stim = visual.TextStim(
        win=window,
        text=text_content,
        color=text_color,
        font=font_name,
        height=0.04,
        wrapWidth=1.5,
        units="norm",
    )
    stim.draw()
    window.flip()

    while True:
        pressed = event.waitKeys(keyList=[wait_key, quit_key])
        if pressed is None:
            continue
        _check_quit(
            pressed, quit_key, window, results, save_fn, save_args,
        )
        if wait_key in pressed:
            break


def run_trial(
    window: visual.Window,
    trial_data: Dict[str, str],
    config: Dict[str, Any],
    is_training: bool = False,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> Dict[str, Any]:
    """Execute a single Stroop trial with the full timeline.

    Timeline:
        1. Jittered ISI (blank screen)
        2. Fixation cross (+)
        3. Stimulus presentation with RT clock reset
        4. Response collection (or timeout)
        5. Data recording
        6. Feedback (training only)

    Args:
        window: PsychoPy Window instance.
        trial_data: Dict with keys: word, color, congruency, corr_ans.
        config: Full configuration dictionary.
        is_training: Whether to show feedback after the trial.
        results: Accumulated results list (for ESC emergency save).
        save_fn: Reference to save_results function.
        save_args: Tuple of (filename, config) for save_fn.

    Returns:
        Dictionary with trial result data (all columns for the output CSV).
    """
    quit_key = config["keys"]["quit"]
    timing = config["timing"]
    response_mapping = config["keys"]["response_mapping"]
    valid_keys = list(response_mapping.keys()) + [quit_key]
    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]
    font_size = config["gui"]["font_size"]

    word = trial_data["word"]
    color_name = trial_data["color"]
    corr_ans = trial_data["corr_ans"]

    stimulus_color = COLOR_MAP.get(color_name, text_color)

    # --- 1. Jittered ISI ---
    isi_duration = random.uniform(timing["isi_min"], timing["isi_max"])
    window.flip()
    _isi_with_escape(
        isi_duration, quit_key, window, results, save_fn, save_args,
    )

    # --- 2. Fixation cross ---
    fixation = visual.TextStim(
        win=window,
        text="+",
        color=text_color,
        font=font_name,
        height=font_size,
        units="pix",
    )
    fixation.draw()
    window.flip()
    _isi_with_escape(
        timing["fixation_cross"], quit_key, window,
        results, save_fn, save_args,
    )

    # --- 3. Stimulus presentation ---
    event.clearEvents()

    stimulus = visual.TextStim(
        win=window,
        text=word,
        color=stimulus_color,
        font=font_name,
        height=font_size,
        units="pix",
        bold=True,
    )
    stimulus.draw()
    window.flip()

    rt_clock = core.Clock()

    # --- 4. Response collection ---
    pressed_key: Optional[str] = None
    rt: Optional[float] = None
    is_correct: int = 0

    response = event.waitKeys(
        maxWait=timing["stimulus_timeout"],
        keyList=valid_keys,
        timeStamped=rt_clock,
    )

    if response is not None:
        pressed_key = response[0][0]
        rt = response[0][1]
        _check_quit(
            [pressed_key], quit_key, window, results, save_fn, save_args,
        )
        is_correct = 1 if pressed_key == corr_ans else 0
    else:
        pressed_key = None
        rt = None
        is_correct = 0

    # --- 5. Record data ---
    trial_result = {
        "word": word,
        "color": color_name,
        "congruency": trial_data["congruency"],
        "expected_key": corr_ans,
        "pressed_key": pressed_key if pressed_key else "none",
        "is_correct": is_correct,
        "rt": round(rt, 4) if rt is not None else "NA",
        "timestamp": datetime.now().isoformat(),
    }

    # --- 6. Feedback (training only) ---
    if is_training:
        _show_feedback(
            window, config, pressed_key, is_correct,
            results, save_fn, save_args,
        )

    return trial_result


def _isi_with_escape(
    duration: float,
    quit_key: str,
    window: visual.Window,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Wait for a specified duration while checking for ESC.

    Uses a tight loop with core.wait increments to remain responsive.

    Args:
        duration: Time to wait in seconds.
        quit_key: The quit key to check for.
        window: PsychoPy Window instance.
        results: Results for emergency save.
        save_fn: Save function reference.
        save_args: Arguments for save function.
    """
    timer = core.Clock()
    while timer.getTime() < duration:
        keys = event.getKeys(keyList=[quit_key])
        if keys:
            _check_quit(
                keys, quit_key, window, results, save_fn, save_args,
            )
        core.wait(0.01, hogCPUperiod=0.001)


def _show_feedback(
    window: visual.Window,
    config: Dict[str, Any],
    pressed_key: Optional[str],
    is_correct: int,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Show feedback text during training if the answer was wrong or timed out.

    Args:
        window: PsychoPy Window instance.
        config: Full configuration dictionary.
        pressed_key: Key pressed by participant (None if timeout).
        is_correct: 1 if correct, 0 if incorrect.
        results: Results for emergency save.
        save_fn: Save function reference.
        save_args: Arguments for save function.
    """
    if is_correct:
        return

    messages = config["messages"]
    quit_key = config["keys"]["quit"]

    if pressed_key is None:
        feedback_text = messages["timeout_feedback"]
    else:
        feedback_text = messages["error_feedback"]

    feedback_stim = visual.TextStim(
        win=window,
        text=feedback_text,
        color=[1.0, -0.2, -0.2],
        font=config["gui"]["font_name"],
        height=config["gui"]["font_size"],
        units="pix",
        bold=True,
    )
    feedback_stim.draw()
    window.flip()

    _isi_with_escape(
        config["timing"]["feedback_duration"],
        quit_key, window, results, save_fn, save_args,
    )


def shuffle_trials(trials_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Pseudorandomize trials preventing consecutive identical word+color.

    Shuffles until no two adjacent trials share the same word AND color.
    Deterministic: limited to 1000 attempts then returns best result.

    Args:
        trials_list: List of trial dictionaries to shuffle.

    Returns:
        A new shuffled list with no consecutive word+color repetitions.
    """
    trials = copy.deepcopy(trials_list)
    max_attempts = 1000

    for _ in range(max_attempts):
        random.shuffle(trials)
        if _is_valid_sequence(trials):
            return trials

    # Fallback: fix remaining violations by swapping
    logging.warning(
        "shuffle_trials: nie udało się uzyskać idealnej sekwencji "
        "po 1000 próbach — naprawianie lokalne."
    )
    return _repair_sequence(trials)


def _is_valid_sequence(trials: List[Dict[str, str]]) -> bool:
    """Check if no two adjacent trials share the same word AND color.

    Args:
        trials: Ordered list of trial dictionaries.

    Returns:
        True if the sequence is valid, False otherwise.
    """
    for i in range(len(trials) - 1):
        if (trials[i]["word"] == trials[i + 1]["word"]
                and trials[i]["color"] == trials[i + 1]["color"]):
            return False
    return True


def _repair_sequence(
    trials: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Attempt to fix consecutive duplicates by swapping with later trials.

    Args:
        trials: Shuffled list with potential violations.

    Returns:
        The repaired list (best effort).
    """
    n = len(trials)
    for i in range(n - 1):
        if (trials[i]["word"] == trials[i + 1]["word"]
                and trials[i]["color"] == trials[i + 1]["color"]):
            # Find a swap candidate further in the list
            swapped = False
            for j in range(i + 2, n):
                if (trials[j]["word"] != trials[i]["word"]
                        or trials[j]["color"] != trials[i]["color"]):
                    # Also check the new neighbor at j
                    if j + 1 < n:
                        if (trials[i + 1]["word"] == trials[j + 1]["word"]
                                and trials[i + 1]["color"] == trials[j + 1]["color"]):
                            continue
                    if j - 1 >= 0 and j - 1 != i:
                        if (trials[i + 1]["word"] == trials[j - 1]["word"]
                                and trials[i + 1]["color"] == trials[j - 1]["color"]):
                            continue
                    trials[i + 1], trials[j] = trials[j], trials[i + 1]
                    swapped = True
                    break
            if not swapped:
                logging.warning(
                    f"Nie udało się naprawić duplikatu na pozycji {i}/{i+1}."
                )
    return trials


def run_block(
    window: visual.Window,
    trials_list: List[Dict[str, str]],
    config: Dict[str, Any],
    is_training: bool = False,
    subject_data: Optional[Dict[str, str]] = None,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> List[Dict[str, Any]]:
    """Run a full block of trials (training or main experiment).

    Pseudorandomizes trial order, iterates through all trials,
    and collects results.

    Args:
        window: PsychoPy Window instance.
        trials_list: List of trial definitions from CSV.
        config: Full configuration dictionary.
        is_training: Whether this is a training block (enables feedback).
        subject_data: Participant info dict with ID, Wiek, Płeć.
        results: Existing results list to append to (for ESC saves).
        save_fn: Reference to save_results function.
        save_args: Tuple of (filename, config) for save_fn.

    Returns:
        List of trial result dictionaries for this block.
    """
    block_name = "training" if is_training else "main"
    logging.info(f"Rozpoczęcie bloku: {block_name}")

    shuffled = shuffle_trials(trials_list)
    block_results: List[Dict[str, Any]] = []

    for idx, trial_data in enumerate(shuffled, start=1):
        trial_result = run_trial(
            window=window,
            trial_data=trial_data,
            config=config,
            is_training=is_training,
            results=results,
            save_fn=save_fn,
            save_args=save_args,
        )

        # Enrich with subject and block data
        trial_result["subject_id"] = subject_data["ID"] if subject_data else "NA"
        trial_result["age"] = subject_data["Wiek"] if subject_data else "NA"
        trial_result["gender"] = subject_data["Płeć"] if subject_data else "NA"
        trial_result["block"] = block_name
        trial_result["trial_idx"] = idx

        block_results.append(trial_result)

        # Also append to global results for ESC safety
        if results is not None:
            results.append(trial_result)

    logging.info(
        f"Blok '{block_name}' zakończony. Prób: {len(block_results)}"
    )
    return block_results


def calculate_accuracy(block_results: List[Dict[str, Any]]) -> float:
    """Calculate response accuracy for a block of trials.

    Args:
        block_results: List of trial result dictionaries.

    Returns:
        Accuracy as a float between 0.0 and 1.0.
    """
    if not block_results:
        return 0.0

    correct = sum(1 for r in block_results if r["is_correct"] == 1)
    return correct / len(block_results)
