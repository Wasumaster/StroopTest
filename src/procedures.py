"""Procedury eksperymentalne dla Testu Stroopa.

Moduł ten zawiera pełną logikę renderowania i przeprowadzania poszczególnych
etapów eksperymentu. Obejmuje:

  - show_instruction_image(): wyświetlanie graficznych ekranów instrukcji (pliki JPG),
  - show_screen(): wyświetlanie ekranów tekstowych (komunikaty systemowe, feedback),
  - run_trial(): przeprowadzenie jednej kompletnej próby z pomiarem czasu reakcji,
  - run_block(): iteracja przez cały blok prób (trening lub faza główna),
  - shuffle_trials(): pseudorandomizacja kolejności bodźców,
  - calculate_accuracy(): obliczanie wskaźnika poprawności odpowiedzi,
  - funkcje pomocnicze: _check_quit(), _isi_with_escape(), _show_feedback(),
    _is_valid_sequence(), _repair_sequence().

Oś czasu jednej sesji eksperymentalnej (na poziomie modułu):
  1. Sekwencja ekranów instrukcji graficznych (instrukcja_1, instrukcja_2, instrukcja_3).
  2. Blok treningowy z feedbackiem — uczestnik poznaje zadanie.
  3. Ekran instrukcji po treningu (post_training_instruction_image).
  4. Blok główny bez feedbacku — właściwy pomiar.
"""

import copy
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from psychopy import core, event, logging, visual


