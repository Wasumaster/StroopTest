# Specyfikacja Projektu: Implementacja Testu Stroopa w PsychoPy

## 1. Wprowadzenie teoretyczne i cele projektu

Projekt zakłada stworzenie narzędzia do przeprowadzania **Zadania Stroopa (Stroop Task)** przy użyciu biblioteki PsychoPy. Efekt Stroopa jest jednym z najbardziej znanych fenomenów w psychologii poznawczej i kognitywistyce, ilustrującym mechanizmy kontroli poznawczej, uwagi selektywnej, rozwiązywania konfliktów (tzw. konflikt inkongruencji) oraz automatyzmu procesów czytania.

### Cel główny

Celem oprogramowania jest precyzyjny pomiar czasu reakcji (RT – *Reaction Time*) oraz poprawności odpowiedzi uczestnika w warunkach:

* **Kongruentnych (zgodnych):** Kolor czcionki i znaczenie słowa są identyczne (np. słowo „CZERWONY” napisane czerwoną czcionką).
* **Inkongruentnych (niezgodnych):** Kolor czcionki różni się od znaczenia słowa (np. słowo „ZIELONY” napisane niebieską czcionką).
* **Neutralnych (opcjonalnie):** Słowa niezwiązane z kolorami (np. „DOM”) lub ciągi znaków (np. „XXXX”) wydrukowane w określonym kolorze.

Aplikacja jest zaprojektowana modułowo. Pozwala to na łatwą replikację badania, modyfikację parametrów bez ingerencji w kod źródłowy Pythona oraz zachowanie przejrzystości struktury.

---

## 2. Architektura i struktura plików

Struktura repozytorium rozdziela logikę, konfigurację, zasoby oraz wyniki.

```text
/
├── instructions/             # Katalog instrukcji i materiałów informacyjnych
│   ├── welcome.txt           # Ekran powitalny i Informed Consent
│   ├── training_inst.txt     # Instrukcja do fazy treningowej
│   └── main_inst.txt         # Instrukcja przejścia do fazy głównej
├── stimulus/                 # Pliki wejściowe definiujące warunki eksperymentalne
│   ├── training_trials.csv   # Lista bodźców dla fazy treningowej
│   └── main_trials.csv       # Pełna randomizowana lista bodźców dla fazy głównej
├── results/                  # Wyniki badan
├── src/                      # Kod źródłowy aplikacji
│   ├── main.py               # Punkt wejścia (Entry point) i główna logika przebiegu
│   ├── config.yaml           # Globalny plik konfiguracyjny (parametryzacja)
│   ├── procedures.py         # Procedury eksperymentalne i logika pojedynczych prób
│   └── utils.py              # Funkcje pomocnicze (konfiguracja, pliki, dane badanego)
├── requirements.txt          # Zależności systemowe (pip)
└── README.md                 # Podstawowa dokumentacja i instrukcja uruchomienia
```

---

## 3. Parametryzacja środowiska – plik `config.yaml`

Cała logika dotycząca wyglądu i przebiegu eksperymentu musi zostać wyabstrahowana do zewnętrznego pliku konfiguracyjnego `config.yaml`. Umożliwia to elastyczną zmianę parametrów środowiskowych przez badacza bez znajomości programowania.

### Zdefiniowane parametry

```yaml
experiment:
  name: "Stroop Task"
  version: "1.1.0"
  log_level: "info"          # Poziom logowania (debug, info, warning, error)

gui:
  full_screen: true
  window_size: [1920, 1080]
  bg_color: [0, 0, 0]         # Przestrzeń barw RGB 
  text_color: [1, 1, 1]       # Kolor tekstu
  font_name: "Open Sans"
  font_size: 40               # Bazowy rozmiar czcionki

timing:
  fixation_cross: 0.5         # Czas ekspozycji punktu fiksacji [s]
  stimulus_timeout: 3.0       # Maksymalny czas na reakcję [s]
  isi_min: 0.4                # Minimalny Inter-Stimulus Interval [s]
  isi_max: 0.8                # Maksymalny Inter-Stimulus Interval [s]
  feedback_duration: 1.0      # Czas wyświetlania feedbacku [s]

keys:
  response_mapping:
    left: "red"
    down: "green"
    right: "blue"
  continue: "space"
  quit: "escape"

thresholds:
  training_min_accuracy: 0.8
  max_training_loops: 3
```

---

## 4. Oś czasu pojedynczej próby (Trial Timeline)

Precyzja pomiaru w PsychoPy jest kluczowa. Oś czasu (*Trial Sequence*) musi być zsynchronizowana z odświeżaniem monitora (V-Sync) w przypadku czasów rzędu milisekund.

Każda iteracja przez zbiór bodźców realizuje poniższy cykl:

