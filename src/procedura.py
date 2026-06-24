"""
Moduł procedur: logika pojedynczych prób (triali), tasowanie i rysowanie na ekranie.
To tutaj dzieje się cała psychofizyka z wykorzystaniem zegarów PsychoPy.
"""

import random
from datetime import datetime
from psychopy import core, event, visual

# PsychoPy definiuje kolory inaczej niż standardowo (nie w skali od 0 do 255).
# Wykorzystuje przestrzeń RGB w przedziale od -1.0 do 1.0.
COLOR_MAP = {
    "red": [1.0, -1.0, -1.0],
    "green": [-1.0, 0.6, -1.0],  # Zielony jest lekko stonowany dla czytelności
    "blue": [-1.0, -1.0, 1.0],
}

def sprawdz_sekwencje(triale):
    """
    Zabezpieczenie przed tzw. torowaniem leksykalnym (lexical priming).
    Sprawdza, czy w wygenerowanej liście to samo słowo (np. CZERWONY) 
    nie występuje w dwóch próbach z rzędu.
    """
    for i in range(len(triale) - 1):
        if triale[i]["word"] == triale[i + 1]["word"]:
            return False # Znaleziono powtórzenie! Sekwencja jest zła.
    return True # Sekwencja jest "czysta"

def przetasuj_triale(triale):
    """
    Inteligentne tasowanie z GWARANCJĄ 100% braku powtórzeń.
    Buduje listę krok po kroku, wybierając tylko dozwolone bodźce.
    """
    
    # --- KROK 1: Zabezpieczenie matematyczne (Zasada Szufladkowa) ---
    # Jeśli np. na 10 prób wpiszesz w CSV aż 6 razy słowo "CZERWONY", 
    # to fizycznie NIE DA SIĘ ułożyć tego bez powtórzeń. 
    zliczenia = {}
    for t in triale:
        zliczenia[t["word"]] = zliczenia.get(t["word"], 0) + 1
        
    najczestsze_slowo = max(zliczenia, key=zliczenia.get)
    ile_razy = zliczenia[najczestsze_slowo]
    limit_matematyczny = (len(triale) + 1) // 2
    
    if ile_razy > limit_matematyczny:
        raise ValueError(
            f"BŁĄD PLIKU CSV: Słowo '{najczestsze_slowo}' występuje aż {ile_razy} razy "
            f"na {len(triale)} całkowitych prób. To matematycznie niemożliwe, "
            f"aby ułożyć z tego sekwencję bez powtórzeń. Zmień proporcje w pliku Excel/CSV!"
        )

    # --- KROK 2: Inteligentne budowanie sekwencji ---
    while True:
        pula = list(triale) # Kopia wszystkich naszych prób (nasz "kapelusz" z losami)
        wynik = []
        ostatnie_slowo = None
        
        while pula:
            # odfiltrowujemy z puli to słowo, które było przed chwilą!
            dozwolone = [t for t in pula if t["word"] != ostatnie_slowo]
            
            if not dozwolone:
                # Ślepy zaułek! W puli zostały nam np. 2 słowa "ZIELONY", a ostatnie słowo
                # to też "ZIELONY". Przerywamy tę małą pętlę i zaczynamy losowanie od nowa.
                break 
                
            # Wyciągamy z kapelusza BEZPIECZNY, losowy trial
            wybrany = random.choice(dozwolone)
            wynik.append(wybrany)
            pula.remove(wybrany) # Wyrzucamy wykorzystany los z kapelusza
            ostatnie_slowo = wybrany["word"] # Zapamiętujemy, co wyciągnęliśmy
            
        # Jeśli lista wynikowa jest tak samo długa jak lista z CSV,
        # oznacza to, że dobrnęliśmy do końca bez ani jednego błędu!
        if len(wynik) == len(triale):
            return wynik

def sprawdz_wyjscie(wcisniete_klawisze, okno):
    """
    Sprawdza, czy na przekazanej liście klawiszy znajduje się 'escape'.
    Wywoływane wszędzie tam, gdzie czekamy na reakcję użytkownika.
    """
    if wcisniete_klawisze and "escape" in wcisniete_klawisze:
        # Zatrzymujemy natychmiast logikę PsychoPy
        okno.close()
        core.quit()

def pokaz_ekran_tekstowy(okno, tekst, config, klawisz_dalej="space"):
    """
    Pomocnicza funkcja do wyświetlania komunikatów na czarnym tle 
    (np. powiadomienie o przerwaniu eksperymentu lub końcu).
    """
    stim = visual.TextStim(
        okno, text=tekst, color=config["gui"]["text_color"], 
        font=config["gui"]["font_name"], height=0.04, units="norm"
    )
    stim.draw() # Rysuje obiekt w buforze pamięci karty graficznej
    okno.flip() # "Przerzuca" zawartość bufora na fizyczny ekran monitora
    
    wcisniete = event.waitKeys(keyList=[klawisz_dalej, "escape"])
    sprawdz_wyjscie(wcisniete, okno)

