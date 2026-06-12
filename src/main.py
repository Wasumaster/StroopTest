"""Stroop Task — Main entry point.

Orchestrates the full experimental procedure:
  0. Load config, init logging, collect participant data
  1. Welcome screen (informed consent)
  2. Training instructions
  3. Training loop with accuracy gating
  4. Main experiment instructions
  5. Main experiment block
  6. End screen and data save
"""

import os

from psychopy import core, logging, visual

from procedures import (
    calculate_accuracy,
    run_block,
    show_screen,
)
from utils import (
    build_instruction_path,
    build_trial_path,
    generate_results_filename,
    get_subject_data,
    load_config,
    load_instruction_text,
    load_trials,
    save_results,
    setup_logging,
)


def main() -> None:
    """Run the complete Stroop Task experiment."""

    # ---- Etap 0: Initialization ----
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    config = load_config(config_path)
    setup_logging(config)
    logging.info(
        f"Eksperyment: {config['experiment']['name']} "
        f"v{config['experiment']['version']}"
    )

    # Collect participant data
    subject_data = get_subject_data(config)
    if subject_data is None:
        logging.warning("Eksperyment anulowany przez uczestnika.")
        core.quit()
        return

    results_filename = generate_results_filename(subject_data["ID"])
    all_results = []

    save_fn = save_results
    save_args = (results_filename, config)

    # Create PsychoPy window
    gui_cfg = config["gui"]
    window = visual.Window(
        size=gui_cfg["window_size"],
        fullscr=gui_cfg["full_screen"],
        color=gui_cfg["bg_color"],
        units="pix",
        allowGUI=False,
    )

    logging.info("Okno PsychoPy zainicjowane.")

    try:
        # ---- Etap 1: Welcome screen ----
        welcome_path = build_instruction_path(config, "welcome_file")
        welcome_text = load_instruction_text(welcome_path)
        show_screen(
            window, welcome_text, config["keys"]["continue"], config,
            all_results, save_fn, save_args,
        )
        logging.info("Ekran powitalny wyświetlony.")

        # ---- Etap 2–3: Training loop ----
        training_trials_path = build_trial_path(config, "training_trials_file")
        training_trials = load_trials(training_trials_path)
        training_inst_path = build_instruction_path(config, "training_inst_file")
        training_inst_text = load_instruction_text(training_inst_path)

        max_loops = config["thresholds"]["max_training_loops"]
        min_accuracy = config["thresholds"]["training_min_accuracy"]
        training_passed = False

        for loop_idx in range(1, max_loops + 1):
            logging.info(f"Trening — pętla {loop_idx}/{max_loops}")

            # Show training instructions
            show_screen(
                window, training_inst_text, config["keys"]["continue"],
                config, all_results, save_fn, save_args,
            )

            # Run training block
            training_results = run_block(
                window=window,
                trials_list=training_trials,
                config=config,
                is_training=True,
                subject_data=subject_data,
                results=all_results,
                save_fn=save_fn,
                save_args=save_args,
            )

            accuracy = calculate_accuracy(training_results)
            logging.info(
                f"Trening pętla {loop_idx}: accuracy = {accuracy:.2%} "
                f"(wymagane: {min_accuracy:.0%})"
            )

            if accuracy >= min_accuracy:
                training_passed = True
                logging.info("Trening zakończony sukcesem.")
                break

            # Training failed — show retry message (unless last loop)
            if loop_idx < max_loops:
                logging.warning(
                    f"Trening pętla {loop_idx}: dokładność poniżej progu."
                )
                show_screen(
                    window,
                    config["messages"]["training_failed"],
                    config["keys"]["continue"],
                    config,
                    all_results, save_fn, save_args,
                )

        if not training_passed:
            logging.warning(
                "Uczestnik nie osiągnął wymaganego poziomu dokładności "
                f"po {max_loops} próbach treningowych."
            )
            save_results(all_results, results_filename, config)
            show_screen(
                window,
                config["messages"]["training_max_reached"],
                config["keys"]["continue"],
                config,
            )
            window.close()
            core.quit()
            return

        # ---- Etap 4: Main experiment instructions ----
        main_inst_path = build_instruction_path(config, "main_inst_file")
        main_inst_text = load_instruction_text(main_inst_path)
        show_screen(
            window, main_inst_text, config["keys"]["continue"], config,
            all_results, save_fn, save_args,
        )
        logging.info("Instrukcja fazy głównej wyświetlona.")

        # ---- Etap 5: Main experiment ----
        main_trials_path = build_trial_path(config, "main_trials_file")
        main_trials = load_trials(main_trials_path)

        logging.info("Rozpoczęcie fazy głównej eksperymentu.")
        run_block(
            window=window,
            trials_list=main_trials,
            config=config,
            is_training=False,
            subject_data=subject_data,
            results=all_results,
            save_fn=save_fn,
            save_args=save_args,
        )
        logging.info("Faza główna zakończona.")

        # ---- Etap 6: Save results and end ----
        save_results(all_results, results_filename, config)
        logging.info("Wyniki zapisane pomyślnie.")

        show_screen(
            window,
            config["messages"]["end_screen"],
            config["keys"]["continue"],
            config,
        )

    except Exception as e:
        logging.error(f"Nieoczekiwany błąd: {e}")
        # Emergency save
        try:
            save_results(all_results, results_filename, config)
            logging.info("Wyniki awaryjne zapisane po wyjątku.")
        except Exception as save_err:
            logging.error(f"Nie udało się zapisać wyników awaryjnych: {save_err}")
        raise
    finally:
        window.close()
        logging.info("Okno zamknięte. Eksperyment zakończony.")
        core.quit()


if __name__ == "__main__":
    main()
