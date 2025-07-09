import re
import ustawienia
import pandas as pd
import numpy as np
import streamlit as st
from datetime import date, timedelta

def dodaj_model(artykul_nazwa):
    for model in ustawienia.analizowane_modele:
        if model in artykul_nazwa:
            return model
    return 'brak_modelu'

def dodaj_bryla(artykul_nazwa):
    pattern = r'\b(?:' + '|'.join(map(re.escape, ustawienia.analizowane_modele)) + r')\b'
    return re.sub(pattern, '', artykul_nazwa).strip()

def modyfikuj_bryla(bryla):
    if bryla and bryla[0] != '[' and bryla[-1] == ']':
        bryla = '[' + bryla[:-1]
    if bryla.startswith('PD') or bryla.startswith('PO'):
        return "poduszka"
    if bryla.endswith(" - STELAŻ NA BIAŁO"):
        bryla = bryla[:-len(" - STELAŻ NA BIAŁO")]
    return bryla

def dodaj_id_komisji(df):
    id_komisji = 1 
    df = df.reset_index(drop=True)
    df['id_komisji'] = 0
    df['ilosc_bryl_w_komisji'] = 0  
    df['time_diff'] = pd.Timedelta(0)

    time_diff = pd.Timedelta(0)
    time_diff_seconds = 0
    ilosc_bryl_w_komisji = 0

    for index, row in df.iterrows():
        if index > 0:
            time_diff = row['Start']- df.at[index - 1, 'Start']
            df.at[index, 'time_diff'] = time_diff  
            
            time_diff_seconds = time_diff.total_seconds()
            df.at[index, 'time_diff_seconds'] = time_diff_seconds

            if time_diff_seconds > 120 or row['Nazwisko'] != df.at[index - 1, 'Nazwisko']:
                ilosc_bryl_w_komisji = 0
                id_komisji += 1
            
        ilosc_bryl_w_komisji+=1

        df.at[index, 'id_komisji'] = id_komisji
        df.at[index, 'ilosc_bryl_w_komisji'] = ilosc_bryl_w_komisji

    max_values = df.groupby('id_komisji')['ilosc_bryl_w_komisji'].transform('max')
    df['ilosc_bryl_w_komisji'] = max_values

    df['id_komisji'] = df['id_komisji'].astype(int)
    agg_result = df.groupby('id_komisji')['model_bryla'].apply(list)
    sorted_agg_result = agg_result.apply(lambda x: sorted(x, key=str))
    df['komisja'] = df['id_komisji'].map(sorted_agg_result)
    df['komisja'] = df['komisja'].apply(lambda x: '\n'.join(map(str, x)) if all(isinstance(item, str) for item in x) else '')

    return df