# ---------------------------------------------------------------------------
# Mapowanie nazw kolorów (z pliku CSV) na format RGB używany przez PsychoPy.
# PsychoPy używa zakresu od -1.0 (brak składowej) do 1.0 (pełna składowa),
# a nie standardowego zakresu 0–255. Każdy kolor jest listą [R, G, B].
# ---------------------------------------------------------------------------
COLOR_MAP: Dict[str, List[float]] = {
    "red":   [1.0, -1.0, -1.0],   # Czerwony: pełne R, brak G i B
    "green": [-1.0, 0.6, -1.0],   # Zielony: brak R, częściowe G, brak B
    "blue":  [-1.0, -1.0, 1.0],   # Niebieski: brak R i G, pełne B
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

    Funkcja ta pełni rolę tzw. 'Escape Hatch' — mechanizmu pozwalającego
    badaczowi lub uczestnikowi na przerwanie eksperymentu w dowolnym momencie
    bez utraty zebranych do tej pory danych.

    Jeśli klawisz wyjścia zostanie wykryty, funkcja:
      1. Zapisuje zebrane dotychczas wyniki do pliku CSV (jeśli przekazano save_fn).
      2. Zamyka okno graficzne PsychoPy.
      3. Trwale kończy proces za pomocą core.quit().

    Parametry:
        keys:      Lista ciągów znaków (nazw) klawiszy, które zostały naciśnięte.
        quit_key:  Zdefiniowany w konfiguracji klawisz wyjścia (np. 'escape').
        window:    Otwarty obiekt okna PsychoPy do zamknięcia.
        results:   Lista zebranych wyników — przekazywana do awaryjnego zapisu.
        save_fn:   Referencja do funkcji save_results z modułu utils.
        save_args: Krotka z argumentami dla funkcji save_fn (nazwa pliku, konfig).
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

        window.close()
        core.quit()


def show_instruction_image(
    window: visual.Window,
    image_path: str,
    wait_key: str,
    config: Dict[str, Any],
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Wyświetla pojedynczy ekran instrukcji w postaci pliku graficznego (JPG).

    Instrukcje eksperymentu są przechowywane jako obrazy (JPG), a nie jako tekst,
    co pozwala na precyzyjne formatowanie treści z kolorowymi przykładami bodźców.
    Obraz jest skalowany tak, by wypełnił całe okno eksperymentu.

    Ekran pozostaje widoczny do momentu naciśnięcia przez uczestnika klawisza
    kontynuacji (domyślnie: spacja) lub klawisza wyjścia (ESC).

    Parametry:
        window:     Obiekt okna PsychoPy.
        image_path: Bezwzględna ścieżka do pliku graficznego instrukcji (.jpg).
        wait_key:   Klawisz powodujący przejście do następnego ekranu (np. 'space').
        config:     Pełny słownik konfiguracyjny (do pobrania klawisza wyjścia).
        results:    Dotychczas zebrane wyniki (na wypadek naciśnięcia ESC).
        save_fn:    Funkcja służąca do awaryjnego zapisu danych.
        save_args:  Argumenty do funkcji zapisu.
    """
    quit_key = config["keys"]["quit"]

    # Tworzymy obiekt obrazu rozciągnięty na pełne okno (units='norm' przy size=(2,2)
    # oznacza zajęcie całej przestrzeni od -1 do 1 na obu osiach)
    image_stim = visual.ImageStim(
        win=window,
        image=image_path,
        size=(2, 2),
        units="norm",
    )

    image_stim.draw()
    window.flip()

    # Pętla oczekuje wyłącznie na klawisz kontynuacji lub wyjścia awaryjnego
    while True:
        pressed = event.waitKeys(keyList=[wait_key, quit_key])

        if pressed is None:
            continue

        _check_quit(pressed, quit_key, window, results, save_fn, save_args)

        if wait_key in pressed:
            break


def show_screen(
    window: visual.Window,
    text_content: str,
    wait_key: str,
    config: Dict[str, Any],
    results: Optional[List[Dict[str, Any]]] = None,
    save_fn: Optional[Any] = None,
    save_args: Optional[Tuple] = None,
) -> None:
    """Wyświetla ekran z komunikatem tekstowym i czeka na reakcję uczestnika.

    Używana do wyświetlania komunikatów systemowych, takich jak informacja
    o wyniku treningu (zbyt niska dokładność), ekran końcowy lub ekran z
    prośbą o ponowne przejście treningu. Nie jest używana do instrukcji
    eksperymentu — te są wyświetlane przez show_instruction_image().

    Parametry:
        window:       Obiekt okna PsychoPy.
        text_content: Treść komunikatu do wyświetlenia na ekranie.
        wait_key:     Oczekiwany klawisz do przejścia dalej (np. 'space').
        config:       Pełny słownik konfiguracyjny (czcionki, kolory, klawisze).
        results:      Dotychczas zebrane wyniki (na wypadek naciśnięcia ESC).
        save_fn:      Funkcja służąca do awaryjnego zapisu danych.
        save_args:    Argumenty do funkcji zapisu.
    """
    quit_key = config["keys"]["quit"]
    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]

    stim = visual.TextStim(
        win=window,
        text=text_content,
        color=text_color,
        font=font_name,
        height=0.04,     # Wielkość czcionki względna (w jednostkach 'norm')
        wrapWidth=1.5,   # Szerokość przed zawinięciem wiersza
        units="norm",
    )

    stim.draw()
    window.flip()

    while True:
        pressed = event.waitKeys(keyList=[wait_key, quit_key])

        if pressed is None:
            continue

        _check_quit(pressed, quit_key, window, results, save_fn, save_args)

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
    """Wykonuje pojedynczą próbę zadania Stroopa — jeden pełny cykl prezentacji.

    Oś czasu jednej próby (Trial Timeline):
      1. ISI (Inter-Stimulus Interval) — czysty ekran przez losowy czas (jitter).
         Losowość czasu ISI zapobiega antycypowaniu momentu pojawienia się bodźca.
      2. Fiksacja — krzyżyk '+' wyświetlany przez stały czas, skupia uwagę uczestnika.
      3. Bodziec — słowo testowe w odpowiednim kolorze. Zegar RT startuje natychmiast
         po wyświetleniu (po wywołaniu window.flip()).
      4. Oczekiwanie na odpowiedź — nasłuchiwanie klawiatury z twardym timeoutem.
         Jeśli uczestnik nie odpowie w czasie, próba jest kodowana jako błędna.
      5. Zapis wyników próby — słownik z danymi o poprawności i czasie reakcji.
      6. Feedback (tylko w fazie treningowej) — komunikat o błędzie lub braku odpowiedzi.

    Parametry:
        window:     Obiekt okna graficznego PsychoPy.
        trial_data: Słownik z parametrami próby (word, color, congruency, corr_ans).
        config:     Słownik parametrów globalnych (timing, keys, gui).
        is_training: Flaga logiczna — True aktywuje wyświetlanie feedbacku po błędzie.
        results:    Lista zebranych prób (do awaryjnego zapisu przy ESC).
        save_fn:    Funkcja zapisująca wyniki.
        save_args:  Argumenty do funkcji zapisu.

    Zwraca:
        Słownik reprezentujący surowe dane wynikowe tej konkretnej próby.
    """
    quit_key = config["keys"]["quit"]
    timing = config["timing"]
    response_mapping = config["keys"]["response_mapping"]

    # Pełna lista klawiszy, na które program reaguje (strzałki kierunkowe + ESC)
    valid_keys = list(response_mapping.keys()) + [quit_key]

    text_color = config["gui"]["text_color"]
    font_name = config["gui"]["font_name"]
    font_size = config["gui"]["font_size"]

    # Parametry bodźca odczytane z wiersza pliku CSV
    word = trial_data["word"]
    color_name = trial_data["color"]
    corr_ans = trial_data["corr_ans"]

    # Mapowanie nazwy koloru (np. "red") na wartości RGB dla PsychoPy.
    # Jeśli kolor z CSV nie jest w COLOR_MAP, jako zapasowy używany jest kolor tekstu z konfiguracji.
    stimulus_color = COLOR_MAP.get(color_name, text_color)

    # --- Krok 1: ISI z jitterem (losowy pusty ekran między próbami) ---
    # Losowy czas ISI zmniejsza efekty antycypacji i torowania sekwencyjnego.
    isi_duration = random.uniform(timing["isi_min"], timing["isi_max"])
    window.flip()  # Czysty ekran

    _isi_with_escape(
        isi_duration, quit_key, window, results, save_fn, save_args,
    )

    # --- Krok 2: Krzyżyk fiksacyjny ---
    # Skupia wzrok uczestnika na środku ekranu tuż przed bodźcem.
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

    # --- Krok 3: Prezentacja bodźca ---
    # Czyszczenie bufora klawiatury zapobiega „przeciekaniu" wciśnięć z poprzedniej próby.
    event.clearEvents()

    stimulus = visual.TextStim(
        win=window,
        text=word,
        color=stimulus_color,
        font=font_name,
        height=font_size,
        units="pix",
        bold=True,  # Pogrubienie zwiększa wyrazistość bodźca
    )
    stimulus.draw()
    window.flip()  # Bodziec pojawia się na ekranie — od tej chwili liczy się czas

    # Zegar RT startuje natychmiast po fizycznym wyświetleniu bodźca (po flip())
    rt_clock = core.Clock()

    # --- Krok 4: Oczekiwanie na odpowiedź ---
    pressed_key: Optional[str] = None
    rt: Optional[float] = None
    is_correct: int = 0

    # event.waitKeys() blokuje wykonanie do momentu naciśnięcia klawisza lub upłynięcia timeoutu.
    # timeStamped=rt_clock powoduje zwrócenie czasu wciśnięcia mierzonego od startu zegara RT.
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

        # Poprawność kodowana binarnie: 1 = dobra odpowiedź, 0 = zła odpowiedź
        is_correct = 1 if pressed_key == corr_ans else 0
    else:
        # Timeout — uczestnik nie odpowiedział w wyznaczonym czasie
        pressed_key = None
        rt = None
        is_correct = 0

    # --- Krok 5: Zapis wyników próby ---
    # Kompletny rekord danych dla jednej próby. RT zapisywany jest w sekundach
    # z dokładnością do 4 miejsc po przecinku (np. 0.4502).
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

    # --- Krok 6: Feedback (wyłącznie w fazie treningowej) ---
    # W fazie głównej feedback jest wyłączony, aby nie wpływać na wyniki.
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
    """Odczekuje określony czas, równocześnie sprawdzając klawisz wyjścia awaryjnego.

    Standardowe funkcje blokujące (time.sleep, core.wait) całkowicie zatrzymują
    wątek i uniemożliwiają reagowanie na klawiaturę. Ta funkcja rozwiązuje problem
    poprzez aktywne odpytywanie klawiatury w krótkiej pętli z drzemką 10ms,
    co pozwala na natychmiastowe wykrycie ESC bez obciążenia procesora.

    Parametry:
        duration:  Czas do odczekania w sekundach.
        quit_key:  Klawisz wyjścia awaryjnego (np. 'escape').
        window:    Obiekt okna PsychoPy (do zamknięcia podczas awaryjnego wyjścia).
        results:   Lista zebranych dotąd prób do uratowania przy ESC.
        save_fn:   Odwołanie do funkcji zapisującej pliki wynikowe.
        save_args: Argumenty do powyższej funkcji.
    """
    timer = core.Clock()
    while timer.getTime() < duration:
        keys = event.getKeys(keyList=[quit_key])
        if keys:
            _check_quit(
                keys, quit_key, window, results, save_fn, save_args,
            )
        # Drzemka 10ms zapobiega wykorzystaniu 100% CPU przez aktywne czekanie
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

    Feedback jest kluczowym elementem fazy treningowej — uczy uczestnika
    prawidłowego mapowania klawiszy na kolory. Ekran feedbacku pojawia się
    wyłącznie wtedy, gdy odpowiedź była niepoprawna lub gdy upłynął czas
    na odpowiedź (timeout). Przy poprawnej odpowiedzi funkcja kończy się
    natychmiastowo bez wyświetlania czegokolwiek.

    Parametry:
        window:      Obiekt okna PsychoPy.
        config:      Słownik ustawień (teksty feedbacku z sekcji 'messages').
        pressed_key: Klawisz wciśnięty przez uczestnika lub None (timeout).
        is_correct:  1 = poprawna odpowiedź, 0 = błędna lub brak.
        results:     Baza wyników — do zapisu awaryjnego przy ESC.
        save_fn:     Funkcja zapisu wyników.
        save_args:   Argumenty funkcji zapisu.
    """
    # Przy poprawnej odpowiedzi nie wyświetlamy żadnego feedbacku
    if is_correct:
        return

    messages = config["messages"]
    quit_key = config["keys"]["quit"]

    # Dobór komunikatu zależny od rodzaju błędu
    if pressed_key is None:
        feedback_text = messages["timeout_feedback"]  # Brak odpowiedzi w czasie
    else:
        feedback_text = messages["error_feedback"]    # Wciśnięto błędny klawisz

    # Feedback wyświetlany jest na czerwono, co wizualnie sygnalizuje błąd
    feedback_stim = visual.TextStim(
        win=window,
        text=feedback_text,
        color=[1.0, -0.2, -0.2],  # Intensywny czerwony kolor alertu
        font=config["gui"]["font_name"],
        height=config["gui"]["font_size"],
        units="pix",
        bold=True,
    )
    feedback_stim.draw()
    window.flip()

    # Feedback wyświetlany jest przez czas zdefiniowany w konfiguracji (feedback_duration)
    _isi_with_escape(
        config["timing"]["feedback_duration"],
        quit_key, window, results, save_fn, save_args,
    )


def shuffle_trials(trials_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Przeprowadza pseudorandomizację listy bodźców z gwarancją braku powtórzeń.

    Zwykłe losowe tasowanie (random.shuffle) może spowodować, że to samo słowo
    pojawi się na dwóch kolejnych pozycjach, co wywołuje efekt torowania
    leksykalnego (lexical priming) i zniekształca pomiar czasu reakcji.

    Reguła walidacji: żadne dwie sąsiednie próby nie mogą zawierać tego samego
    słowa (kolumna 'word'), niezależnie od koloru czcionki. Dotyczy to zarówno
    prób kongruentnych i inkongruentnych (np. CZERWONY, ZIELONY, NIEBIESKI), jak
    i słów neutralnych (np. malina, rakieta).

    Algorytm działa dwuetapowo:
      1. Brute-force: tasuje listę do 1000 razy i za każdym razem sprawdza
         poprawność sekwencji. Dla typowej liczby prób (12–50) metoda ta
         niemal zawsze kończy się sukcesem w pierwszych kilku iteracjach.
      2. Chirurgiczne naprawy: jeśli brute-force zawiedzie (bardzo mała pula
         i wiele powtórzeń), wywołuje _repair_sequence(), która przechodzi
         przez listę i zamienia miejscami problematyczne elementy.

    Parametry:
        trials_list: Oryginalna lista słowników z próbami (z load_trials).

    Zwraca:
        Nową, przetasowaną listę gotową do prezentacji uczestnikowi.
    """
    # Głęboka kopia chroni oryginalną listę przed modyfikacją w miejscu
    trials = copy.deepcopy(trials_list)
    max_attempts = 1000

    for _ in range(max_attempts):
        random.shuffle(trials)
        if _is_valid_sequence(trials):
            return trials

    # Fallback: po 1000 nieudanych próbach tasowania uruchamiamy ręczną naprawę
    logging.warning(
        "shuffle_trials: nie udało się uzyskać poprawnej sekwencji "
        "po 1000 próbach brute-force — rozpoczynam ręczne naprawianie lokalne."
    )
    return _repair_sequence(trials)


def _is_valid_sequence(trials: List[Dict[str, str]]) -> bool:
    """Sprawdza, czy sekwencja nie zawiera tego samego słowa na dwóch kolejnych pozycjach.

    Warunek jest rygorystyczny: to samo słowo ('word') nie może wystąpić dwa razy
    pod rząd, niezależnie od koloru czcionki ('color'). Dzięki temu eliminowane
    jest zarówno torowanie leksykalne (lexical priming), jak i torowanie przez
    identyczną konfigurację (słowo + kolor).

    Przykłady blokowanych sekwencji:
      - CZERWONY (red) → CZERWONY (blue)   ← to samo słowo, inny kolor — ZABLOKOWANE
      - malina (red)   → malina (green)    ← to samo słowo neutralne   — ZABLOKOWANE
      - CZERWONY (red) → ZIELONY (red)     ← różne słowa, ten sam kolor — DOZWOLONE

    Parametry:
        trials: Lista prób do walidacji.

    Zwraca:
        True jeśli sekwencja jest poprawna (brak powtórzeń), False jeśli wykryto powtórzenie.
    """
    for i in range(len(trials) - 1):
        # Sprawdzamy wyłącznie pole 'word' — kolor czcionki nie jest kryterium
        if trials[i]["word"] == trials[i + 1]["word"]:
            return False
    return True


def _repair_sequence(
    trials: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Naprawia sekwencję poprzez iteracyjne zamiany miejsc problematycznych elementów.

    Wywoływana wyłącznie jako fallback po 1000 nieudanych próbach brute-force shuffle.
    Przechodzi przez listę od lewej do prawej. Gdy wykryje, że dwie sąsiednie próby
    mają to samo słowo (pozycje i i i+1), szuka dalej w liście elementu j (j > i+1),
    który:
      a) ma inne słowo niż próba na pozycji i,
      b) po wstawieniu na pozycję i+1 nie spowoduje nowego konfliktu z sąsiadami
         (pozycje i+1-1 = i oraz i+1+1 = i+2 po zamianie).

    Kryterium konfliktu jest spójne z _is_valid_sequence: tylko pole 'word'.

    Parametry:
        trials: Lista prób po nieudanych próbach brute-force shuffle.

    Zwraca:
        Listę z naprawionymi (lub najlepiej możliwymi) powtórzeniami słów.
    """
    n = len(trials)
    for i in range(n - 1):
        # Wykrycie konfliktu: to samo słowo na dwóch kolejnych pozycjach
        if trials[i]["word"] == trials[i + 1]["word"]:

            swapped = False
            for j in range(i + 2, n):
                # Kandydat musi mieć inne słowo niż próba na pozycji i
                if trials[j]["word"] != trials[i]["word"]:

                    # Sprawdzamy, czy wstawienie kandydata nie stworzy nowego
                    # konfliktu z jego przyszłym prawym sąsiadem (j+1)
                    if j + 1 < n:
                        if trials[i + 1]["word"] == trials[j + 1]["word"]:
                            continue
                    # Sprawdzamy, czy wstawienie kandydata nie stworzy nowego
                    # konfliktu z jego przyszłym lewym sąsiadem (j-1, który
                    # po zamianie staje się sąsiadem pierwotnego i+1)
                    if j - 1 >= 0 and j - 1 != i:
                        if trials[i + 1]["word"] == trials[j - 1]["word"]:
                            continue

                    # Zamiana: element j trafia na pozycję i+1
                    trials[i + 1], trials[j] = trials[j], trials[i + 1]
                    swapped = True
                    break

            if not swapped:
                logging.warning(
                    f"Nie udało się naprawić duplikatu słowa na pozycji {i}/{i+1} "
                    f"ze względu na zbyt małą pulę różnych słów."
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
    """Przeprowadza cały blok zadań — trening lub fazę główną eksperymentu.

    Blok to sekwencja wszystkich prób z pliku CSV, przetasowanych pseudorandomowo.
    Funkcja iteruje przez każdą próbę, wywołując run_trial(), a następnie
    wzbogaca wyniki o metadane uczestnika (ID, wiek, płeć) i numer bloku.

    Metadane są dodawane tutaj (a nie w run_trial), ponieważ run_trial jest
    funkcją niskiego poziomu — odpowiada wyłącznie za jeden cykl prezentacji.
    Kontekst sesji (kto jest badany, jaki to blok) jest zarządzany na tym poziomie.

    Parametry:
        window:       Obiekt okna wyświetlającego.
        trials_list:  Lista prób wczytana przez load_trials().
        config:       Parametry konfiguracyjne (timing, gui, keys).
        is_training:  True = blok treningowy (z feedbackiem), False = blok główny.
        subject_data: Słownik z danymi uczestnika (ID, Wiek, Płeć).
        results:      Globalna lista wyników — aktualizowana na bieżąco.
        save_fn:      Funkcja awaryjnego zapisu danych.
        save_args:    Argumenty do funkcji zapisu.

    Zwraca:
        Listę słowników z wynikami wszystkich prób przeprowadzonych w tym bloku.
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

        # Wzbogacenie rekordu o metadane kontekstu sesji
        trial_result["subject_id"] = subject_data["ID"] if subject_data else "NA"
        trial_result["age"] = subject_data["Wiek"] if subject_data else "NA"
        trial_result["gender"] = subject_data["Płeć"] if subject_data else "NA"
        trial_result["block"] = block_name
        trial_result["trial_idx"] = idx  # Numer próby w przetasowanej sekwencji

        block_results.append(trial_result)

        # Natychmiastowe dołączenie wyników do globalnej listy chroni dane
        # przed utratą w przypadku przerwania eksperymentu w trakcie bloku
        if results is not None:
            results.append(trial_result)

    logging.info(
        f"Blok '{block_name}' zakończony. Łączna suma prób: {len(block_results)}"
    )
    return block_results


def calculate_accuracy(block_results: List[Dict[str, Any]]) -> float:
    """Oblicza wskaźnik poprawności odpowiedzi (Accuracy) dla danego bloku.

    Accuracy jest kluczową miarą używaną w pętli treningowej w main.py
    do decydowania, czy uczestnik może przejść do fazy głównej eksperymentu,
    czy musi powtórzyć trening. Próg minimalny jest zdefiniowany w konfiguracji
    (thresholds.training_min_accuracy).

    Parametry:
        block_results: Lista słowników z wynikami prób danego bloku treningowego.

    Zwraca:
        Wskaźnik dokładności jako liczba zmiennoprzecinkowa w zakresie 0.0–1.0,
        gdzie 1.0 oznacza 100% poprawnych odpowiedzi.
    """
    if not block_results:
        return 0.0

    correct = sum(1 for r in block_results if r["is_correct"] == 1)
    return correct / len(block_results)
