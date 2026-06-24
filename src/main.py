"""
Główny punkt startowy (orkiestrator) programu.
Dzięki podziałowi kodu na mniejsze kroki w utils.py i procedura.py,
w tym pliku widać wyraźną, czytelną oś czasu całego eksperymentu z góry na dół.
"""

import os
from psychopy import visual, core
import utils
import procedura

def main():
    # 1. Zabezpieczenie ścieżek
    # os.path.abspath(__file__) znajduje absolutną lokalizację tego pliku (main.py).
    # Gwarantuje to, że obojętnie skąd odpalimy skrypt w terminalu, program poprawnie 
    # odnajdzie pliki z konfiguracją i bodźcami.
    sciezka_src = os.path.dirname(os.path.abspath(__file__))
    katalog_glowny = os.path.dirname(sciezka_src)
    
    # 2. Inicjalizacja danych (Wczytanie YAMLA i GUI)
    config = utils.wczytaj_config(os.path.join(sciezka_src, "config.yaml"))
    
    dane_badanego = utils.pobierz_dane_badanego(config["experiment"]["name"])
    if not dane_badanego:
        print("Uczestnik anulował badanie. Zamykam program.")
        core.quit() # Kończy działanie programu i Pythona
        
    # Pusta lista, do której powolutku (trial po trialu) będziemy dorzucać wyniki
    globalne_wyniki = []
    
    # 3. Utworzenie "płótna" - okna PsychoPy, na którym będziemy malować grafiki
    gui_cfg = config["gui"]
    okno = visual.Window(
        size=gui_cfg["window_size"], fullscr=gui_cfg["full_screen"], 
        color=gui_cfg["bg_color"], units="pix"
    )
    
    # TZW. ESCAPE HATCH (Właz ewakuacyjny) - blok try / finally.
    # Konstrukcja tego bloku gwarantuje, że kod wpisany po słowie 'finally' (na samym dole)
    # wywoła się absolutnie ZAWSZE. Nieważne, czy w środku eksperymentu wyskoczy błąd,
    # czy uczestnik wciśnie klawisz ESC w trakcie procedury - dane zawsze się zapiszą.
    try:
        
        # === ETAP A: EKRANY INSTRUKCJI ===
        katalog_instrukcji = os.path.join(katalog_glowny, config["paths"]["instructions_dir"])
        for nazwa_obrazka in config["paths"]["instruction_images"]:
            pelna_sciezka = os.path.join(katalog_instrukcji, nazwa_obrazka)
            procedura.pokaz_obrazek(okno, pelna_sciezka, config["keys"]["continue"])
            
            
        # === ETAP B: FAZA TRENINGOWA ===
        sciezka_trening = os.path.join(katalog_glowny, config["paths"]["stimulus_dir"], config["paths"]["training_trials_file"])
        triale_treningowe = utils.wczytaj_bodzce(sciezka_trening)
        
        sukces_treningu = False
        
        # Pętla iteruje do X powtórzeń zdefiniowanych w yaml (domyślnie 3 próby na zdanie treningu)
        for proba in range(config["thresholds"]["max_training_loops"]):
            przetasowane_triale = procedura.przetasuj_triale(triale_treningowe)
            wyniki_bloku = []
            
            # enumerate pozwala przechodzić przez listę przypisując elementom licznik (indeks)
            # start=1 sprawia, że numery prób w excelu zaczną się od 1, a nie programistycznego 0
            for indeks, trial in enumerate(przetasowane_triale, start=1):
                wynik = procedura.wykonaj_trial(okno, trial, config, czy_trening=True)
                
                # Funkcja update() dokleja do naszego słownika wynikowego zmienne globalne uczestnika,
                # dzięki czemu Excel jest pełny informacji o wieku badanego i fazie w każdej linijce.
                wynik.update({
                    "subject_id": dane_badanego["ID"], "age": dane_badanego["Wiek"], 
                    "gender": dane_badanego["Płeć"], "block": "trening", "trial_idx": indeks
                })
                wyniki_bloku.append(wynik)
                globalne_wyniki.append(wynik)
                
            # Wyliczanie progu poprawności - Accuracy po zakończeniu pojedynczej pętli bloku
            poprawne = sum(1 for w in wyniki_bloku if w["is_correct"] == 1)
            dokladnosc = poprawne / len(wyniki_bloku)
            
            if dokladnosc >= config["thresholds"]["training_min_accuracy"]:
                sukces_treningu = True
                break # Jeśli zdał - "łamiemy" i omijamy dalsze pętle treningowe
            else:
                if proba < config["thresholds"]["max_training_loops"] - 1:
                    procedura.pokaz_ekran_tekstowy(okno, config["messages"]["training_failed"], config, config["keys"]["continue"])
        
        # Wyrzucenie badanego, jeśli pomimo x prób nie osiągnął 80% poprawności (nie zrozumiał zasad)
        if not sukces_treningu:
            procedura.pokaz_ekran_tekstowy(okno, config["messages"]["training_max_reached"], config, config["keys"]["continue"])
            okno.close()
            core.quit() # Program się wyłącza zrzucając dotychczasowe dane do zapisu
            
            
        # === ETAP C: PRZEJŚCIE i FAZA GŁÓWNA ===
        sciezka_po_tren = os.path.join(katalog_instrukcji, config["paths"]["post_training_instruction_image"])
        procedura.pokaz_obrazek(okno, sciezka_po_tren, config["keys"]["continue"])
        
        sciezka_glowna = os.path.join(katalog_glowny, config["paths"]["stimulus_dir"], config["paths"]["main_trials_file"])
        triale_glowne = utils.wczytaj_bodzce(sciezka_glowna)
        przetasowane_glowne = procedura.przetasuj_triale(triale_glowne)
        
        # Odtwarzamy główny blok, tym razem wywołując wykonaj_trial z flagą czy_trening=False
        for indeks, trial in enumerate(przetasowane_glowne, start=1):
            wynik = procedura.wykonaj_trial(okno, trial, config, czy_trening=False)
            
            wynik.update({
                "subject_id": dane_badanego["ID"], "age": dane_badanego["Wiek"], 
                "gender": dane_badanego["Płeć"], "block": "glowna", "trial_idx": indeks
            })
            globalne_wyniki.append(wynik)
            
        # Wyświetlenie ekranu końcowego
        procedura.pokaz_ekran_tekstowy(okno, config["messages"]["end_screen"], config, config["keys"]["continue"])
        
    finally:
        # ---> SEKRYTNY MECHANIZM ZAPISU AWARYJNEGO <---
        # Nawet gdy PsychoPy ulegnie awarii w locie, lub wyjdziesz na "Eskepie", wchodzimy tutaj:
        if globalne_wyniki:  # Zapisujemy plik tylko, jeśli zdążyliśmy zarejestrować co najmniej 1 próbę
            katalog_wynikow = os.path.join(katalog_glowny, config["paths"]["results_dir"])
            utils.zapisz_wyniki(globalne_wyniki, katalog_wynikow, dane_badanego["ID"])
            print(f"Zapisano {len(globalne_wyniki)} prób!")
            
        # Ostateczne zwolnienie procesów
        okno.close()
        core.quit()

# Zabezpieczenie przed samoczynnym uruchomieniem procedury,
# np. jeśli w przyszłości ktoś chciałby ten plik zaimportować do innego skryptu jako moduł.
if __name__ == "__main__":
    main()