1. **Jittered ISI (Inter-Stimulus Interval)**

   * Pusty ekran wyświetlany przez losowy czas między `isi_min` a `isi_max`.
   * Zapobiega habituacji i antycypowaniu bodźca przez uczestnika.

2. **Fixation Cross**

   * Znak `+` na środku ekranu (np. 500 ms).
   * Skupia uwagę uczestnika na centralnym punkcie przestrzeni wizualnej.

3. **Prezentacja Bodźca (Stimulus Onset)**

   * Wyświetlenie docelowego słowa.
   * Jednoczesny reset zegara `core.Clock()`.
   * Wyczyszczenie bufora zdarzeń klawiatury (`event.clearEvents()`).

4. **Nasłuch i Reakcja**

   * System oczekuje na reakcję uczestnika.
   * Oczekiwanie trwa do momentu:

     * wykrycia odpowiedzi,
     * lub przekroczenia `stimulus_timeout`.

5. **Ewaluacja i Zapis**

   * Zatrzymanie zegara po detekcji odpowiedzi.
   * Obliczenie poprawności odpowiedzi.
   * Rejestracja czasu reakcji (RT).

6. **Feedback (Wyłącznie w treningu)**

   * Komunikat „BŁĄD” przy błędnej odpowiedzi.
   * Komunikat „ZA WOLNO” po przekroczeniu limitu czasu.

---

## 5. Przebieg procedury eksperymentalnej (State Machine)

### Etap 0: Inicjalizacja i dane demograficzne

Skrypt:

* ładuje konfigurację,
* wywołuje okno dialogowe `gui.DlgFromDict()` do zebrania danych od uczestnika,
* inicjuje obiekt okna głównego PsychoPy.

Zbierane dane:

* `Wiek` – walidacja, czy podano dodatnią liczbę całkowitą,
* `Płeć` – K/M do wyboru z listy,
* `ID` – automatycznie generowane w tle w formacie `SUB_YYYYMMDD_HHMMSS`.

### Etap 1: Ekran powitalny

Wyświetlenie:

* instrukcji ogólnych,
* zgody uczestnika,
* klauzuli RODO/Informed Consent.

Kontynuacja po naciśnięciu klawisza `continue`.

### Etap 2: Instrukcja fazy treningowej

Wyjaśnienie:

* mapowania klawiszy,
* konieczności reagowania na kolor czcionki,
* ignorowania znaczenia słowa.

### Etap 3: Pętla treningowa

* Odczyt `training_trials.csv`.
* Wykonanie bloku treningowego.
* Obliczenie skuteczności:

$$Accuracy = \frac{N_{correct}}{N_{total}}$$

*(Gdzie $N_{correct}$ to liczba poprawnych odpowiedzi, a $N_{total}$ to łączna liczba prób).*

#### Warunek niespełniony

Jeżeli:

[
Accuracy < x
]

system:

* czyści wyniki treningowe,
* wyświetla komunikat o błędach,
* powraca do instrukcji treningowej.

#### Warunek spełniony

Jeżeli:


Accuracy > x


uczestnik przechodzi do fazy głównej.

### Etap 4: Instrukcja fazy głównej

Komunikat:

> „Trening zakończony sukcesem. Rozpoczynamy fazę główną. Odpowiadaj jak najszybciej i najdokładniej.”

### Etap 5: Eksperyment właściwy

* Uruchomienie bloku głównego prób (funkcja `run_block`).
* Pseudorandomizacja prób zapobiegająca powtórzeniom pod rząd (funkcja `shuffle_trials`).
* Zbieranie pełnych logów i RT.

### Etap 6: Ekran końcowy i zapis danych

* Podziękowanie za udział.
* Zapis wyników do pliku.
* Zamknięcie okna.
* Zwolnienie zasobów systemowych.
* Wywołanie `core.quit()`.

---

## 6. Architektura kodu źródłowego (Podejście Proceduralne)

Zgodnie z wymaganiami projekt zaimplementowano w sposób całkowicie proceduralny (bez stosowania klas i programowania obiektowego OOP). Kod jest podzielony na czytelne moduły:

### `main.py`

Główny punkt wejścia. Orkiestruje przebieg całego eksperymentu wywołując po kolei niezbędne kroki: zebranie danych przez dialog, inicjalizację okna, wyświetlanie ekranów instrukcji, pętle treningowe z kontrolą progu poprawności i eksperyment właściwy, a na koniec zapis wyników do CSV.

### `utils.py`

Zawiera czyste funkcje narzędziowe, które nie sterują przebiegiem eksperymentu, m.in.:

* `load_config` – parsowanie i walidacja pliku konfiguracyjnego YAML.
* `setup_logging` – inicjalizacja logowania z PsychoPy i konfigurowanie zapisów do plików log.
* `get_subject_data` – zbieranie wieku i płci przez okno dialogowe GUI, weryfikowanie wejścia z automatycznym generowaniem unikalnego ID (`SUB_YYYYMMDD_...`) dla każdego badanego.
* `load_trials` – ładowanie i walidacja obecności kolumn dla bodźców wejściowych z CSV.
* `save_results` – bezpieczny zapis zebranych wyników (wszystkich prób) do plików CSV.

