"""Procedury eksperymentalne dla Testu Stroopa.

Moduł ten zawiera pełną logikę renderowania i przeprowadzania pojedynczych
prób (trial) oraz całych bloków (block). Obejmuje sterowanie wyświetlaniem bodźców,
zbieranie reakcji od uczestnika (z pomiarem RT), funkcję autorskiej 
pseudorandomizacji, podawanie informacji zwrotnej w fazie treningu oraz 
tzw. "Escape Hatch" - system pozwalający na awaryjne wyjście w dowolnym momencie.
"""

import copy
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from psychopy import core, event, logging, visual


# ---------------------------------------------------------------------------
# Mapowanie nazw kolorów na przestrzeń barw używaną przez PsychoPy (RGB od -1 do 1)
# ---------------------------------------------------------------------------
COLOR_MAP: Dict[str, List[float]] = {
    "red": [1.0, -1.0, -1.0],      # Czerwony
    "green": [-1.0, 0.6, -1.0],    # Zielony
    "blue": [-1.0, -1.0, 1.0],     # Niebieski
}


def _check_quit(
    keys: List[str],
    quit_key: str,
    window: visual.Window,
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Sprawdza, czy wciśnięto klawisz wyjścia (ESC) i obsługuje awaryjne zamykanie.

    Jeśli klawisz wyjścia zostanie wykryty, funkcja:
    1. Zapisze zebrane do tej pory wyniki do pliku (jeśli przekazano funkcję save_fn).
    2. Zamknie okno graficzne.
    3. Trwale zakończy proces PsychoPy.

    Parametry:
        keys: Lista ciągów znaków (nazw) klawiszy, które zostały naciśnięte.
        quit_key: Zdefiniowany w konfiguracji klawisz wyjścia (np. 'escape').
        window: Otwarty obiekt Okna (Window) z PsychoPy do zamknięcia.
        results: Lista zebranych już wyników do awaryjnego zapisu.
        save_fn: Referencja (wskaźnik) do funkcji save_results.
        save_args: Krotka (Tuple) z argumentami dla funkcji save_fn (nazwa pliku, konfig).
    """
    if quit_key in keys:
        logging.warning("Klawisz ESC wykryty — przerywanie eksperymentu.")
        
        # Awaryjny zapis zebranych wyników, żeby zapobiec utracie danych
        if results is not None and save_fn is not None and save_args is not None:
            try:
                save_fn(results, *save_args)
                logging.info("Wyniki awaryjne zapisane pomyślnie.")
            except Exception as e:
                logging.error(f"Błąd zapisu awaryjnego: {e}")
                
        # Bezpieczne zamknięcie okna i procesu
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
    """Wyświetla ekran tekstowy (np. z instrukcją) na pełnym oknie i czeka na reakcję.

    Nieustannie nasłuchuje klawisza kontynuacji (np. Spacja) oraz klawisza ESC.

    Parametry:
        window: Obiekt okna PsychoPy.
        text_content: Treść instrukcji do wyświetlenia na ekranie.
        wait_key: Oczekiwany klawisz do przejścia dalej (np. 'space').
        config: Pełny słownik konfiguracyjny (używany do pobrania czcionek i kolorów).
        results: Dotychczas zebrane wyniki (na wypadek awaryjnego wyjścia ESC).
        save_fn: Funkcja służąca do zapisu.
        save_args: Argumenty do funkcji zapisu.
    """
    quit_key = config["keys"]["quit"]
    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]

    # Utworzenie obiektu tekstowego do wyrenderowania w oknie
    stim = visual.TextStim(
        win=window,
        text=text_content,
        color=text_color,
        font=font_name,
        height=0.04,        # Wielkość czcionki względna (w norm)
        wrapWidth=1.5,      # Zalamanie wiersza
        units="norm",       # Pozycjonowanie relatywne względem ekranu
    )
    
    # Rysowanie w buforze pamięci
    stim.draw()
    # Przeniesienie z bufora na fizyczny ekran monitora
    window.flip()

    # Nieskończona pętla oczekująca wyłącznie na wybrane klawisze
    while True:
        # Czekaj na naciśnięcie klawisza przez badanego (tylko spacja lub escape)
        pressed = event.waitKeys(keyList=[wait_key, quit_key])
        
        if pressed is None:
            continue
            
        # Zawsze sprawdzaj, czy naciśnięty klawisz nie jest przyciskiem wyjścia awaryjnego
        _check_quit(
            pressed, quit_key, window, results, save_fn, save_args,
        )
        
        # Jeśli naciśnięto klawisz kontynuacji, przerwij pętlę i opuść ekran
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
    """Wykonuje pojedynczą próbę zadania Stroopa (jeden pełny cykl prezentacji).

    Oś czasu jednej próby (Timeline):
        1. Jitterowane ISI (Inter-Stimulus Interval) - czysty ekran przez losowy czas.
        2. Fiksacja (krzyżyk na środku ekranu przygotowujący uczestnika).
        3. Prezentacja bodźca (słowa w danym kolorze) z jednoczesnym startem zegara reakcji.
        4. Oczekiwanie na reakcję (do momentu wciśnięcia klawisza lub przekroczenia czasu).
        5. Zapisanie danych o poprawności i czasie reakcji (RT - reaction time).
        6. Jeśli to faza treningowa, podanie informacji zwrotnej (Feedback) w razie pomyłki.

    Parametry:
        window: Obiekt okna graficznego.
        trial_data: Słownik z parametrami danej próby (słowo, kolor, zgodność, poprawna odpowiedź).
        config: Słownik parametrów globalnych.
        is_training: Zmienna logiczna, flaga wskazująca, czy to blok treningowy (wymaga feedbacku).
        results: Lista zebranych prób (dla ratunkowego zapisu podczas ESC).
        save_fn: Funkcja zapisująca wyniki.
        save_args: Argumenty do zapisu wyników.

    Zwraca:
        Słownik reprezentujący surowe statystyki wynikowe tej konkretnej próby.
    """
    # Rozpakowanie zmiennych z konfiguracji dla czytelności kodu
    quit_key = config["keys"]["quit"]
    timing = config["timing"]
    response_mapping = config["keys"]["response_mapping"]
    
    # Tworzymy pełną listę klawiszy, na które skrypt będzie reagować (strzałki + ESC)
    valid_keys = list(response_mapping.keys()) + [quit_key]
    
    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]
    font_size = config["gui"]["font_size"]

    # Rozpakowanie konfiguracji pojedynczego bodźca na podstawie wczytanego CSV
    word = trial_data["word"]
    color_name = trial_data["color"]
    corr_ans = trial_data["corr_ans"]

    # Mapujemy nazwę koloru "red" / "green" z pliku na RGB używane przez PsychoPy
    # Jeśli kolor nie istnieje, jako fail-safe zostanie użyty domyślny kolor z konfiguracji
    stimulus_color = COLOR_MAP.get(color_name, text_color)

    # --- 1. Jitterowane ISI (pusty ekran o zmiennym losowym czasie) ---
    isi_duration = random.uniform(timing["isi_min"], timing["isi_max"])
    window.flip() # Pokazuje czysty ekran
    
    # Czeka na upłynięcie czasu ISI równocześnie sprawdzając klawisz ESC
    _isi_with_escape(
        isi_duration, quit_key, window, results, save_fn, save_args,
    )

    # --- 2. Fixation cross (Krzyżyk skupiający uwagę) ---
    fixation = visual.TextStim(
        win=window,
        text="+",
        color=text_color,
        font=font_name,
        height=font_size,
        units="pix",
    )
    fixation.draw()
    window.flip() # Pokazuje krzyżyk na ekranie
    
    _isi_with_escape(
        timing["fixation_cross"], quit_key, window,
        results, save_fn, save_args,
    )

    # --- 3. Prezentacja głównego bodźca (Słowo testowe) ---
    # Czyszczenie bufora klawiatury zapobiega problemowi "przeciekania" wciśnięć (key ghosting) z poprzedniej próby
    event.clearEvents()

    stimulus = visual.TextStim(
        win=window,
        text=word,
        color=stimulus_color,
        font=font_name,
        height=font_size,
        units="pix",
        bold=True, # Bodziec musi być dobrze widoczny
    )
    stimulus.draw()
    window.flip() # Bodziec pojawia się na ekranie!

    # Natychmiast po fizycznym wyświetleniu (flip) resetujemy wysoce precyzyjny zegar sprzętowy
    rt_clock = core.Clock()

    # --- 4. Oczekiwanie na reakcję badanego ---
    pressed_key: Optional[str] = None
    rt: Optional[float] = None
    is_correct: int = 0

    # Nasłuchuje wejścia z klawiatury. Posiada twardy timeout (np. 2-3 sekundy) zapobiegający blokowaniu się eksperymentu
    response = event.waitKeys(
        maxWait=timing["stimulus_timeout"],
        keyList=valid_keys,
        timeStamped=rt_clock, # Precyzyjne oznaczenie czasu w którym wciśnięto przycisk z milisekundową dokładnością
    )

    if response is not None:
        pressed_key = response[0][0]
        rt = response[0][1]
        
        # Sprawdzamy czy to wyjście awaryjne
        _check_quit(
            [pressed_key], quit_key, window, results, save_fn, save_args,
        )
        
        # Kodujemy poprawność reakcji: 1 (dobrze), 0 (źle) - co jest standardem w psychologii kognitywnej
        is_correct = 1 if pressed_key == corr_ans else 0
    else:
        # Reakcja w przypadku Timeout'u (brak odpowiedzi przed upływem limitu)
        pressed_key = None
        rt = None
        is_correct = 0

    # --- 5. Zapisanie wyników dla tej jednej próby ---
    trial_result = {
        "word": word,
        "color": color_name,
        "congruency": trial_data["congruency"],
        "expected_key": corr_ans,
        "pressed_key": pressed_key if pressed_key else "none",
        "is_correct": is_correct,
        "rt": round(rt, 4) if rt is not None else "NA", # RT w sekundach np 0.4502
        "timestamp": datetime.now().isoformat(),
    }

    # --- 6. Feedback (informacja zwrotna tylko w fazie treningu) ---
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
    """Odczekuje określony czas równocześnie sprawdzając klawisz wyjścia awaryjnego.

    Funkcja rozwiązuje problem `time.sleep` lub `core.wait`, które całkowicie mrożą 
    proces i nie pozwalają użytkownikowi na natychmiastowe przerwanie programu w połowie czekania.

    Parametry:
        duration: Czas do odczekania w sekundach.
        quit_key: Klawisz służący do przerywania programu (np. ESC).
        window: Obiekt okna PsychoPy (do zamknięcia podczas awarii).
        results: Lista zapisanych dotąd prób do uratowania.
        save_fn: Odwołanie do funkcji zapisującej pliki.
        save_args: Argumenty do powyższej funkcji.
    """
    timer = core.Clock()
    # Pętla while działa tak długo, aż zegar nie przekroczy docelowego czasu ISI
    while timer.getTime() < duration:
        # Sprawdzamy zawartość klawiatury tylko pod kątem klawisza ESC
        keys = event.getKeys(keyList=[quit_key])
        if keys:
            _check_quit(
                keys, quit_key, window, results, save_fn, save_args,
            )
        # Krótki postój zapobiegający wykorzystaniu 100% użycia procesora (CPU) przez pętlę "while"
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
    """Wyświetla wiadomość zwrotną po błędnej odpowiedzi w bloku treningowym.

    Feedback uczy uczestnika prawidłowego reagowania. Ekran pojawi się wyłącznie 
    wtedy, kiedy odpowiedź badanego była zła lub nie zdążył odpowiedzieć na czas.

    Parametry:
        window: Obiekt okna PsychoPy.
        config: Słownik ustawień (z którego czerpane są teksty z sekcji Messages).
        pressed_key: Przycisk wciśnięty przez użytkownika (jeśli brak to 'None').
        is_correct: 1 - Poprawna odp, 0 - Zła lub brak.
        results: Baza wyników, by zapisać jeśli badany wyjdzie podcas oglądania błędu.
        save_fn: Narzędzie zapisu.
        save_args: Argumenty narzedzia.
    """
    # Jeśli odpowiedź była dobra, nic nie robimy i wracamy natychmiastowo
    if is_correct:
        return

    messages = config["messages"]
    quit_key = config["keys"]["quit"]

    # Dobieramy wiadomość ze względu na rodzaj przewinienia uczestnika
    if pressed_key is None:
        feedback_text = messages["timeout_feedback"]  # Zbyt wolno ("Zbyt wolno!")
    else:
        feedback_text = messages["error_feedback"]    # Błędny klawisz ("Błąd!")

    # Tworzymy bodziec na czerwono z uwagą
    feedback_stim = visual.TextStim(
        win=window,
        text=feedback_text,
        color=[1.0, -0.2, -0.2], # Mocno czerwony, alertowy kolor tekstu
        font=config["gui"]["font_name"],
        height=config["gui"]["font_size"],
        units="pix",
        bold=True,
    )
    feedback_stim.draw()
    window.flip()

    # Ekran feedbacku wisi przez wyznaczony w ustawieniach 'feedback_duration' czas (również z opcją przerwania przez ESC)
    _isi_with_escape(
        config["timing"]["feedback_duration"],
        quit_key, window, results, save_fn, save_args,
    )


def shuffle_trials(trials_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Przeprowadza Pseudorandomizację przygotowanej listy bodźców.

    Zwykłe wymieszanie (random.shuffle) powodowałoby, że słowo "Czerwony" mogłoby
    pojawić się dwa razy pod rząd w tym samym kolorze. Byłaby to anomalia torująca 
    odpowiedzi. Pseudorandomizacja w tej pętli to zabezpieczenie, które tasuje elementy,
    a następnie zmusza mechanizm do testowania wygenerowanego układu pod kątem "powtórzeń
    identycznej konfiguracji (Słowo + Kolor)". Jeśli taka wystąpi, plik jest tasowany ponownie.

    Maksymalny cykl ponowień na tasowanie to 1000 iteracji - dla pewności i wydajności.

    Parametry:
        trials_list: Surowa lista słowników zawierających próby.

    Zwraca:
        Nową, przetasowaną z uwzględnieniem obostrzeń listę gotową do wyświetlenia.
    """
    # Używamy głębokiej kopii, aby nie naruszać bazowej wejściowej listy
    trials = copy.deepcopy(trials_list)
    max_attempts = 1000

    # Brute-force - wstrząsaj pudełkiem aż wszystko ułoży się idealnie
    for _ in range(max_attempts):
        random.shuffle(trials)
        if _is_valid_sequence(trials):
            return trials

    # Fallback (Awaryjne): jeśli po tysiącu losowań nadal mamy powtórzenia pod rząd,
    # wymuś rozplecenie poprzez system zamiany iteracyjnej (swap)
    logging.warning(
        "shuffle_trials: nie udało się uzyskać idealnej sekwencji "
        "po 1000 próbach brute-force — rozpoczynam ręczne naprawianie lokalne."
    )
    return _repair_sequence(trials)


def _is_valid_sequence(trials: List[Dict[str, str]]) -> bool:
    """Sprawdza sekwencję, czy nie zawiera dwóch identycznych prób sąsiadujących obok siebie.

    Identyczne oznaczają, że mają oboje TAKIE SAMO słowo wyrazowe, oraz TAKI SAM
    kolor renderowanego atramentu.

    Parametry:
        trials: Wymieszana lista do walidacji.

    Zwraca:
        Prawda (True) gdy lista jest poprawna, Fałsz (False) gdy wpadła w sidła powtórzeń.
    """
    for i in range(len(trials) - 1):
        if (trials[i]["word"] == trials[i + 1]["word"]
                and trials[i]["color"] == trials[i + 1]["color"]):
            return False
    return True


def _repair_sequence(
    trials: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Dokonuje "chirurgicznych zamian" by naprawić pozostałe błędy w tasowaniu (Swap Fallback).

    Przechodzi element po elemencie, a kiedy odnajdzie zabronione powtórzenie (Z i Z+1), 
    wtedy odrywa Z+1 i przesuwa go daleko wgłąb listy z inną przypadkową pozycją.

    Parametry:
        trials: Lista po 1000 nieudanych shuffle'ach, która ciągle ma złe zestawienia.

    Zwraca:
        Naprawiona (wymuszona) lista z próbami do wyświetlenia.
    """
    n = len(trials)
    for i in range(n - 1):
        # Detekcja dwóch powielających się prób
        if (trials[i]["word"] == trials[i + 1]["word"]
                and trials[i]["color"] == trials[i + 1]["color"]):
            
            # Wyszukanie w dalszej części bufora innego elementu by się z nim zamienić pozycją
            swapped = False
            for j in range(i + 2, n):
                if (trials[j]["word"] != trials[i]["word"]
                        or trials[j]["color"] != trials[i]["color"]):
                    
                    # Weryfikujemy również by ta "zamiana" nie spowodowała błędów tam, gdzie wrzucamy nowy element (j+1 oraz j-1)
                    if j + 1 < n:
                        if (trials[i + 1]["word"] == trials[j + 1]["word"]
                                and trials[i + 1]["color"] == trials[j + 1]["color"]):
                            continue
                    if j - 1 >= 0 and j - 1 != i:
                        if (trials[i + 1]["word"] == trials[j - 1]["word"]
                                and trials[i + 1]["color"] == trials[j - 1]["color"]):
                            continue
                    
                    # Zamiana zrealizowana (swap algorytm)
                    trials[i + 1], trials[j] = trials[j], trials[i + 1]
                    swapped = True
                    break
            
            # Jeśli lista ma np. tylko 3 powtarzające się same takie same elementy to naprawa mogła nie przejść
            if not swapped:
                logging.warning(
                    f"Nie udało się naprawić duplikatu na pozycji {i}/{i+1} ze względu na małą pulę próbek."
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
    """Przeprowadza cały pojedynczy pełny BLOK zadań (np. cały trening, cała faza główna).

    Krok po kroku:
    1. Uruchamia system Pseudorandomizacji na dostarczonym pliku CSV.
    2. Dla każdego bodźca wywołuje run_trial() by zrealizować pomiar.
    3. Opisuje metadane zebranej próby o takie kwestie jak ID użytkownika, płeć, czy to był
       blok eksperymentalny itp.
    4. Aktualizuje główny stos globalnych wyników.

    Parametry:
        window: Obiekt globalny okna wyświetlającego.
        trials_list: Plik z listą do przepuszczenia odczytany z utils.load_trials.
        config: Zestaw parametrów czasowych itd.
        is_training: Zaznacza czy podczas trwania tego BLOKU feedback dla badanego powienin być wyświetlany.
        subject_data: Słownik zawierający dane wyciągnięte z GUI (ID/Wiek/Płeć).
        results: Globalna lista ze wszystkimi wyciągami.
        save_fn: Funkcja z utils pomagająca zrobić zrzut w razie kliknięcia ESC wewnątrz iterowanej próby.
        save_args: Wymagane argumenty dla func.

    Zwraca:
        Listę słowników, gdzie każdy element to jeden kompletny zmierzony wpis z CSV wynikowego dla tego danego bloku.
    """
    block_name = "training" if is_training else "main"
    logging.info(f"Rozpoczęcie bloku: {block_name}")

    # Przetasuj bez brzydkich powtórek
    shuffled = shuffle_trials(trials_list)
    block_results: List[Dict[str, Any]] = []

    # Iteruj jeden po drugim dla każdego elementu z rozpiski eksperymentu z CSV
    for idx, trial_data in enumerate(shuffled, start=1):
        # Realizuje właściwy pojedynczy pomiar
        trial_result = run_trial(
            window=window,
            trial_data=trial_data,
            config=config,
            is_training=is_training,
            results=results,
            save_fn=save_fn,
            save_args=save_args,
        )

        # Dograj szczegółowe metadane ułatwiające potem badaczowi analizę (np w R czy SPSS)
        trial_result["subject_id"] = subject_data["ID"] if subject_data else "NA"
        trial_result["age"] = subject_data["Wiek"] if subject_data else "NA"
        trial_result["gender"] = subject_data["Płeć"] if subject_data else "NA"
        trial_result["block"] = block_name
        trial_result["trial_idx"] = idx # Oznacza numer w którym dana sekwencja się pojawiła uczestnikowi po przetasowaniu

        block_results.append(trial_result)

        # Dopisz wyniki od razu do głównej listy wyników, to zabezpiecza dane jeśli badany przerwie w trakcje
        if results is not None:
            results.append(trial_result)

    logging.info(
        f"Blok '{block_name}' zakończony. Łączna suma pomyślnie zrealizowanych prób to: {len(block_results)}"
    )
    return block_results


def calculate_accuracy(block_results: List[Dict[str, Any]]) -> float:
    """Metryka skuteczności uczestnika (Procent poprawnych trafień).

    Sprawdza, z jaką skutecznością badany dopasowywał przyciski do koloru czcionki.
    Skuteczność ta jest wykorzystywana przez główną pętlę w main.py by w bloku 
    treningowym decydować o wypuszczeniu uczestnika na eksperyment główny, 
    bądź przydzieleniu go do kolejnego loopu korekcyjnego treningu.

    Parametry:
        block_results: Baza zmierzonych prób z danego bloku treningowego.

    Zwraca:
        Dokładność (Accuracy) reprezentowana we floacie w zakresie od 0.0 (0%) do 1.0 (100%).
    """
    if not block_results:
        return 0.0

    # Przelicza wszystkie instancje w których pole 'is_correct' zostało ocenione jako '1'
    correct = sum(1 for r in block_results if r["is_correct"] == 1)
    
    # Dzieli poprawne ilości wyników na łączną wielkość bufora bloku
    return correct / len(block_results)