def pokaz_obrazek(okno, sciezka_obrazka, klawisz_dalej="space"):
    """
    Pomocnicza funkcja do pokazywania gotowych plików graficznych (instrukcji).
    """
    obrazek = visual.ImageStim(okno, image=sciezka_obrazka, size=(2, 2), units="norm")
    obrazek.draw()
    okno.flip()
    
    wcisniete = event.waitKeys(keyList=[klawisz_dalej, "escape"])
    sprawdz_wyjscie(wcisniete, okno)

def wykonaj_trial(okno, trial_data, config, czy_trening):
    """
    Najważniejsza funkcja eksperymentu. Oś czasu pojedynczej próby (Triala).
    Przeprowadza badanego przez sekwencję: ISI -> Fiksacja -> Bodziec -> Odpowiedź.
    """
    timing = config["timing"]
    
    # 1. ISI (Inter-Stimulus Interval)
    # Odwracamy uwagę badanego - pusty ekran przez losowy ułamek sekundy.
    # Utrudnia to przewidzenie dokładnego momentu pojawienia się bodźca.
    okno.flip() 
    core.wait(random.uniform(timing["isi_min"], timing["isi_max"]))
    
    # 2. Krzyżyk fiksacyjny
    # Ustanawia centralny punkt na ekranie, by badany skupił wzrok w jednym miejscu.
    fiksacja = visual.TextStim(
        okno, text="+", color=config["gui"]["text_color"], 
        units="pix", height=config["gui"]["font_size"]
    )
    fiksacja.draw()
    okno.flip()
    core.wait(timing["fixation_cross"])
    
    # 3. Przygotowanie słowa (bodźca)
    slowo = trial_data["word"]
    kolor_nazwa = trial_data["color"]
    poprawna_odp = trial_data["corr_ans"]
    kolor_rgb = COLOR_MAP.get(kolor_nazwa, config["gui"]["text_color"])
    
    bodziec = visual.TextStim(
        okno, text=slowo, color=kolor_rgb, font=config["gui"]["font_name"], 
        units="pix", height=config["gui"]["font_size"], bold=True
    )
    
    # BARDZO WAŻNE KROKI:
    # Czyścimy bufor klawiatury tuż przed wyświetleniem słowa.
    # Zapobiega to sytuacji, gdzie badany wciska klawisz jeszcze w trakcie fiksacji,
    # a program zalicza to błędnie jako "superszybką" reakcję (np. czas 0.01s).
    event.clearEvents()  
    
    bodziec.draw()
    okno.flip() # Rysujemy słowo na ekran
    
    # Tworzymy "stoper" dokładnie w chwili wyświetlenia bodźca na ekranie.
    zegar_rt = core.Clock()
    
    # 4. Nasłuchiwanie odpowiedzi uczestnika
    dozwolone_klawisze = list(config["keys"]["response_mapping"].keys()) + ["escape"]
    
    # Funkcja waitKeys z argumentem timeStamped oddaje nam listę wcisnietych
    # klawiszy oraz DOKŁADNY czas ze stopera (zegar_rt), w którym to nastąpiło.
    reakcja = event.waitKeys(
        maxWait=timing["stimulus_timeout"], 
        keyList=dozwolone_klawisze, 
        timeStamped=zegar_rt
    )
    
    # Zmienne domyślne, jeśli badany np. nie zdąży wcisnąć klawisza (timeout)
    wcisniety_klawisz = None
    rt = "NA"
    czy_poprawnie = 0
    
    if reakcja:
        # Reakcja zwraca tuplet np: ('left', 0.5432)
        wcisniety_klawisz = reakcja[0][0]
        rt = round(reakcja[0][1], 4) # Zaokrąglamy ułamek sekundy do 4 miejsc
        
        sprawdz_wyjscie([wcisniety_klawisz], okno) # Sprawdzamy czy nie wcisnął ESC
        
        # Oceniamy, czy wciśnięto przycisk wymagany dla koloru czcionki
        if wcisniety_klawisz == poprawna_odp:
            czy_poprawnie = 1
            
    # 5. Ewentualny feedback (włącza się tylko w fazie treningowej dla ułatwienia nauki)
    if czy_trening and czy_poprawnie == 0:
        tekst_feedbacku = config["messages"]["error_feedback"]
        if not wcisniety_klawisz:
            tekst_feedbacku = config["messages"]["timeout_feedback"]
            
        feedback = visual.TextStim(
            okno, text=tekst_feedbacku, color=[1.0, -0.2, -0.2],  # Kolor czerwony komunikatu
            units="pix", height=config["gui"]["font_size"], bold=True
        )
        feedback.draw()
        okno.flip()
        core.wait(timing["feedback_duration"])
        
    # Zwrócenie słownika ze wszystkimi detalami z pojedynczej próby
    return {
        "word": slowo,
        "color": kolor_nazwa,
        "congruency": trial_data["congruency"],
        "expected_key": poprawna_odp,
        "pressed_key": wcisniety_klawisz if wcisniety_klawisz else "brak",
        "is_correct": czy_poprawnie,
        "rt": rt,
        "timestamp": datetime.now().isoformat()
    }