"""Główny punkt wejścia dla Testu Stroopa.

Plik ten odpowiada za orkiestrację całego przepływu eksperymentu. Nie zawiera
logiki renderowania bodźców (ta znajduje się w procedures.py), lecz dyryguje
kolejnością działania poszczególnych etapów:

  Etap 0 — Inicjalizacja:
      Wczytanie konfiguracji z config.yaml, uruchomienie systemu logowania,
      zebranie danych demograficznych uczestnika przez okno GUI systemu operacyjnego.

  Etap 1 — Sekwencja instrukcji graficznych:
      Wyświetlenie trzech ekranów instrukcji (instrukcja_1, instrukcja_2, instrukcja_3)
      w formacie graficznym (JPG). Każdy ekran czeka na naciśnięcie spacji przez uczestnika.

  Etap 2 — Pętla treningowa:
      Trening z feedbackiem. Uczestnik poznaje zadanie i mapowanie klawiszy na kolory.
      Jeśli wskaźnik poprawności jest poniżej progu (domyślnie 80%), trening jest
      powtarzany. Maksymalna liczba powtórzeń jest zdefiniowana w konfiguracji.
      Jeśli uczestnik nie osiągnie progu po maksymalnej liczbie prób, eksperyment
      kończy się bez fazy głównej.

  Etap 3 — Instrukcja po treningu:
      Po zaliczeniu treningu wyświetlany jest osobny ekran graficzny informujący
      o rozpoczęciu właściwej fazy eksperymentalnej.

  Etap 4 — Faza główna:
      Właściwy pomiar — pełna pula bodźców bez feedbacku. Wszystkie dane są
      zapisywane do pliku CSV.

  Etap 5 — Zakończenie:
      Finalny zapis wyników, wyświetlenie ekranu końcowego, zamknięcie okna.
"""

import os

from psychopy import core, logging, visual

from procedures import (
    calculate_accuracy,
    run_block,
    show_instruction_image,
    show_screen,
)
from utils import (
    build_instruction_image_path,
    build_trial_path,
    generate_results_filename,
    get_subject_data,
    load_config,
    load_trials,
    save_results,
    setup_logging,
)


