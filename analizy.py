import pandas as pd
import streamlit as st
import statsmodels.api as sm
import ustawienia
import funkcje_pomocnicze

def metoda3_plik_wydajnosc(sciezka_cennik, sciezka_czas_pracy, imie):
    """
    Analizuje wydajność pracownika na podstawie plików cenników i czasu pracy.

    Parametry:
    - sciezka_cennik (str): ścieżka do pliku Excel z wartościami cennikowymi przypisanymi do modeli (kolumny: 'dzien', 'model', 'cennik')
    - sciezka_czas_pracy (str): ścieżka do pliku Excel z rzeczywistym czasem pracy pracownika (kolumny: 'dzien', 'czas_pracy')
    - imie (str): imię pracownika (do wyświetlenia w aplikacji)

    Wyniki:
    - Wyświetla tabelę przefiltrowanych danych
    - Pokazuje wyniki regresji OLS (efektywność + przedziały ufności dla istotnych zmiennych)
    """
    st.write(f"Analiza dotycząca: {imie}")
    try:
        df_cennik = funkcje_pomocnicze.zaladuj_dane(sciezka_czas_pracy)
        df_czas_pracy = funkcje_pomocnicze.zaladuj_dane(sciezka_cennik)
    except FileNotFoundError as e:
        st.error(f"Nie znaleziono pliku: {e.filename}")
        return
    except ValueError as e:
        st.error(f"Nieprawidłowy format pliku: {e}")
        return
    except Exception as e:
        st.error(f"Wystąpił błąd przy wczytywaniu danych: {e}")
        return
    df_cennik['model'] = df_cennik['model'].replace(ustawienia.model_skrot_mapping)
    df_pivot = df_cennik.pivot_table(index='dzien', columns='model', values='cennik', aggfunc='sum', fill_value=0)

    # Połączenie z czasem_realnym
    df_all = df_czas_pracy.merge(df_pivot, on='dzien', how='left').set_index('dzien')
    df_all = df_all.dropna(subset=['czas_pracy'])
    df_all = df_all[df_all['czas_pracy'] != 0]
    df_all = df_all[~df_all.drop(columns='czas_pracy').isna().all(axis=1)]
    data_od_ktorej_odejmowano_35_minut = pd.to_datetime('2025-01-17')
    df_all.loc[df_all.index < data_od_ktorej_odejmowano_35_minut, 'czas_pracy'] -= 35
    

    # Wyliczenie dziennej efektywności
    df_efektywnosc_dzienna = df_all.copy()

    # Suma wartości cennikowych ze wszystkich modeli
    df_efektywnosc_dzienna['cennik_suma'] = df_efektywnosc_dzienna.drop(columns='czas_pracy').sum(axis=1)

    # Kolumny końcowe
    df_efektywnosc_dzienna = df_efektywnosc_dzienna[['czas_pracy', 'cennik_suma']]
    df_efektywnosc_dzienna['efektywnosc_%'] = (df_efektywnosc_dzienna['cennik_suma'] / df_efektywnosc_dzienna['czas_pracy'] * 100).round(1)

    # Sortowanie od najniższej efektywności
    df_efektywnosc_dzienna = df_efektywnosc_dzienna.sort_values('efektywnosc_%')

    st.dataframe(df_efektywnosc_dzienna)

    liczba_dni_przed = len(df_all)
    efektywnosc = df_all.drop(columns='czas_pracy').sum(axis=1) / df_all['czas_pracy'] * 100
    df_all = df_all[(efektywnosc >= 100) & (efektywnosc <= 200)]
    
    # Po filtrowaniu
    liczba_dni_po = len(df_all)
    liczba_usunietych = liczba_dni_przed - liczba_dni_po
    procent_usunietych = round(liczba_usunietych / liczba_dni_przed * 100, 1) if liczba_dni_przed > 0 else 0

    # Wyświetlenie informacji
    st.info(f"Usunięto {liczba_usunietych} dni z {liczba_dni_przed} ({procent_usunietych}% danych) ze względu na efektywność poza zakresem 100–200%.")
        
    
    # Przygotowanie do regresji MNK
    X = df_all.drop(columns='czas_pracy')
    y = df_all['czas_pracy']

    st.write(df_all)

    # Regresja OLS (MNK)
    model = sm.OLS(y, X).fit()

    # Wyniki regresji
    conf = model.conf_int()
    conf.columns = ['ci_lower', 'ci_upper']
    p_values = model.pvalues

    # Minimalna wartość bezpieczna do dzielenia (by nie dzielić przez 0)
    MIN_ABS = 1e-3

    # Maska: tylko istotne zmienne i bezpieczne przedziały
    significant = p_values < 0.05
    valid_ci = (conf['ci_lower'].abs() > MIN_ABS) & (conf['ci_upper'].abs() > MIN_ABS)

    # Filtrowanie indeksów, które spełniają oba warunki
    valid_idx = significant & valid_ci

    # Tworzenie ramki wyników tylko dla istotnych i bezpiecznych zmiennych
    wyniki = pd.DataFrame({
        'model': model.params[valid_idx].index,
        'coef': model.params[valid_idx].values,
        'p_value': p_values[valid_idx].round(2).values,
        'efektywnosc_%': (1 / model.params[valid_idx].values * 100).round(1),
        'efektywnosc_ci_lower_%': (1 / conf.loc[valid_idx, 'ci_upper'] * 100).round(1),
        'efektywnosc_ci_upper_%': (1 / conf.loc[valid_idx, 'ci_lower'] * 100).round(1)
    })

    # Opcjonalnie: sortowanie
    wyniki = wyniki.sort_values('efektywnosc_%')

    # Wyświetlenie
    st.dataframe(wyniki)