"""Główny punkt wejścia dla Testu Stroopa.

Plik ten odpowiada za orkiestrację całego przepływu procedury eksperymentalnej.
Nie zawiera on logiki wyświetlania (ta znajduje się w procedures.py),
jednak dyryguje kolejnością działania poszczególnych elementów:
  0. Załadowanie konfiguracji, inicjalizacja logowania, pobranie danych badanego (GUI).
  1. Wyświetlenie ekranu powitalnego i zgody RODO (Informed Consent).
  2. Ekran z instrukcją dla treningu.
  3. Pętla treningowa, badająca skuteczność reakcji (Accuracy threshold gating).
  4. Ekran z instrukcją wejścia do fazy głównej.
  5. Pętla fazy głównej eksperymentu (zapis wszystkich bodźców).
  6. Ekran końcowy z automatycznym zapisem i eleganckim zamknięciem okna.
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
    """Główna funkcja uruchamiająca i nadzorująca cały Test Stroopa."""

    # ---- Etap 0: Inicjalizacja środowiska i zebranie danych od badanego ----
    
    # 0.1 Skrypt najpierw lokalizuje absolutną ścieżkę konfiguracyjną (w src/) i ją wczytuje
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    config = load_config(config_path)
    
    # 0.2 Logowanie jest uruchamiane natychmiast, żeby ewentualne awarie UI już mogły zostać wyśledzone
    setup_logging(config)
    logging.info(
        f"Eksperyment: {config['experiment']['name']} "
        f"v{config['experiment']['version']} — Rozpoczęty!"
    )

    # 0.3 Zebranie i zwalidowanie WIEKU i PŁCI na małym osobnym okienku interfejsu systemu (OS GUI)
    subject_data = get_subject_data(config)
    
    # Przerwanie działania bez zapisywania w ogóle czegokolwiek jeśli uczestnik zamknął okienko krzyżykiem / przyciskiem Anuluj
    if subject_data is None:
        logging.warning("Eksperyment anulowany przez uczestnika podczas wypełniania GUI.")
        core.quit() # core.quit() ubija wszystkie wewnątrz-wątkowe sprawy PsychoPy i zamyka skrypt bezbłędnie
        return

    # 0.4 Wygenerowanie bazowej i bezpiecznej nazwy pliku gdzie znajdą się wyniki
    results_filename = generate_results_filename(subject_data["ID"])
    all_results = [] # Inicjalizacja głównego rejestru, to tutaj wędrują dane co każdą pojedynczą próbę

    # Parametry pomocnicze potrzebne przy przekazywaniu funkcji zapisu awaryjnego np. przy kliknięciu ESC
    save_fn = save_results
    save_args = (results_filename, config)

    # 0.5 Inicjalizacja okna Fullscreen dla eksperymentu
    gui_cfg = config["gui"]
    window = visual.Window(
        size=gui_cfg["window_size"],    # z config.yaml, np. 1920x1080 
        fullscr=gui_cfg["full_screen"], # czy pełny ekran czy w małym okienku?
        color=gui_cfg["bg_color"],      # Kolor w PsychoPy np. [-1, -1, -1] co da perfekcyjną i jednorodną czerń
        units="pix",                    # Ważne: skalujemy pozycje stymulacji w pikselach
        allowGUI=False,                 # Zablokowanie myszki i ukrycie belek okien podczas testu zmusza to do skupienia
    )

    logging.info("Główne okno PsychoPy zostało zainicjowane z sukcesem.")

    # Cały proces badawczy łapiemy w bloku TRY by bezwarunkowo zapisać ułomne/niewyraźne dane nawet jeśli
    # coś wyrzuci niespodziewany błąd lub awarię w samym sercu PsychoPy.
    try:
        # ---- Etap 1: Ekran Powitalny (Informed Consent) ----
        welcome_path = build_instruction_path(config, "welcome_file")
        welcome_text = load_instruction_text(welcome_path)
        
        # Ekran ten nie odlicza czasu, leży tak długo póki badany nie zatwierdzi go wpisanym w config
        # klawiszem kontynuacji (np. Spacja).
        show_screen(
            window, welcome_text, config["keys"]["continue"], config,
            all_results, save_fn, save_args,
        )
        logging.info("Uczestnik zatwierdził informacje na ekranie powitalnym.")

        # ---- Etap 2 oraz 3: Pętla instrukcji + samego bloku treningowego ----
        
        # Przygotowanie zasobów do bloku treningowego
        training_trials_path = build_trial_path(config, "training_trials_file")
        training_trials = load_trials(training_trials_path)
        
        training_inst_path = build_instruction_path(config, "training_inst_file")
        training_inst_text = load_instruction_text(training_inst_path)

        # Ograniczenia i minimalne progi odczytane z konfiguracji
        max_loops = config["thresholds"]["max_training_loops"]
        min_accuracy = config["thresholds"]["training_min_accuracy"]
        training_passed = False

        # W przypadku złego wykonania badania przez uczestnika aplikacja potrafi dynamicznie przywrócić
        # go ponownie do instrukcji i ponowić cały trening
        for loop_idx in range(1, max_loops + 1):
            logging.info(f"Faza treningowa — aktualny przebieg: Pętla {loop_idx}/{max_loops}")

            # Wyświetl wprowadzenie teoretyczne
            show_screen(
                window, training_inst_text, config["keys"]["continue"],
                config, all_results, save_fn, save_args,
            )

            # Uruchom faktyczny trening
            training_results = run_block(
                window=window,
                trials_list=training_trials,
                config=config,
                is_training=True, # Argument 'True' pozwala algorytmom wyświetlać duże, czerwone hasło "Błąd!" przy złym wciśnięciu
                subject_data=subject_data,
                results=all_results,
                save_fn=save_fn,
                save_args=save_args,
            )

            # Pobranie wskaźnika wyników Accuracy na ułamkach od 0.0 do 1.0
            accuracy = calculate_accuracy(training_results)
            logging.info(
                f"Obliczanie dokładności po ukończeniu Pętli {loop_idx}: accuracy = {accuracy:.2%} "
                f"(Próg zdawalności wymaga min.: {min_accuracy:.0%})"
            )

            # Weryfikacja czy użytkownik sprostał minimalnemu progowi (np 80% poprawnych reakcji)
            if accuracy >= min_accuracy:
                training_passed = True
                logging.info("Trening zwieńczony powodzeniem - próg dokładności spełniony.")
                break

            # Jeżeli to była wpadka to uruchom ponownie (chyba że nie ma już limitów prób w puli)
            if loop_idx < max_loops:
                logging.warning(
                    f"Trening oblał próg testowy. Podejście {loop_idx} było niezadowalające."
                )
                show_screen(
                    window,
                    config["messages"]["training_failed"],
                    config["keys"]["continue"],
                    config,
                    all_results, save_fn, save_args,
                )

        # Brak sukcesu po osiągnięciu maksymalnego limitu np 3 przebiegów dyskwalifikuje użytkownika
        if not training_passed:
            logging.warning(
                f"Dyskwalifikacja. Uczestnik wielokrotnie zawiódł procedurę na treningu po {max_loops} podejściach."
            )
            
            # Nawet jeśli oblano, to zapisujemy te dane po treningu by zweryfikować co było u takiego delikwenta tak ułomne.
            save_results(all_results, results_filename, config)
            
            show_screen(
                window,
                config["messages"]["training_max_reached"],
                config["keys"]["continue"],
                config,
            )
            # Zamknij bez wejścia do gry głownej
            window.close()
            core.quit()
            return

        # ---- Etap 4: Ekran powiadamiający o rozpoczęciu trudnej fazy (Faza Główna) ----
        main_inst_path = build_instruction_path(config, "main_inst_file")
        main_inst_text = load_instruction_text(main_inst_path)
        show_screen(
            window, main_inst_text, config["keys"]["continue"], config,
            all_results, save_fn, save_args,
        )
        logging.info("Użytkownik zadeklarował gotowość (wcisnął spację). Faza Główna zaraz zostanie odsłonięta.")

        # ---- Etap 5: Eksperyment Właściwy (Szeroka pula bodźców) ----
        main_trials_path = build_trial_path(config, "main_trials_file")
        main_trials = load_trials(main_trials_path)

        logging.info("Silnik proceduralny: Inicjacja Fazy Głównej")
        
        # Wypalenie pętli głównej (tu zazwyczaj znajduje się ok 50 - 150 bodźców zaleznie od CSV)
        run_block(
            window=window,
            trials_list=main_trials,
            config=config,
            is_training=False, # Istotna zmiana - 'False' odcina procedurze możliwość pokazania feedbacku ("Błąd!") uczestnikowi. Faza ta jest milcząca
            subject_data=subject_data,
            results=all_results,
            save_fn=save_fn,
            save_args=save_args,
        )
        logging.info("Sukces. Procedury fazy głównej sfinalizowane bez awarii.")

        # ---- Etap 6: Zrzut kompletnej bazy wszystkich cyklów prób do pliku wynikowego ----
        save_results(all_results, results_filename, config)
        logging.info(f"Ostateczny zrzut zebranych czasów RT i wciśnięć zapisany.")

        # Wyświetlenie końcowej informacji informującej, że można wezwać badacza i eksperyment się zakończył
        show_screen(
            window,
            config["messages"]["end_screen"],
            config["keys"]["continue"],
            config,
        )

    # Zabezpieczenie przed niewiadomą (Exception) gwarantujące awaryjne zapisanie postępów
    except Exception as e:
        logging.error(f"FATALNY BŁĄD w strukturze eksperymentu: {e}")
        try:
            save_results(all_results, results_filename, config)
            logging.info("Zrzut bufora ratunkowego (Emergency Dump) powiódł się.")
        except Exception as save_err:
            logging.error(f"Nie powiodło się wykonanie ratunkowego zrzutu wyników do CSV!: {save_err}")
        # Przekaż wyjątek na górę stosu by było można prześledzić dokładny Call Stack usterki
        raise
    
    # Blok 'finally' wykona się absolutnie ZAWSZE — czy kod przetrwał poprawnie, 
    # czy uczestnik użył "Escape Hatch", czy wystąpił nagły Exception
    finally:
        window.close()
        logging.info("Silnik renderujący okna odpięty. Moduły zgaszone. Program zakończył proces na dobre.")
        core.quit()


# Konstrukcja idiomu zabezpieczająca wywołanie (kod wykona się tylko po wywołaniu bezpośrednim modułu)
if __name__ == "__main__":
    main()
