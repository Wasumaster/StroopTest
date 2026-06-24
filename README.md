# Specyfikacja Projektu: Implementacja Testu Stroopa w PsychoPy

## 1. Wprowadzenie teoretyczne i cele projektu

Projekt zakłada stworzenie narzędzia do przeprowadzania Zadania Stroopa (Stroop Task) przy użyciu biblioteki PsychoPy. Efekt Stroopa jest jednym z najbardziej znanych fenomenów w psychologii poznawczej i kognitywistyce, ilustrującym mechanizmy kontroli poznawczej, uwagi selektywnej, rozwiązywania konfliktów (tzw. konflikt inkongruencji) oraz automatyzmu procesów czytania.

### Cel główny

Celem oprogramowania jest precyzyjny pomiar czasu reakcji (**RT – Reaction Time**) oraz poprawności odpowiedzi uczestnika w warunkach:

- **Kongruentnych (zgodnych)** – kolor czcionki i znaczenie słowa są identyczne (np. słowo „CZERWONY” napisane czerwoną czcionką).
- **Inkongruentnych (niezgodnych)** – kolor czcionki różni się od znaczenia słowa (np. słowo „ZIELONY” napisane niebieską czcionką).
- **Neutralnych** – słowa niezwiązane z kolorami (np. „malina”, „rakieta”) wydrukowane w jednym z trzech kolorów czcionki.

Aplikacja została zaprojektowana modułowo i zoptymalizowana pod kątem czytelności. Pozwala to na łatwą replikację badania, modyfikację parametrów bez ingerencji w kod źródłowy Pythona oraz zachowanie przejrzystości struktury dla innych badaczy.

---

## 2. Architektura i struktura plików

Struktura repozytorium rygorystycznie rozdziela logikę, konfigurację, zasoby graficzne oraz wyniki.

```text
/
├── instructions/                # Graficzne ekrany instrukcji (pliki JPG)
├── stimulus/                    # Pliki wejściowe definiujące warunki eksperymentalne
│   ├── training_trials.csv      # Lista bodźców dla fazy treningowej
│   └── main_trials.csv          # Pełna lista bodźców dla fazy głównej
├── results/                     # Wyniki badań w formacie CSV (generowane automatycznie)
├── src/                         # Kod źródłowy aplikacji
│   ├── main.py                  # Punkt wejścia i liniowa oś czasu przebiegu eksperymentu
│   ├── config.yaml              # Globalny plik konfiguracyjny (parametryzacja)
│   ├── procedura.py             # Procedury eksperymentalne, logika prób i wyświetlania
│   └── utils.py                 # Funkcje pomocnicze (wczytywanie i zapis danych)
├── requirements.txt             # Zależności systemowe (pip)
└── README.md                    # Dokumentacja i instrukcja uruchomienia
```

---

## 3. Parametryzacja środowiska – `config.yaml`

Cała logika dotycząca wyglądu i przebiegu eksperymentu jest wyabstrahowana do zewnętrznego pliku konfiguracyjnego `config.yaml`.

Pozwala to na elastyczną zmianę parametrów środowiskowych (czasy, kolory, progi dokładności, klawisze) bez konieczności modyfikowania kodu źródłowego.

Przykładowe parametry:

```yaml
window:
  fullscreen: true
  background_color: [0, 0, 0]

timing:
  fixation_duration: 0.5
  isi_min: 0.5
  isi_max: 1.5
  stimulus_timeout: 3.0

training:
  min_accuracy: 0.80

keys:
  red: left
  green: down
  blue: right
  next: space
  quit: escape
```


---

## 4. Oś czasu pojedynczej próby (Trial Timeline)

Precyzja pomiaru w PsychoPy jest kluczowa. Oś czasu zsynchronizowana jest z odświeżaniem monitora.

Każda próba realizuje następujący cykl:

### 1. Jittered ISI (Inter-Stimulus Interval)

- Pusty ekran wyświetlany przez losowy czas między `isi_min` a `isi_max`.
- Zapobiega habituacji oraz antycypowaniu bodźca.

### 2. Fixation Cross

- Znak `+` wyświetlany centralnie przez 500 ms.
- Koncentruje uwagę przestrzenną uczestnika.

### 3. Prezentacja Bodźca (Stimulus Onset)

Bezpośrednio przed prezentacją bodźca wykonywane są:

- Reset zegara `core.Clock()`.
- Czyszczenie bufora zdarzeń:

```python
event.clearEvents()
```

Zapobiega to rejestracji przypadkowych naciśnięć z poprzedniej próby.

### 4. Nasłuch i Reakcja

Program oczekuje na odpowiedź uczestnika przy użyciu klawiszy strzałek.

Oczekiwanie trwa do:

- udzielenia odpowiedzi,
- przekroczenia limitu czasu (`stimulus_timeout`).

### 5. Ewaluacja i Zapis

Dla każdej próby zapisywane są:

- odpowiedź uczestnika,
- poprawność odpowiedzi,
- czas reakcji z dokładnością do 4 miejsc po przecinku.

Przykład:

```text
0.4502 s
```

### 6. Feedback (wyłącznie trening)

Jeżeli odpowiedź jest błędna lub nie zostanie udzielona:

- wyświetlany jest czerwony komunikat zwrotny.

W fazie głównej feedback jest całkowicie wyłączony.

---

## 5. Przebieg procedury eksperymentalnej

Eksperyment realizowany jest liniowo zgodnie ze strukturą `main.py`.

### 1. Inicjalizacja