### `procedures.py`

Odpowiada za logikę wizualną i obsługę samych zadań w oknie PsychoPy:

* `show_screen` – wyświetlanie statycznych ekranów tekstowych (np. powitalnego, instrukcji) z obsługą wyjścia.
* `run_trial` – złożona funkcja wykonująca dokładnie jedną, pełną próbę pomiarową (ISI -> Fixation -> Bodziec z czyszczeniem bufora -> Oczekiwanie na reakcję -> Ewaluacja -> Ewentualny Feedback).
* `run_block` – pętla iterująca po wielu próbach w danym etapie eksperymentu (trening/faza główna).
* `shuffle_trials` – autorska logika pseudorandomizacji w ramach której blokowany jest przypadek pojawienia się dwóch identycznych konfiguracji (to samo słowo i ten sam kolor) jedna po drugiej.

Wszystkie procedury powiązane z wyświetlaniem i pobieraniem klawiszy w sposób ciągły (np. nawet podczas czasów ISI) monitorują klawisz wyjścia awaryjnego (ESC). Gwarantuje to możliwość natychmiastowego przerwania aplikacji, z automatycznym zapisem zebranych do tej pory danych (Escape Hatch).

---

## 7. Wymagania techniczne i struktura danych wynikowych

### Struktura plików wejściowych (`Stimulus CSV`)

Każdy plik triali musi zawierać kolumny:

| Kolumna      | Opis                          |
| ------------ | ----------------------------- |
| `word`       | Wyświetlane słowo             |
| `color`      | Kolor bodźca                  |
| `congruency` | Typ warunku eksperymentalnego |
| `corr_ans`   | Poprawna odpowiedź            |

### Struktura plików wynikowych (`Results CSV`)

Format:

```text
results/ID_Stroop_YYYYMMDD_HHMM.csv
```

Kolumny danych:

| Kolumna        | Opis                              |
| -------------- | --------------------------------- |
| `subject_id`   | ID badanego                       |
| `age`          | Wiek                              |
| `gender`       | Płeć                              |
| `block`        | Faza eksperymentu                 |
| `trial_idx`    | Numer próby                       |
| `word`         | Wyświetlane słowo                 |
| `color`        | Kolor bodźca                      |
| `congruency`   | Typ konfliktu                     |
| `expected_key` | Poprawny klawisz                  |
| `pressed_key`  | Klawisz naciśnięty przez badanego |
| `is_correct`   | 1 = poprawnie, 0 = błędnie        |
| `rt`           | Czas reakcji                      |
| `timestamp`    | Timestamp wykonania próby         |

---

## 8. Dobre praktyki i bezpieczeństwo

### Globalny klawisz awaryjny (Escape Hatch)

System musi stale nasłuchiwać klawisza `ESC`.

Naciśnięcie:

* zapisuje dotychczasowe wyniki,
* bezpiecznie zamyka aplikację,
* kończy proces eksperymentu.

### Optymalizacja bufora klawiatury

Przed prezentacją bodźca należy:

```python
event.clearEvents()
```

Pozwala to uniknąć fałszywie krótkich czasów reakcji.

### Logowanie systemowe

Wszystkie operacje powinny być rejestrowane przy użyciu:

```python
logging.LogFile()
```

Rejestrowane informacje:

* błędy,
* czasy odświeżania,
* inicjalizacja modułów,
* ostrzeżenia sprzętowe,
* informacje diagnostyczne.

---

## 9. Szybki start (Quick Start)

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
2. Ekran powitalny — naciśnij **SPACJĘ** aby kontynuować.
3. Instrukcja treningowa → faza treningowa (z feedbackiem).
4. Jeśli dokładność ≥ 80% → przejście do fazy głównej.
5. Faza główna (bez feedbacku).
6. Ekran końcowy — wyniki zapisane w katalogu `results/`.

### Klawisze

| Klawisz | Akcja |
|---------|-------|
| ← (lewo) | Czerwony |
| ↓ (dół) | Zielony |
| → (prawo) | Niebieski |
| SPACJA | Kontynuuj |
| ESC | Przerwij eksperyment (dane zostaną zapisane) |

### Wyniki

Plik CSV w formacie `results/{ID}_Stroop_YYYYMMDD_HHMM.csv` z kolumnami:

```
subject_id, age, gender, block, trial_idx, word, color,
congruency, expected_key, pressed_key, is_correct, rt, timestamp
```

### Konfiguracja

Wszystkie parametry eksperymentu (czasy, kolory, progi, klawisze) można modyfikować w pliku `src/config.yaml` bez zmian w kodzie.