def main() -> None:
    """Główna funkcja uruchamiająca i nadzorująca cały Test Stroopa.

    Funkcja jest jedynym punktem wejścia do eksperymentu. Organizuje przepływ
    sterowania pomiędzy poszczególnymi etapami, zarządza zasobami (okno PsychoPy,
    pliki wynikowe) oraz zapewnia awaryjny zapis danych w bloku try/finally.
    """

    # ---- Etap 0: Inicjalizacja środowiska i zebranie danych od badanego ----

    # Lokalizacja pliku konfiguracyjnego relative do położenia tego skryptu.
    # Użycie os.path.abspath(__file__) gwarantuje poprawność ścieżki niezależnie
    # od katalogu roboczego, z którego uruchomiono skrypt.
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    config = load_config(config_path)

    # Logowanie uruchamiane jest natychmiast po wczytaniu konfiguracji,
    # by ewentualne błędy inicjalizacji okna były już rejestrowane w pliku logu.
    setup_logging(config)
    logging.info(
        f"Eksperyment: {config['experiment']['name']} "
        f"v{config['experiment']['version']} — Rozpoczęty!"
    )

    # Zebranie danych demograficznych (Wiek, Płeć) przez systemowe okno dialogowe.
    # ID uczestnika generowane jest automatycznie na podstawie bieżącego czasu.
    subject_data = get_subject_data(config)

    # Jeśli uczestnik zamknie okno dialogowe (krzyżyk / Anuluj), eksperyment kończy się
    # bez zapisu czegokolwiek — nie doszło do żadnego pomiaru.
    if subject_data is None:
        logging.warning("Eksperyment anulowany przez uczestnika podczas wypełniania GUI.")
        core.quit()
        return

    # Wygenerowanie unikalnej nazwy pliku wynikowego na podstawie ID uczestnika.
    # Plik jest tworzony (lub nadpisywany) dopiero przy pierwszym zapisie danych.
    results_filename = generate_results_filename(subject_data["ID"])
    all_results = []  # Główna lista gromadząca wyniki wszystkich prób z całej sesji

    # Referencje do funkcji i argumentów zapisu — przekazywane dalej jako parametry,
    # aby wszystkie procedury mogły wykonać awaryjny zapis przy naciśnięciu ESC.
    save_fn = save_results
    save_args = (results_filename, config)

    # Inicjalizacja okna pełnoekranowego PsychoPy.
    # allowGUI=False ukrywa paski okna i kursor myszy, co minimalizuje rozproszenia.
    gui_cfg = config["gui"]
    window = visual.Window(
        size=gui_cfg["window_size"],    # Rozdzielczość okna (z config.yaml)
        fullscr=gui_cfg["full_screen"], # Tryb pełnoekranowy
        color=gui_cfg["bg_color"],      # Kolor tła (domyślnie czarny: [0, 0, 0])
        units="pix",                    # Pozycje i rozmiary w pikselach
        allowGUI=False,                 # Brak dekoracji okna podczas eksperymentu
    )

    logging.info("Główne okno PsychoPy zostało zainicjowane.")

    # Blok try/finally zapewnia, że okno zostanie zawsze zamknięte i core.quit()
    # zostanie wywołane — nawet jeśli eksperyment zakończy się wyjątkiem.
    try:

        # ---- Etap 1: Sekwencja instrukcji graficznych ----
        #
        # Trzy ekrany instrukcji są wyświetlane jeden po drugim przed treningiem.
        # Kolejność wyświetlania odpowiada kolejności na liście 'instruction_images'
        # w config.yaml: instrukcja_1 → instrukcja_2 → instrukcja_3.
        # Każdy ekran czeka na naciśnięcie spacji przez uczestnika.
        #
        # Instrukcje są plikami graficznymi (JPG) — przechowywane w katalogu /instructions/.
        # Graficzny format pozwala na dokładne i bogate wizualnie przedstawienie zasad zadania.

        instruction_images = config["paths"]["instruction_images"]
        logging.info(f"Sekwencja instrukcji — {len(instruction_images)} ekranów do wyświetlenia.")

        for img_filename in instruction_images:
            img_path = build_instruction_image_path(config, img_filename)
            logging.info(f"Wyświetlanie instrukcji: {img_filename}")
            show_instruction_image(
                window, img_path, config["keys"]["continue"],
                config, all_results, save_fn, save_args,
            )

        logging.info("Uczestnik zapoznał się ze wszystkimi ekranami instrukcji.")

        # ---- Etap 2: Pętla treningowa ----
        #
        # Faza treningowa trwa do momentu osiągnięcia przez uczestnika
        # minimalnego progu poprawności (domyślnie 80%) lub wyczerpania
        # maksymalnej liczby dozwolonych powtórzeń.
        #
        # W trakcie treningu po każdej błędnej odpowiedzi lub braku odpowiedzi
        # wyświetlany jest komunikat feedbacku (np. "BŁĄD" lub "ZA WOLNO").
        # Feedback uczy uczestnika prawidłowego mapowania klawiszy na kolory.

        training_trials_path = build_trial_path(config, "training_trials_file")
        training_trials = load_trials(training_trials_path)

        max_loops = config["thresholds"]["max_training_loops"]
        min_accuracy = config["thresholds"]["training_min_accuracy"]
        training_passed = False

        for loop_idx in range(1, max_loops + 1):
            logging.info(f"Faza treningowa — pętla {loop_idx}/{max_loops}")

            # Uruchomienie bloku treningowego z aktywnym feedbackiem
            training_results = run_block(
                window=window,
                trials_list=training_trials,
                config=config,
                is_training=True,   # True = feedback po błędach jest aktywny
                subject_data=subject_data,
                results=all_results,
                save_fn=save_fn,
                save_args=save_args,
            )

            # Obliczenie wskaźnika poprawności po zakończeniu bloku treningowego
            accuracy = calculate_accuracy(training_results)
            logging.info(
                f"Dokładność po pętli {loop_idx}: {accuracy:.2%} "
                f"(wymagane minimum: {min_accuracy:.0%})"
            )

            if accuracy >= min_accuracy:
                training_passed = True
                logging.info("Trening zaliczony — próg dokładności osiągnięty.")
                break

            # Jeśli próg nie został osiągnięty i pozostały jeszcze próby, wyświetl
            # komunikat zachęcający do ponownego zapoznania się z instrukcją.
            if loop_idx < max_loops:
                logging.warning(
                    f"Dokładność poniżej progu w pętli {loop_idx} — powtarzanie treningu."
                )
                show_screen(
                    window,
                    config["messages"]["training_failed"],
                    config["keys"]["continue"],
                    config,
                    all_results, save_fn, save_args,
                )

        # Jeśli po wszystkich dozwolonych powtórzeniach próg nie został osiągnięty,
        # uczestnik jest dyskwalifikowany — dane są zapisywane i eksperyment kończy się.
        if not training_passed:
            logging.warning(
                f"Dyskwalifikacja — uczestnik nie osiągnął progu po {max_loops} powtórzeniach."
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

        # ---- Etap 3: Instrukcja po zakończeniu fazy treningowej ----
        #
        # Po zaliczeniu treningu wyświetlany jest specjalny ekran graficzny,
        # który informuje uczestnika o zakończeniu treningu i nadchodzącym
        # początku właściwej fazy eksperymentalnej. Uczestnik naciska spację,
        # aby natychmiast rozpocząć fazę główną.

        post_training_img = config["paths"]["post_training_instruction_image"]
        post_training_path = build_instruction_image_path(config, post_training_img)
        logging.info(f"Wyświetlanie instrukcji po treningu: {post_training_img}")
        show_instruction_image(
            window, post_training_path, config["keys"]["continue"],
            config, all_results, save_fn, save_args,
        )
        logging.info("Uczestnik gotowy do fazy głównej — nacisnął spację.")

        # ---- Etap 4: Faza główna eksperymentu ----
        #
        # Właściwy pomiar — pełna pula bodźców (zgodne, niezgodne, neutralne)
        # prezentowana w losowej kolejności. W tej fazie feedback jest wyłączony
        # (is_training=False), co pozwala na zebranie czystych danych bez wpływu
        # informacji zwrotnej na zachowanie uczestnika.

        main_trials_path = build_trial_path(config, "main_trials_file")
        main_trials = load_trials(main_trials_path)

        logging.info("Inicjacja fazy głównej eksperymentu.")

        run_block(
            window=window,
            trials_list=main_trials,
            config=config,
            is_training=False,  # False = brak feedbacku w fazie głównej
            subject_data=subject_data,
            results=all_results,
            save_fn=save_fn,
            save_args=save_args,
        )
        logging.info("Faza główna zakończona pomyślnie.")

        # ---- Etap 5: Zapis wyników i ekran końcowy ----
        #
        # Finalne zapisanie kompletnych danych ze wszystkich blokób (trening + faza główna).
        # Wyświetlenie komunikatu kończącego z podziękowaniem, który znika po naciśnięciu
        # dowolnego klawisza przez uczestnika lub badacza.

        save_results(all_results, results_filename, config)
        logging.info("Finalny zapis wyników zakończony.")

        show_screen(
            window,
            config["messages"]["end_screen"],
            config["keys"]["continue"],
            config,
        )

    except Exception as e:
        # Zabezpieczenie przed niespodziewanym wyjątkiem — awaryjny zapis danych
        # zapobiega utracie wszystkich zebranych wyników w przypadku awarii programu.
        logging.error(f"FATALNY BŁĄD w strukturze eksperymentu: {e}")
        try:
            save_results(all_results, results_filename, config)
            logging.info("Awaryjny zapis wyników (Emergency Dump) powiódł się.")
        except Exception as save_err:
            logging.error(f"Nie powiodło się wykonanie awaryjnego zapisu: {save_err}")
        raise  # Ponowne zgłoszenie wyjątku, by call stack był widoczny w logach

    finally:
        # Blok finally wykonuje się zawsze — zarówno po normalnym zakończeniu,
        # jak i po wyjątku lub użyciu ESC (core.quit). Gwarantuje poprawne
        # uwolnienie zasobów graficznych.
        window.close()
        logging.info("Okno PsychoPy zamknięte. Eksperyment zakończony.")
        core.quit()


# Idiom zabezpieczający przed przypadkowym importem — kod wykonuje się tylko
# przy bezpośrednim uruchomieniu pliku (python main.py), nie przy imporcie.
if __name__ == "__main__":
    main()
