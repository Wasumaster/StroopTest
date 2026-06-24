"""
Moduł narzędziowy: wczytywanie plików, zapisywanie wyników i obsługa okienka GUI.
Wszystkie funkcje tutaj są "czyste" - nie wpływają na wyświetlanie bodźców,
zajmują się tylko obsługą danych, aby nie zaśmiecać głównego skryptu.
"""

import os
import csv
import yaml
from datetime import datetime
from psychopy import gui

def wczytaj_config(sciezka):
    """
    Wczytuje ustawienia z pliku YAML i zamienia je na słownik (dictionary) w Pythonie.
    Dzięki temu w kodzie odwołujemy się do ustawień np. przez config["timing"]["isi_min"].
    """
    with open(sciezka, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def pobierz_dane_badanego(nazwa_eksperymentu):
    """
    Wyświetla okienko (GUI) na początku badania. Zbieramy tylko Wiek i Płeć, 
    aby zachować pełną anonimowość uczestnika (brak imienia/nazwiska).
    """
    # Słownik definiujący pola do wypełnienia w okienku
    info = {"Wiek": "", "Płeć": ["K", "M"]}
    
    # Tworzymy systemowe okienko wykorzystując wbudowaną funkcję z biblioteki PsychoPy
    dlg = gui.DlgFromDict(dictionary=info, title=nazwa_eksperymentu)
    
    # Jeśli uczestnik wcisnął 'Anuluj' lub krzyżyk na oknie
    if not dlg.OK:
        return None
    
    # Generujemy unikalne ID uczestnika na podstawie obecnej daty i czasu (co do sekundy)
    # Zabezpiecza to przed przypadkowym nadpisaniem plików dwóch różnych badanych
    info["ID"] = "SUB_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    return info

def wczytaj_bodzce(sciezka):
    """
    Wczytuje listę triali z pliku CSV.
    Używamy DictReader, dzięki czemu każdy wiersz staje się słownikiem,
    co pozwala nam odpytywać zmienne po nagłówkach, np. trial["word"].
    """
    with open(sciezka, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def zapisz_wyniki(dane, katalog_wynikow, id_badanego):
    """
    Zapisuje zebrane wyniki (listę słowników) do pliku CSV.
    Wywoływana tylko raz na samym końcu programu.
    """
    # Jeśli folder 'results' jeszcze nie istnieje, tworzymy go
    if not os.path.exists(katalog_wynikow):
        os.makedirs(katalog_wynikow)
        
    # Konstruujemy docelową nazwę pliku
    nazwa_pliku = f"{id_badanego}_Stroop.csv"
    pelna_sciezka = os.path.join(katalog_wynikow, nazwa_pliku)
    
    # Dynamicznie pobieramy nagłówki kolumn z kluczy pierwszego elementu na liście wyników
    # Dzięki temu, jeśli dodamy nową zmienną w procedurze, sama dopisze się do pliku CSV
    naglowki = list(dane[0].keys())
    
    # Zapis do pliku - newline="" zapobiega tworzeniu pustych wierszy w Windowsie
    with open(pelna_sciezka, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=naglowki)
        writer.writeheader()  # Najpierw zapisz wiersz z nazwami kolumn
        for wiersz in dane:
            writer.writerow(wiersz) # Zapisz każdy poszczególny trial
            
    print(f"Pomyślnie zapisano plik z wynikami: {pelna_sciezka}")