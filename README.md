# Specyfikacja Projektu: Implementacja Testu Stroopa w PsychoPy

## 1. Wprowadzenie teoretyczne i cele projektu

Projekt zakłada stworzenie narzędzia do przeprowadzania **Zadania Stroopa (Stroop Task)** przy użyciu biblioteki PsychoPy. Efekt Stroopa jest jednym z najbardziej znanych fenomenów w psychologii poznawczej i kognitywistyce, ilustrującym mechanizmy kontroli poznawczej, uwagi selektywnej, rozwiązywania konfliktów (tzw. konflikt inkongruencji) oraz automatyzmu procesów czytania.

### Cel główny

Celem oprogramowania jest precyzyjny pomiar czasu reakcji (RT – *Reaction Time*) oraz poprawności odpowiedzi uczestnika w warunkach:

* **Kongruentnych (zgodnych):** Kolor czcionki i znaczenie słowa są identyczne (np. słowo „CZERWONY" napisane czerwoną czcionką).
* **Inkongruentnych (niezgodnych):** Kolor czcionki różni się od znaczenia słowa (np. słowo „ZIELONY" napisane niebieską czcionką).
* **Neutralnych:** Słowa niezwiązane z kolorami (np. „malina", „rakieta") wydrukowane w jednym z trzech kolorów czcionki.

Aplikacja jest zaprojektowana modułowo. Pozwala to na łatwą replikację badania, modyfikację parametrów bez ingerencji w kod źródłowy Pythona oraz zachowanie przejrzystości struktury.

---

## 2. Architektura i struktura plików

Struktura repozytorium rozdziela logikę, konfigurację, zasoby oraz wyniki.

```text
/
├── instructions/                # Graficzne ekrany instrukcji (pliki JPG)
│   ├── instrukcja_1.jpg         # Ekran 1: zasady zadania i mapowanie klawiszy
│   ├── instrukcja_2.jpg         # Ekran 2: wyjaśnienie warunków (kongruentne/neutralne)
│   ├── instrukcja_3.jpg         # Ekran 3: informacja o fazie treningowej
│   └── instrukcja_po_fazie_treningowej.jpg  # Ekran po treningu: przejście do fazy głównej
├── stimulus/                    # Pliki wejściowe definiujące warunki eksperymentalne
│   ├── training_trials.csv      # Lista bodźców dla fazy treningowej
│   └── main_trials.csv          # Pełna lista bodźców dla fazy głównej
├── results/                     # Wyniki badań (generowane automatycznie)
├── src/                         # Kod źródłowy aplikacji
│   ├── main.py                  # Punkt wejścia i główna logika przebiegu eksperymentu
│   ├── config.yaml              # Globalny plik konfiguracyjny (parametryzacja)
│   ├── procedures.py            # Procedury eksperymentalne i logika pojedynczych prób
│   └── utils.py                 # Funkcje pomocnicze (konfiguracja, pliki, dane badanego)
├── requirements.txt             # Zależności systemowe (pip)
└── README.md                    # Dokumentacja i instrukcja uruchomienia
```

---

## 3. Parametryzacja środowiska – plik `config.yaml`

Cała logika dotycząca wyglądu i przebiegu eksperymentu jest wyabstrahowana do zewnętrznego pliku konfiguracyjnego `config.yaml`. Umożliwia to elastyczną zmianę parametrów środowiskowych przez badacza bez znajomości programowania.

### Zdefiniowane parametry

```yaml
experiment:
  name: "Stroop Task"
  version: "1.1.0"
  log_level: "info"          # Poziom logowania (debug, info, warning, error)

gui:
  full_screen: true
  window_size: [1920, 1080]
  bg_color: [0, 0, 0]         # Kolor tła w przestrzeni RGB (PsychoPy: zakres -1 do 1)
  text_color: [1, 1, 1]       # Kolor tekstu (biały)
  font_name: "Open Sans"
  font_size: 40               # Bazowy rozmiar czcionki bodźców (w pikselach)

timing:
  fixation_cross: 0.5         # Czas ekspozycji krzyżyka fiksacyjnego [s]
  stimulus_timeout: 3.0       # Maksymalny czas na reakcję [s]
  isi_min: 0.4                # Minimalny Inter-Stimulus Interval [s]
  isi_max: 0.8                # Maksymalny Inter-Stimulus Interval [s]
  feedback_duration: 1.0      # Czas wyświetlania feedbacku o błędzie [s]

keys:
  response_mapping:
    left: "red"               # Strzałka w lewo = czerwony
    down: "green"             # Strzałka w dół  = zielony
    right: "blue"             # Strzałka w prawo = niebieski
  continue: "space"
  quit: "escape"

thresholds:
  training_min_accuracy: 0.8  # Minimalny próg poprawności do zaliczenia treningu (80%)
  max_training_loops: 3       # Maksymalna liczba powtórzeń treningu
```

---

## 4. Oś czasu pojedynczej próby (Trial Timeline)

Precyzja pomiaru w PsychoPy jest kluczowa. Oś czasu (*Trial Sequence*) jest zsynchronizowana z odświeżaniem monitora (V-Sync).

Każda iteracja przez zbiór bodźców realizuje poniższy cykl:

1. **Jittered ISI (Inter-Stimulus Interval)**

   * Pusty ekran wyświetlany przez losowy czas między `isi_min` a `isi_max`.
   * Zapobiega habituacji i antycypowaniu bodźca przez uczestnika.

2. **Fixation Cross**

   * Znak `+` na środku ekranu (500 ms).
   * Skupia uwagę uczestnika na centralnym punkcie przestrzeni wizualnej.

3. **Prezentacja Bodźca (Stimulus Onset)**

   * Wyświetlenie docelowego słowa w odpowiednim kolorze.
   * Jednoczesny reset zegara `core.Clock()` — od tej chwili mierzony jest RT.
   * Wyczyszczenie bufora zdarzeń klawiatury (`event.clearEvents()`) przed bodźcem.

4. **Nasłuch i Reakcja**

   * System oczekuje na reakcję uczestnika (naciśnięcie klawisza strzałki).
   * Oczekiwanie trwa do momentu wykrycia odpowiedzi lub przekroczenia `stimulus_timeout`.

5. **Ewaluacja i Zapis**

   * Obliczenie poprawności odpowiedzi (1 = poprawnie, 0 = błędnie lub brak).
   * Rejestracja czasu reakcji (RT) w sekundach z dokładnością 4 miejsc po przecinku.

6. **Feedback (Wyłącznie w fazie treningowej)**

   * Komunikat „BŁĄD" przy błędnej odpowiedzi.
   * Komunikat „ZA WOLNO" po przekroczeniu limitu czasu.
   * W fazie głównej feedback jest wyłączony — pomiar jest „cichy".

---

## 5. Przebieg procedury eksperymentalnej

### Etap 0: Inicjalizacja i dane demograficzne

Skrypt:

* wczytuje konfigurację z `config.yaml`,
* wywołuje okno dialogowe `gui.DlgFromDict()` do zebrania danych od uczestnika,
* inicjuje obiekt okna głównego PsychoPy.

Zbierane dane:

* `Wiek` – walidacja, czy podano dodatnią liczbę całkowitą,
* `Płeć` – K/M do wyboru z listy,
* `ID` – automatycznie generowane w tle w formacie `SUB_YYYYMMDD_HHMMSS`.

### Etap 1: Sekwencja instrukcji graficznych

Trzy ekrany instrukcji (pliki JPG) są wyświetlane kolejno:

1. `instrukcja_1.jpg` — ogólne zasady zadania i mapowanie klawiszy na kolory,
2. `instrukcja_2.jpg` — wyjaśnienie warunków kongruentnych i neutralnych z przykładami,
3. `instrukcja_3.jpg` — informacja o fazie treningowej i timeoucie.

Każdy ekran czeka na naciśnięcie klawisza `spacja`.

### Etap 2: Pętla treningowa

* Odczyt `training_trials.csv`.
* Pseudorandomizacja kolejności prób (gwarancja: żadne słowo nie pojawi się dwa razy pod rząd).
* Wykonanie bloku treningowego z feedbackiem.
* Obliczenie wskaźnika poprawności:

$$Accuracy = \frac{N_{correct}}{N_{total}}$$

#### Warunek niespełniony (Accuracy < próg)

System wyświetla komunikat o zbyt niskiej dokładności i powraca do treningu.
Maksymalna liczba powtórzeń zdefiniowana jest w `max_training_loops` (domyślnie 3).
Po wyczerpaniu limitu uczestnik jest dyskwalifikowany, a zebrane dane zapisywane.

#### Warunek spełniony (Accuracy ≥ próg)

Uczestnik przechodzi do instrukcji po treningu.

### Etap 3: Instrukcja po fazie treningowej

Wyświetlenie ekranu graficznego `instrukcja_po_fazie_treningowej.jpg` informującego
o zakończeniu treningu i nadchodzącym starcie fazy głównej. Uczestnik naciska spację.

### Etap 4: Faza główna (Eksperyment właściwy)

* Uruchomienie bloku głównego prób (funkcja `run_block`).
* Pseudorandomizacja prób z pliku `main_trials.csv`.
* Zbieranie pełnych danych: RT, poprawność, znacznik czasu dla każdej próby.
* Brak feedbacku — uczestnik nie otrzymuje informacji o poprawności.

### Etap 5: Ekran końcowy i zapis danych

* Finalny zapis wyników wszystkich prób (trening + faza główna) do pliku CSV.
* Wyświetlenie ekranu z podziękowaniem.
* Zamknięcie okna i zwolnienie zasobów (`core.quit()`).

---

## 6. Mechanizm pseudorandomizacji bodźców

Funkcja `shuffle_trials()` w `procedures.py` gwarantuje, że **żadne słowo nie pojawi
się na dwóch kolejnych pozycjach w sekwencji** — niezależnie od koloru czcionki.

Reguła jest rygorystyczna celowo: nawet jeśli to samo słowo pojawia się w dwóch próbach
z różnymi kolorami (np. CZERWONY-red i CZERWONY-blue), umieszczenie ich obok siebie
wywołałoby torowanie leksykalne i zaniżyło czas reakcji na drugą próbę.

Algorytm dwuetapowy:
1. **Brute-force (do 1000 iteracji):** losowe tasowanie i walidacja sekwencji.
2. **Repair fallback:** przy bardzo małej puli bodźców — iteracyjne zamiany par.

---

## 7. Architektura kodu źródłowego

### `main.py`

Główny punkt wejścia. Orkiestruje przebieg eksperymentu: inicjalizacja, sekwencja
instrukcji graficznych, pętla treningowa z kontrolą progu poprawności, instrukcja
po treningu, faza główna oraz finalny zapis wyników.

### `utils.py`

Czyste funkcje narzędziowe (bez logiki eksperymentalnej):

* `load_config` – parsowanie i walidacja pliku YAML.
* `setup_logging` – inicjalizacja logowania PsychoPy.
* `get_subject_data` – zebranie danych przez GUI z automatycznym generowaniem ID.
* `build_instruction_image_path` – budowanie ścieżki do pliku graficznego instrukcji.
* `build_trial_path` – budowanie ścieżki do pliku CSV z bodźcami.
* `load_trials` – ładowanie i walidacja pliku CSV z bodźcami.
* `save_results` – bezpieczny zapis zebranych wyników do pliku CSV.

### `procedures.py`

Logika wizualna i obsługa zadań w oknie PsychoPy:

* `show_instruction_image` – wyświetlanie graficznych ekranów instrukcji (JPG).
* `show_screen` – wyświetlanie ekranów tekstowych (komunikaty systemowe).
* `run_trial` – jeden pełny cykl próby: ISI → fiksacja → bodziec → odpowiedź → feedback.
* `run_block` – pętla iterująca przez wszystkie próby bloku (trening lub faza główna).
* `shuffle_trials` – pseudorandomizacja z gwarancją braku powtórzeń słów.
* `calculate_accuracy` – obliczanie wskaźnika poprawności odpowiedzi.

Wszystkie procedury monitorują klawisz ESC nawet podczas czasów ISI — gwarantuje to
możliwość przerwania eksperymentu w dowolnym momencie z automatycznym zapisem danych.

---

## 8. Wymagania techniczne i struktura danych wynikowych

### Struktura plików wejściowych (`Stimulus CSV`)

Każdy plik bodźców musi zawierać kolumny:

| Kolumna      | Opis                                              |
| ------------ | ------------------------------------------------- |
| `word`       | Wyświetlane słowo (np. CZERWONY, malina)          |
| `color`      | Kolor czcionki (red / green / blue)               |
| `congruency` | Typ warunku: congruent / incongruent / neutral    |
| `corr_ans`   | Poprawna odpowiedź (left / down / right)          |

### Struktura plików wynikowych (`Results CSV`)

Format nazwy pliku:

```text
results/SUB_YYYYMMDD_HHMMSS_Stroop_YYYYMMDD_HHMM.csv
```

Kolumny danych:

| Kolumna        | Opis                                            |
| -------------- | ----------------------------------------------- |
| `subject_id`   | Automatycznie generowane ID badanego            |
| `age`          | Wiek uczestnika                                 |
| `gender`       | Płeć (K/M)                                      |
| `block`        | Faza eksperymentu (training / main)             |
| `trial_idx`    | Numer próby w przetasowanej sekwencji           |
| `word`         | Wyświetlane słowo                               |
| `color`        | Kolor czcionki                                  |
| `congruency`   | Typ warunku                                     |
| `expected_key` | Poprawny klawisz                                |
| `pressed_key`  | Klawisz naciśnięty przez uczestnika             |
| `is_correct`   | 1 = poprawna odpowiedź, 0 = błąd lub brak       |
| `rt`           | Czas reakcji w sekundach (np. 0.4502) lub „NA"  |
| `timestamp`    | ISO 8601 – znacznik czasu wykonania próby       |

---

## 9. Dobre praktyki i bezpieczeństwo

### Globalny klawisz awaryjny (Escape Hatch)

Naciśnięcie klawisza `ESC` w dowolnym momencie eksperymentu:

* zapisuje zebrane do tej pory wyniki do pliku CSV,
* bezpiecznie zamyka aplikację,
* kończy proces bez utraty danych.

### Optymalizacja bufora klawiatury

Przed prezentacją każdego bodźca wykonywane jest:

```python
event.clearEvents()
```

Zapobiega to fałszywie krótkim czasom reakcji spowodowanym „przeciekaniem" wciśnięć z poprzedniej próby.

### Logowanie systemowe

Wszystkie operacje są rejestrowane za pomocą `logging.LogFile()` PsychoPy. Pliki logów zapisywane są w katalogu `results/` z unikalną nazwą opartą o znacznik czasu. Rejestrowane są m.in.: inicjalizacja modułów, wyniki poszczególnych bloków, ostrzeżenia i błędy krytyczne.

---

## 10. Szybki start (Quick Start)

### Wymagania systemowe

* **Python 3.10 lub 3.11** (PsychoPy nie wspiera Python 3.12+)
* System operacyjny: Windows 10/11, macOS lub Linux

### Instalacja

```bash
# 1. Sklonuj repozytorium
git clone <url-repozytorium>
cd StroopTest-1

# 2. Utwórz środowisko wirtualne (Python 3.11)
py -3.11 -m venv .venv

# 3. Aktywuj środowisko
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# 4. Zaktualizuj pip i zainstaluj zależności
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Uruchomienie eksperymentu

```bash
python src/main.py
```

### Przebieg

1. Pojawi się okno dialogowe — wpisz **wiek** i wybierz **płeć** (ID generuje się automatycznie).
2. Trzy ekrany instrukcji graficznych — naciśnij **SPACJĘ** po każdym.
3. Faza treningowa z feedbackiem — odpowiadaj klawiszy strzałek.
4. Jeśli dokładność ≥ 80% → ekran przejścia → faza główna.
5. Faza główna (bez feedbacku) — pełny pomiar.
6. Ekran końcowy — wyniki zapisane w katalogu `results/`.

### Klawisze

| Klawisz     | Akcja                                               |
|-------------|-----------------------------------------------------|
| ← (lewo)    | Czerwony                                            |
| ↓ (dół)     | Zielony                                             |
| → (prawo)   | Niebieski                                           |
| SPACJA      | Kontynuuj (ekrany instrukcji i komunikaty)          |
| ESC         | Przerwij eksperyment (dane zostaną zapisane)        |

### Wyniki

Plik CSV w formacie `results/{ID}_Stroop_YYYYMMDD_HHMM.csv` z kolumnami:

```
subject_id, age, gender, block, trial_idx, word, color,
congruency, expected_key, pressed_key, is_correct, rt, timestamp
```

### Konfiguracja

Wszystkie parametry eksperymentu (czasy, kolory, progi, klawisze) można modyfikować w pliku `src/config.yaml` bez zmian w kodzie źródłowym.

---

## 11. Literatura naukowa

Poniższe publikacje stanowią teoretyczne i metodologiczne podstawy implementacji Zadania Stroopa. Zostały dobrane tak, aby obejmować zarówno klasyczne prace źródłowe, jak i nowsze metaanalizy oraz przeglądy systematyczne.

### Prace źródłowe i klasyczne

- **Stroop, J. R. (1935).** Studies of interference in serial verbal reactions. *Journal of Experimental Psychology, 18*(6), 643–662. https://doi.org/10.1037/h0054651
  > Oryginalna praca opisująca efekt Stroopa. Pierwsze systematyczne badanie interferencji między czytaniem słów a nazywaniem kolorów.

- **MacLeod, C. M. (1991).** Half a century of research on the Stroop effect: An integrative review. *Psychological Bulletin, 109*(2), 163–203. https://doi.org/10.1037/0033-2909.109.2.163
  > Autorytatywny przegląd 50 lat badań nad efektem Stroopa. Omawia teorie wyjaśniające: model siły nawyku (Habit Strength), model szybkości przetwarzania (Processing Speed) oraz modele uwagi selektywnej.

### Mechanizmy poznawcze i kontrola poznawcza

- **Botvinick, M. M., Braver, T. S., Barch, D. M., Carter, C. S., & Cohen, J. D. (2001).** Conflict monitoring and cognitive control. *Psychological Review, 108*(3), 624–652. https://doi.org/10.1037/0033-295X.108.3.624
  > Teoria monitorowania konfliktu (Conflict Monitoring Theory). Wyjaśnia rolę kory przedniej obręczy (ACC) w wykrywaniu konfliktów przetwarzania — kluczowe dla rozumienia efektu Stroopa jako miary konfliktu poznawczego.

- **Cohen, J. D., Dunbar, K., & McClelland, J. L. (1990).** On the control of automatic processes: A parallel distributed processing account of the Stroop effect. *Psychological Review, 97*(3), 332–361. https://doi.org/10.1037/0033-295X.97.3.332
  > Model PDP (Parallel Distributed Processing) tłumaczący efekt Stroopa przez różnicę w sile trenowanych ścieżek przetwarzania (czytanie vs. nazywanie kolorów).

### Uwaga selektywna i hamowanie

- **Eriksen, B. A., & Eriksen, C. W. (1974).** Effects of noise letters upon the identification of a target letter in a nonsearch task. *Perception & Psychophysics, 16*(1), 143–149. https://doi.org/10.3758/BF03203267
  > Paradygmat flankerów Eriksena — powiązany paradygmat uwagi selektywnej, często stosowany obok zadania Stroopa w bateriach testów kontroli poznawczej.

- **Logan, G. D., & Cowan, W. B. (1984).** On the ability to inhibit thought and action: A theory of an act of control. *Psychological Review, 91*(3), 295–327. https://doi.org/10.1037/0033-295X.91.3.295
  > Model wyścigu (Race Model) dotyczący hamowania reakcji. Kontekst teoretyczny dla rozumienia kontroli behawioralnej mierzonej w zadaniu Stroopa.

### Zastosowania kliniczne i neuropsychologiczne

- **Alvarez, J. A., & Emory, E. (2006).** Executive function and the frontal lobes: A meta-analytic review. *Neuropsychology Review, 16*(1), 17–42. https://doi.org/10.1007/s11065-006-9002-x
  > Metaanaliza dotycząca funkcji wykonawczych i płatów czołowych. Zadanie Stroopa jest tu omawiane jako jeden z kluczowych wskaźników funkcji wykonawczych.

- **Van der Elst, W., Van Boxtel, M. P. J., Van Breukelen, G. J. P., & Jolles, J. (2006).** The Stroop Color-Word Test: Influence of age, sex, and education; and normative data for a large sample across the adult age range. *Assessment, 13*(1), 62–79. https://doi.org/10.1177/1073191105283427
  > Dane normatywne dla Testu Stroopa dla dużej próby populacyjnej. Uwzględnia wpływ wieku, płci i wykształcenia — istotne przy interpretacji wyników badania.

### Metodologia i implementacja komputerowa

- **Peirce, J. W. (2007).** PsychoPy — Psychophysics software in Python. *Journal of Neuroscience Methods, 162*(1–2), 8–13. https://doi.org/10.1016/j.jneumeth.2006.11.017
  > Oryginalna publikacja opisująca bibliotekę PsychoPy użytą w niniejszej implementacji. Omawia precyzję pomiaru czasu, synchronizację z monitorem i architekturę narzędzia.

- **Peirce, J., Gray, J. R., Simpson, S., MacAskill, M., Höchenberger, R., Sogo, H., Kastman, E., & Lindeløv, J. K. (2019).** PsychoPy2: Experiments in behavior made easy. *Behavior Research Methods, 51*(1), 195–203. https://doi.org/10.3758/s13428-018-01193-y
  > Aktualizacja opisująca PsychoPy2 — wersję używaną w projekcie. Omawia m.in. walidację precyzji czasowej i synchronizację V-sync.

- **MacLeod, C. M., & MacDonald, P. A. (2000).** Interdimensional interference in the Stroop effect: Uncovering the cognitive and neural anatomy of attention. *Trends in Cognitive Sciences, 4*(10), 383–391. https://doi.org/10.1016/S1364-6613(00)01530-8
  > Przegląd neuronalnych podstaw efektu Stroopa — istotny kontekst dla interpretacji danych RT zebranych przez niniejsze narzędzie.

### Metaanalizy

- **Hutchison, K. A. (2011).** The interactive effects of listwide control, item-based control, and working memory capacity on Stroop performance. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 37*(4), 851–860. https://doi.org/10.1037/a0023437

- **Verbruggen, F., & Logan, G. D. (2008).** Response inhibition in the stop-signal paradigm. *Trends in Cognitive Sciences, 12*(11), 418–424. https://doi.org/10.1016/j.tics.2008.07.005
  > Przegląd dotyczący hamowania odpowiedzi — powiązany kontekst dla interpretacji błędów i timeoutów w zadaniu Stroopa.