Wyświetlane jest okno dialogowe zbierające:

- wiek,
- płeć.

Dodatkowo generowany jest unikalny identyfikator uczestnika.

### 2. Instrukcje

Wyświetlana jest sekwencja grafik JPG znajdujących się w katalogu:

```text
instructions/
```

### 3. Pętla treningowa

Krótki blok treningowy zawierający feedback.

Po zakończeniu obliczana jest dokładność:

```text
Accuracy = liczba poprawnych odpowiedzi / liczba wszystkich prób
```

Jeżeli wynik jest poniżej progu (domyślnie 80%), uczestnik musi powtórzyć trening.

### 4. Faza główna

Właściwy pomiar eksperymentalny.

Cechy:

- brak feedbacku,
- zapis wszystkich prób,
- pomiar RT.

### 5. Zapis i zakończenie

Po zakończeniu:

- wszystkie dane zostają zapisane do pliku CSV,
- zamykane jest okno PsychoPy.

---

## 6. Mechanizm pseudorandomizacji bodźców

Funkcja:

```python
przetasuj_triale()
```

zapewnia, że identyczne słowo nie pojawi się w dwóch kolejnych próbach.

Przykład niedozwolonej sekwencji:

```text
CZERWONY (red)
CZERWONY (blue)
```

Mogłoby to powodować efekt torowania leksykalnego (*lexical priming*), który sztucznie obniża czas reakcji.

### Algorytm

1. Losowe tasowanie listy prób.
2. Sprawdzenie poprawności sekwencji.
3. Powtórzenie procesu do 1000 razy.
4. Akceptacja pierwszego poprawnego układu.

Podejście typu brute-force gwarantuje prostotę i wysoką skuteczność.

---

## 7. Architektura kodu źródłowego

### `main.py`

Punkt wejścia programu.

Odpowiedzialności:

- inicjalizacja eksperymentu,
- tworzenie okna PsychoPy,
- przełączanie pomiędzy blokami,
- obsługa bezpiecznego zamykania.

### `utils.py`

Warstwa infrastrukturalna.

Zawiera:

- wczytywanie YAML,
- odczyt CSV,
- zapis wyników,
- okna dialogowe GUI.

### `procedura.py`

Warstwa logiki eksperymentalnej.

Zawiera:

- prezentację instrukcji,
- procedurę pojedynczej próby,
- algorytmy losowania,
- prezentację bodźców,
- obsługę feedbacku.

---

## 8. Wymagania techniczne i struktura danych wynikowych

### Nazwa pliku wynikowego

```text
results/{ID}_Stroop.csv
```

Przykład:

```text
results/P023_Stroop.csv
```

### Kolumny danych

```text
subject_id
age
gender
block
trial_idx
word
color
congruency
expected_key
pressed_key
is_correct
rt
timestamp
```

Opis:

| Kolumna | Opis |
|----------|----------|
| subject_id | Identyfikator uczestnika |
| age | Wiek |
| gender | Płeć |
| block | training / main |
| trial_idx | Numer próby |
| word | Wyświetlone słowo |
| color | Kolor czcionki |
| congruency | congruent / incongruent / neutral |
| expected_key | Poprawny klawisz |
| pressed_key | Wciśnięty klawisz |
| is_correct | 0/1 |
| rt | Czas reakcji |
| timestamp | Znacznik czasu |

---

## 9. Dobre praktyki i bezpieczeństwo badawcze

### Zapis awaryjny — klawisz ESC (Escape Hatch)

W module `main.py` zastosowano konstrukcję:

```python
try:
    ...
finally:
    save_results(...)
```

Naciśnięcie klawisza **ESC** w dowolnym momencie:

- natychmiast przerywa eksperyment,
- zamyka okno graficzne,
- zapisuje wszystkie dotychczas zebrane dane.

Dzięki temu nawet nieukończona sesja może zostać wykorzystana w analizach.

### Niezależność ścieżek

Wszystkie ścieżki budowane są względem lokalizacji pliku wykonywalnego.

Przykład:

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```

Zapobiega to błędom:

```text
FileNotFoundError
```

oraz umożliwia uruchamianie programu z różnych środowisk IDE i terminali.

---

## 10. Szybki start (Quick Start)

### Wymagania

- Python 3.10 lub 3.11
- PsychoPy

> PsychoPy nie wspiera w pełni najnowszych wersji Pythona.

### 1. Utworzenie środowiska wirtualnego

```bash
py -3.11 -m venv .venv
```

### 2. Aktywacja środowiska

Windows:

```bash
.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 4. Uruchomienie eksperymentu

```bash
python src/main.py
```

---

## Klawisze sterujące

| Klawisz | Funkcja |
|----------|----------|
| ← | Czerwony |
| ↓ | Zielony |
| → | Niebieski |
| SPACJA | Następny ekran instrukcji |
| ESC | Natychmiastowe zakończenie z automatycznym zapisem |

---

## 11. Literatura naukowa

Stroop, J. R. (1935). *Studies of interference in serial verbal reactions*. Journal of Experimental Psychology, 18(6), 643–662.

MacLeod, C. M. (1991). *Half a century of research on the Stroop effect: An integrative review*. Psychological Bulletin, 109(2), 163–203.

Peirce, J. W., Gray, J. R., Simpson, S., MacAskill, M. R., Höchenberger, R., Sogo, H., Kastman, E., & Lindeløv, J. K. (2019). *PsychoPy2: Experiments in behavior made easy*. Behavior Research Methods, 51(1), 195–203.