def polacz_dane_w_komisje(df):
    unique_id_komisji = df['id_komisji'].unique()
    df_final = pd.DataFrame({'id_komisji': unique_id_komisji})
    grouped = df.groupby('id_komisji')

    ### SUMA CZASU CENNIKOWEGO
    sum_czas_cennikowy = grouped['czas_cennik'].sum().reset_index()
    df_final = pd.merge(df_final, sum_czas_cennikowy, on='id_komisji')

    ### ŚREDNI CZAS
    mean_czas = grouped['Czas'].mean().reset_index()
    df_final = pd.merge(df_final, mean_czas, on='id_komisji')


    ### LICZBA BRYŁ W RAMACH KOMISJI
    count_id_komisji = df['id_komisji'].value_counts().reset_index()
    count_id_komisji.columns = ['id_komisji', 'ilosc_bryl_w_komisji']
    df_final = pd.merge(df_final, count_id_komisji, on='id_komisji')

    ### NAZWISKO TAPICERA
    unique_nazwisko = grouped['Nazwisko'].unique().reset_index()
    unique_nazwisko.columns = ['id_komisji', 'nazwisko']
    df_final = pd.merge(df_final, unique_nazwisko, on='id_komisji')

    ### NAZWA WSZYSTKICH TAPICEROWANYCH BRYŁ
    all_komisja = grouped['model_bryla'].agg(lambda x: sorted(list(x))).reset_index()
    all_komisja.columns = ['id_komisji', 'model_bryla']
    df_final = pd.merge(df_final, all_komisja, on='id_komisji')
    df_final['komisja'] = df_final['model_bryla']

    all_komisja_org = grouped['Artykul nazwa'].agg(lambda x: sorted(list(x))).reset_index()
    all_komisja_org.columns = ['id_komisji', 'Artykul nazwa']
    df_final = pd.merge(df_final, all_komisja_org, on='id_komisji')
    df_final['komisja_org'] = df_final['Artykul nazwa']

    ### ILOŚĆ PODUSZEK W KOMISJI
    sum_poduszek = grouped['model_bryla'].apply(lambda x: sum(1 for elem in x if 'poduszka' in elem)).reset_index()
    sum_poduszek.columns = ['id_komisji', 'suma_poduszek']
    df_final = pd.merge(df_final, sum_poduszek, on='id_komisji')

    ### ILOŚĆ SOF NIETYPOWYCH W KOMISJI
    sum_sofy_nietypowe = grouped['model_bryla'].apply(lambda x: sum(1 for elem in x if 'SOFA NIETYPOWA' in elem)).reset_index()
    sum_sofy_nietypowe.columns = ['id_komisji', 'suma_sofy_nietypowe']
    df_final = pd.merge(df_final, sum_sofy_nietypowe, on='id_komisji')

    ### ILOŚĆ SOF NIETYPOWYCH W KOMISJI
    sum_fotele_nietypowe = grouped['model_bryla'].apply(lambda x: sum(1 for elem in x if 'FOTEL NIETYPOWY' in elem)).reset_index()
    sum_fotele_nietypowe.columns = ['id_komisji', 'suma_fotele_nietypowe']
    df_final = pd.merge(df_final, sum_fotele_nietypowe, on='id_komisji')

    ### NAZWA WSZYSTKICH TAPICEROWANYCH MODELI
    unique_model = grouped['model'].unique().reset_index()
    unique_model.columns = ['id_komisji', 'model']
    df_final = pd.merge(df_final, unique_model, on='id_komisji')

    ### KIEDY UKOŃCZONO
    unique_kiedy_ukonczono = grouped['kiedy_ukonczono'].unique().reset_index()
    unique_kiedy_ukonczono.columns = ['id_komisji', 'kiedy_ukonczono']
    df_final = pd.merge(df_final, unique_kiedy_ukonczono, on='id_komisji')

    ### MINIMALNY CZAS STARTU W RAMACH KOMISJI
    min_start = grouped['Start'].min().reset_index()
    min_start.columns = ['id_komisji', 'minimum_start']
    df_final = pd.merge(df_final, min_start, on='id_komisji')

    ### MAXYMALNY CZAS STOPU W RAMACH KOMISJI
    max_stop = grouped['Stop'].max().reset_index()
    max_stop.columns = ['id_komisji', 'maximum_stop']
    df_final = pd.merge(df_final, max_stop, on='id_komisji')

    mask_p06 = df_final['nazwisko'] == 'P06'

    # 1. Zbierz oryginalne wartości maximum_stop przed mapowaniem
    oryginalne_datetimes = set(df_final.loc[mask_p06, 'maximum_stop'].unique())

    # 2. Klucze słownika
    klucze_slownika = set(ustawienia.P06_zmiana.keys())

    # 3. Sprawdź trafienia (czyli jakie wartości z df są w kluczach słownika)
    wspolne = oryginalne_datetimes & klucze_slownika
    print("Liczba trafień w słowniku:", len(wspolne))
    print("Daty, które się zgadzają:", wspolne)

    # 4. Teraz wykonaj mapowanie
    df_final.loc[mask_p06, 'maximum_stop'] = (
        df_final.loc[mask_p06, 'maximum_stop']
        .map(ustawienia.P06_zmiana)
        .fillna(df_final.loc[mask_p06, 'maximum_stop'])
    )

    # 5. Inne debugowanie
    print(df_final['maximum_stop'].dtype)
    print(type(list(ustawienia.P06_zmiana.keys())[0]))

    ma_mikrosekundy = (df_final['maximum_stop'].dt.microsecond != 0).any()
    print("Czy kolumna 'maximum_stop' zawiera mikrosekundy różne od 0?", ma_mikrosekundy)

    df_final['czas_po_mapowaniu'] = (df_final['maximum_stop'] - df_final['minimum_start']).dt.total_seconds() / 60
    mask_mapowanie = df_final["czas_po_mapowaniu"] > 5
    mask_rozne_dni = df_final["minimum_start"].dt.date != df_final["maximum_stop"].dt.date
    df_final.loc[mask_mapowanie, "jak_liczymy"] = "różnica Start - Stop: ten sam dzień"
    df_final.loc[mask_mapowanie & mask_rozne_dni, "jak_liczymy"] = "różnica Start - Stop: różne dni" 

    def same_time_check(df):
        df['inne_komisje_tapicerowane_jednoczesnie'] = [[] for _ in range(len(df))]

        for i in range(len(df)):
            nazwisko = df.at[i, 'nazwisko']
            max_stop = df.at[i, 'maximum_stop']

            for j in range(i + 1, len(df)):
                if df.at[j, 'nazwisko'] != nazwisko:
                    break  # inna osoba

                if df.at[j, 'minimum_start'] + timedelta(minutes=2) < max_stop:
                    df.at[i, 'inne_komisje_tapicerowane_jednoczesnie'].append(j + 1)
                    df.at[j, 'inne_komisje_tapicerowane_jednoczesnie'].append(i + 1)
                else:
                    break
    same_time_check(df_final)
    
    ### CZAS POMIĘDZY KOMISJAMI
    df_final["poprzedni_stop"] = df_final["maximum_stop"].shift(1)
    mask_pierwszy_pomiar = df_final["nazwisko"] != df_final["nazwisko"].shift(1)
    df_final.loc[mask_pierwszy_pomiar, "poprzedni_stop"] = pd.NaT
    df_final.loc[mask_pierwszy_pomiar, "jak_liczymy"] = "wyłączone z analizy - pierwszy pomiar piankacza"
    df_final["czas_pomiedzy_komisjami"] = df_final["minimum_start"] - df_final["poprzedni_stop"]
    df_final["czas_pomiedzy_komisjami"] = df_final["czas_pomiedzy_komisjami"].dt.total_seconds() / 60

    ### CZY PIERWSZA KOMISJA DANEGO DNIA
    df_final["data"] = df_final["minimum_start"].dt.date
    df_final["czy_pierwsza_komisja_dnia"] = (
        (df_final["nazwisko"] != df_final["nazwisko"].shift(1)) |
        (df_final["data"] != df_final["data"].shift(1))
    )
    mask_wczesne_odbicie = (
        (df_final["czy_pierwsza_komisja_dnia"] == True) &
        (df_final["minimum_start"].dt.time < pd.to_datetime("12:00").time()) &
        (df_final["jak_liczymy"] != "różnica Start - Stop: ten sam dzień") &
        (df_final["jak_liczymy"] != "wyłączone z analizy - pierwszy pomiar piankacza")
    )
    df_final.loc[mask_wczesne_odbicie, "jak_liczymy"] = "wyłączone z analizy - pierwsze odbicie przed 12:00"

    mask_pozne_odbicie = (
        (df_final["czy_pierwsza_komisja_dnia"] == True) &
        (df_final["minimum_start"].dt.time > pd.to_datetime("12:00").time()) &
        (df_final["jak_liczymy"] != "różnica Start - Stop: ten sam dzień") &
        (df_final["jak_liczymy"] != "wyłączone z analizy - pierwszy pomiar piankacza")
    )
    df_final.loc[mask_pozne_odbicie, "jak_liczymy"] = "pierwsze odbicie po 12:00"

    mask_roznica_miedzy_komisjami = (df_final["Czas"] < 3) & (df_final["czy_pierwsza_komisja_dnia"] == False)
    df_final.loc[mask_roznica_miedzy_komisjami, "jak_liczymy"] = "różnica pomiędzy komisjami"


    ### ILOŚC PRZERW
    df_final["ilosc_przerw"] = 0

    def licz_przerwy(row):
        jak_liczymy = row["jak_liczymy"]
        start = row["minimum_start"].time()
        poprzedni_stop = row.get("poprzedni_stop", pd.NaT)
        poprzedni_stop_time = poprzedni_stop.time() if pd.notna(poprzedni_stop) else None
        maximum_stop = row["maximum_stop"].time()

        if jak_liczymy == "różnica pomiędzy komisjami":
            przerwy = 0
            if start > pd.to_datetime("10:15").time() and poprzedni_stop_time and poprzedni_stop_time < pd.to_datetime("10:00").time():
                przerwy += 1
            if start > pd.to_datetime("13:15").time() and poprzedni_stop_time and poprzedni_stop_time < pd.to_datetime("13:00").time():
                przerwy += 1
            return przerwy

        elif jak_liczymy == "pierwsze odbicie po 12:00":
            if start > pd.to_datetime("13:15").time():
                return 2
            elif pd.to_datetime("10:15").time() < start <= pd.to_datetime("13:15").time():
                return 1
            else:
                return 0

        elif jak_liczymy == "różnica Start - Stop: różne dni":
            if start < pd.to_datetime("10:00").time() and maximum_stop > pd.to_datetime("13:15").time():
                return 4
            elif pd.to_datetime("10:15").time() < start < pd.to_datetime("13:15").time() and maximum_stop > pd.to_datetime("13:15").time():
                return 3
            elif start > pd.to_datetime("13:15").time() and maximum_stop > pd.to_datetime("13:15").time():
                return 2
            elif start > pd.to_datetime("13:15").time() and pd.to_datetime("10:15").time() < maximum_stop < pd.to_datetime("13:15").time():
                return 1
            else:
                return 0
            
        elif jak_liczymy == "różnica Start - Stop: ten sam dzień":
            if start < pd.to_datetime("10:00").time() and maximum_stop > pd.to_datetime("13:15").time():
                return 2
            elif pd.to_datetime("10:15").time() < start < pd.to_datetime("13:15").time() and maximum_stop > pd.to_datetime("13:15").time():
                return 1
            elif start < pd.to_datetime("10:00").time() and pd.to_datetime("10:15").time() < maximum_stop < pd.to_datetime("13:15").time():
                return 1
            else:
                return 0

        else:
            return 0

    df_final["ilosc_przerw"] += df_final.apply(licz_przerwy, axis=1)


    ### EFEKTYWNOŚĆ
    # === RÓŻNICA POMIĘDZY KOMISJAMI ===
    mask_roznica = df_final['jak_liczymy'] == "różnica pomiędzy komisjami"

    df_final.loc[mask_roznica, 'czas_bez_przerw'] = df_final.loc[mask_roznica, 'czas_pomiedzy_komisjami']
    df_final.loc[mask_roznica, 'efektywnosc'] = (
        df_final.loc[mask_roznica, 'czas_cennik'] / df_final.loc[mask_roznica, 'czas_bez_przerw']
    )


    # === PIERWSZE ODBICIE PO 12:00 ===
    # Czas to różnica między godziną stop a 7:15 rano (bez 30 minut przerwy)
    mask_po_12 = df_final['jak_liczymy'] == "pierwsze odbicie po 12:00"

    czas_po_12 = (
        (df_final.loc[mask_po_12, 'maximum_stop'] - 
        pd.to_datetime(df_final.loc[mask_po_12, 'maximum_stop'].dt.date.astype(str) + ' 07:15'))
        .dt.total_seconds() / 60
    ) - 30  # odejmujemy 30 minut przerwy

    df_final.loc[mask_po_12, 'czas_bez_przerw'] = czas_po_12
    df_final.loc[mask_po_12, 'efektywnosc'] = (
        df_final.loc[mask_po_12, 'czas_cennik'] / df_final.loc[mask_po_12, 'czas_bez_przerw']
    )


    # === PIERWSZE ODBICIE PRZED 12:00 ===
    # Łączymy dwa okresy: 15:15 dnia poprzedniego do poprzedniego stop + maximum_stop do 7:15
    mask_przed_12 = df_final['jak_liczymy'] == "wyłączone z analizy - pierwsze odbicie przed 12:00"

    godzina_715 = pd.to_datetime(df_final.loc[mask_przed_12, 'maximum_stop'].dt.date.astype(str) + ' 07:15')
    godzina_1520 = pd.to_datetime(df_final.loc[mask_przed_12, 'poprzedni_stop'].dt.date.astype(str) + ' 15:20')

    czas_do_1520 = (godzina_1520 - df_final.loc[mask_przed_12, 'poprzedni_stop']).dt.total_seconds() / 60
    czas_od_715 = (df_final.loc[mask_przed_12, 'maximum_stop'] - godzina_715).dt.total_seconds() / 60
    czas_sumaryczny = czas_do_1520 + czas_od_715

    df_final.loc[mask_przed_12, 'czas_bez_przerw'] = czas_sumaryczny
    df_final.loc[mask_przed_12, 'efektywnosc'] = (
        df_final.loc[mask_przed_12, 'czas_cennik'] / df_final.loc[mask_przed_12, 'czas_bez_przerw']
    )


    # === RÓŻNICA START - STOP (JEDEN DZIEŃ) ===
    mask_start_stop = df_final['jak_liczymy'] == "różnica Start - Stop: ten sam dzień"

    df_final.loc[mask_start_stop, 'czas_bez_przerw'] = (
        df_final.loc[mask_start_stop, 'maximum_stop'] - df_final.loc[mask_start_stop, 'minimum_start']
    ).dt.total_seconds() / 60
    df_final.loc[mask_start_stop, 'efektywnosc'] = (
        df_final.loc[mask_start_stop, 'czas_cennik'] / df_final.loc[mask_start_stop, 'czas_bez_przerw']
    )


    # === RÓŻNICA START - STOP (RÓŻNE DNI) ===
    mask_start_stop_rozne_dni = df_final['jak_liczymy'] == "różnica Start - Stop: różne dni"
    print("Liczba dopasowań:", mask_start_stop_rozne_dni.sum())

    # Czas = od minimum_start do 15:15 + od 7:15 do maximum_stop (następnego dnia)
    godzina_715 = pd.to_datetime(df_final.loc[mask_start_stop_rozne_dni, 'maximum_stop'].dt.date.astype(str) + ' 07:15')
    godzina_1520 = pd.to_datetime(df_final.loc[mask_start_stop_rozne_dni, 'minimum_start'].dt.date.astype(str) + ' 15:20')

    czas_do_1520 = (godzina_1520 - df_final.loc[mask_start_stop_rozne_dni, 'minimum_start']).dt.total_seconds() / 60
    czas_od_715 = (df_final.loc[mask_start_stop_rozne_dni, 'maximum_stop'] - godzina_715).dt.total_seconds() / 60
    czas_sumaryczny = czas_do_1520 + czas_od_715
    print(czas_sumaryczny)

    df_final.loc[mask_start_stop_rozne_dni, 'czas_bez_przerw'] = czas_sumaryczny
    df_final.loc[mask_start_stop_rozne_dni, 'efektywnosc'] = (
        df_final.loc[mask_start_stop_rozne_dni, 'czas_cennik'] / df_final.loc[mask_start_stop_rozne_dni, 'czas_bez_przerw']
    )

    df_final['efektywnosc_przerwy'] = df_final['czas_cennik'] / (df_final['czas_bez_przerw'] - df_final['ilosc_przerw'] * 15)

    bins_eff = [-float('inf'), 0, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, float('inf')]
    labels_eff = ['<0%', '0-50%', '50-75%', '75-100%', '100-125%', 
          '125-150%', '150-200%', ">200%"]
    df_final['efektywnosc_przedzialy'] = pd.cut(df_final['efektywnosc'], bins=bins_eff, labels=labels_eff, right=False)
    df_final['efektywnosc_przerwy_przedzialy'] = pd.cut(df_final['efektywnosc_przerwy'], bins=bins_eff, labels=labels_eff, right=False)

    ### TYYDZIEŃ KALENDARZOWY
    df_final['iso_rok'] = df_final['maximum_stop'].dt.isocalendar().year
    df_final['iso_tydzien'] = df_final['maximum_stop'].dt.isocalendar().week

    return df_final

def wygeneruj_tabela_html(df):
    html = "<style>table, th, td { border: 1px solid black; border-collapse: collapse; padding: 6px; text-align: center; }</style>"
    html += df.to_html(escape=False, index=True)
    return html

def normalizuj_list(x):
    if isinstance(x, (list, np.ndarray)):
        return ', '.join(sorted(map(str, x)))
    else:
        return str(x)

def podswietl_min_20(row):
    return ['background-color: yellow' if v >= 20 else '' for v in row]

def szary_gdy_nan(val):
    if pd.isna(val):
        return 'color: gray; background-color: #F2F2F2'
    else:
        return ''

def sprawdz_haslo():
    correct_password = st.secrets["access"]["password"]

    def password_entered():
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Wpisz hasło:", type="password", on_change=password_entered, key="password")
        st.stop()   # Zatrzymaj dalsze działanie
    if not st.session_state.get("password_correct", False):
        st.text_input("Wpisz hasło:", type="password", on_change=password_entered, key="password")
        st.error("Niepoprawne hasło, spróbuj ponownie.")
        st.stop()   # Zatrzymaj dalsze działanie
