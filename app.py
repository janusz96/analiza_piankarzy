import pandas as pd
import streamlit as st
import numpy as np
import funkcje_pomocnicze
import ustawienia
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
import analizy
from datetime import date, timedelta

### USTAWIENIA STREAMLIT
st.set_page_config(page_title="Analiza piankarzy", layout="wide")
st.title("📊 Analiza czasu pracy piankarzy")

### WPISYWANIE HASŁA
funkcje_pomocnicze.sprawdz_haslo()

start = time.perf_counter()

### ŁADOWANIE DANYCH ŹRÓDŁOWYCH
#df_org = pd.read_excel("czasy_wszystko_do_2025.06.30_piankowanie.xls")
#df_cennik = pd.read_excel("TABELA CZASY 160.92.02 CZASY NA PIANKOWANIE_nowy.xls")

if 'bazowe_dane' not in st.session_state:
    st.session_state.bazowe_dane = funkcje_pomocnicze.zaladuj_dane(st.secrets["sciezki"]["sciezka_baza"])
if 'dane_cennik' not in st.session_state:
    st.session_state.dane_cennik = funkcje_pomocnicze.zaladuj_dane(st.secrets["sciezki"]["sciezka_cennik"])

df_org = st.session_state.bazowe_dane.copy()
df_cennik = st.session_state.dane_cennik.copy()

stop = time.perf_counter()
st.write(f"⏱️ Czas ładowania danych: {stop - start:.2f} s")
start = time.perf_counter()

### WYBRANIE TAPICERÓW DO ANALIZY
st.subheader("PODSTAWOWE INFORMACJE O ANALIZIE")
#df_org = df_org[df_org['Nazwisko'].isin(ustawienia.analizowani_piankarze)]
#st.write("Piankarze ujęci w analizie to: ", ustawienia.imiona_piankarzy)

### ZAKRES DAT
st.write("Zakres dat analizy to ", df_org['Start'].dt.date.min()," do ", df_org['Stop'].dt.date.max())

### USUNIĘCIE ZBĘDNYCH KOLUMN
kolumny_do_usuniecia = ['Imie', 'Wydzial', 'Grupy akord. opis', 'Grupy akord. kod', 'Przerwa']
df_org.drop(columns=kolumny_do_usuniecia, inplace=True)

### SORTOWANIE 
df_org.sort_values(by=["Nazwisko", "Start"], ascending=[True, True], inplace=True)

stop = time.perf_counter()
st.write(f"⏱️ Czas usunieca kolumn i sortowania danych: {stop - start:.2f} s")
start = time.perf_counter()

### DODANIE INFORMACJI O TYM KIEDY UKOŃCZONO PIANKOWANIE
df_org["kiedy_ukonczono"] = df_org["Czas"].apply(lambda x: "mniej niż 3 minuty" if x < 3 else "inne")
rozkład_proc = (
    df_org.groupby("Nazwisko")["kiedy_ukonczono"]
    .value_counts(normalize=True)
    .unstack(fill_value=0)
    * 100
)
rozkład_proc = rozkład_proc.round(1)
rozkład_proc["Ilość opiankowanych brył"] = df_org.groupby("Nazwisko").size()
st.markdown("### Rozkład procentowy (%) czasu ukończenia piankowania")
st.markdown(
    "Tabela pokazuje procent pomiarów, w których czas piankowania był krótszy niż 3 minuty.<br>"
    "**INTERPRETACJA**: piankarze do lipca 2025 roku skanowali bryły po zakończeniu piankowania.",
    unsafe_allow_html=True
)
html_table = funkcje_pomocnicze.wygeneruj_tabela_html(rozkład_proc.round(1))
st.markdown(html_table, unsafe_allow_html=True)

### MODYFIKACJA ARTYKUL NAZWA
# WYCIAGAMY MODEL I MODYFIKUJEMY
df_org['model'] = df_org['Artykul nazwa'].apply(funkcje_pomocnicze.dodaj_model)
df_org['model'] = df_org['model'].replace(ustawienia.model_mapping)

# WYCIAGAMY BRYLE I MODYFIKUJEMY
df_org['bryla'] = df_org['Artykul nazwa'].apply(funkcje_pomocnicze.dodaj_bryla)
df_org['bryla_zmodyfikowana'] = df_org['bryla'].apply(funkcje_pomocnicze.modyfikuj_bryla)
df_org['model_bryla'] = df_org['model'] + ' ' + df_org['bryla_zmodyfikowana']

# EDYCJA DLA PODUSZEK
mask_poduszka = df_org['bryla_zmodyfikowana'] == 'poduszka'
df_org.loc[mask_poduszka, 'model'] = 'poduszka'
df_org.loc[mask_poduszka, 'model_bryla'] = 'poduszka'

st.subheader("INFORMACJE O MODELACH I BRYŁACH")
st.markdown("### Zmodyfikowane modele i/lub bryły")
st.markdown(
    "Tabela pokazuje wszystkie modele i bryły, które zostały zmodyfikowane.<br>"
    "**INTERPRETACJA**: redukcja liczby unikalnych zmiennych przez ujednolicenie sprzyja prostszej i bardziej przejrzystej analizie danych.",
    unsafe_allow_html=True
)
df_roznice_model_bryla = df_org[df_org['Artykul nazwa'] != df_org['model_bryla']][['Artykul nazwa', 'model_bryla']]
df_roznice_model_bryla = df_roznice_model_bryla.drop_duplicates()
df_roznice_model_bryla = df_roznice_model_bryla.sort_values(by='Artykul nazwa')
df_roznice_model_bryla = df_roznice_model_bryla.rename(columns={
    'Artykul nazwa': 'Oryginalny model + bryła',
    'model_bryla': 'Poprawiony model + bryła'
})
df_roznice_model_bryla = df_roznice_model_bryla.reset_index(drop=True)
st.write(df_roznice_model_bryla)

### ŁACZENIE Z CZASEM CENNIKOWYM
mapa_czasu = df_cennik.set_index("model_bryla")["czas"]
df_org["czas_cennik"] = df_org["model_bryla"].map(mapa_czasu).fillna(0)
df_org.loc[df_org['model_bryla'] == 'poduszka', 'czas_cennik'] = 1
df_filtr = df_org[df_org["czas_cennik"] == 0].copy()

stop = time.perf_counter()
st.write(f"⏱️ Czas laczenia z cennikiem i pozostalego obrabiania danych: {stop - start:.2f} s")
start = time.perf_counter()

#### POKAZUJEMY WARTOSCI DO KTORYCH BRAK WARTOSCI W CENNIKU
df_brak_cennika = df_filtr.groupby(['Artykul nazwa', 'model_bryla']).size().reset_index(name='Liczba wystąpień')
df_brak_cennika = df_brak_cennika.sort_values(by=['Artykul nazwa', 'model_bryla'])
df_brak_cennika = df_brak_cennika.rename(columns={
    'Artykul nazwa': 'Oryginalny model + bryła',
    'model_bryla': 'Poprawiony model + bryła'
})
st.markdown("### Bryły do których brakuje wartości w cenniku")
st.markdown(
    "Tabela pokazuje wszystkie modele i bryły do których brakuje wartości w cenniku<br>",
    unsafe_allow_html=True
)
st.write(df_brak_cennika)

### ZAPISANIE PLIKU PRZED GRUPOWANIEM DANYCH
#df_org.to_excel('df_przed_zmianami.xlsx', index=False)

stop = time.perf_counter()
st.write(f"⏱️ Zapisanie danych do excela: {stop - start:.2f} s")

### LACZYMY DANE W KOMISJE
if 'dane_z_id_komisji' not in st.session_state:
    st.session_state.dane_z_id_komisji = funkcje_pomocnicze.dodaj_id_komisji(df_org)
if 'zgrupowane_dane' not in st.session_state:
    st.session_state.zgrupowane_dane = funkcje_pomocnicze.polacz_dane_w_komisje(st.session_state.dane_z_id_komisji)
df_group = st.session_state.zgrupowane_dane


### MODYFIKACJA DANYCH
df_group['model'] = df_group['model'].apply(funkcje_pomocnicze.normalizuj_list)
df_group['nazwisko'] = df_group['nazwisko'].apply(funkcje_pomocnicze.normalizuj_list)

### FILTRUJEMY DANE Z GŁÓWNEJ TABELI
# 1 - odrzucamy pierwsze piankowania, jezeli były przed 12:00
# 2 - odrzucamy komisje, które zawierają NIETYPOWE sofy lub fotele
df_filtrowany = df_group[
    #(df_group['jak_liczymy'] != "wyłączone z analizy - pierwsze odbicie przed 12:00") &
    (df_group['suma_fotele_nietypowe'] == 0) &
    (df_group['suma_sofy_nietypowe'] == 0)
]

### TABELA WYSTAPIEN
tabela_wystapien = df_group.groupby(['model', 'nazwisko']).size().unstack(fill_value=0)
tabela_wystapien = tabela_wystapien.astype(int)
tabela_wystapien = tabela_wystapien[(tabela_wystapien >= 20).any(axis=1)]

st.write("### Ilości opiankowanych komisji przez piankarzy w podziale na modele")
st.markdown(
    "Filtr 1: wykluczone komisje, które zawierają nietypowe sofy i fotele.<br>"
    "Wyświetlane są tylko modele, w ktorych co najmniej jeden piankarz opiankował minimum 20 komisji",
    unsafe_allow_html=True
)
styled = tabela_wystapien.style.apply(funkcje_pomocnicze.podswietl_min_20, axis=1)
st.dataframe(styled, use_container_width=True)

### TABELA JAK LICZYMY
tabela_jak_liczymy = df_group.groupby(['jak_liczymy', 'nazwisko']).size().unstack(fill_value=0)
tabela_jak_liczymy = tabela_jak_liczymy.astype(int)
tabela_jak_liczymy = tabela_jak_liczymy[(tabela_jak_liczymy >= 20).any(axis=1)]

st.write("### Ilości opiankowanych komisji przez piankarzy w podziale na sposób liczenia")
st.markdown(
    "Filtr 1: wykluczone komisje, które zawierają nietypowe sofy i fotele.<br>"
    "Wyświetlane są tylko sposoby liczenia, w ktorych co najmniej jeden piankarz opiankował minimum 10 komisji",
    unsafe_allow_html=True
)
styled_jak_liczymy = tabela_jak_liczymy.style.apply(funkcje_pomocnicze.podswietl_min_20, axis=1)
st.dataframe(styled_jak_liczymy, use_container_width=True)

st.write("### Mediana efektywności (%) komisji przez piankarzy w podziale na sposób liczenia")
df_filtrowany_jak_liczymy = df_group[
    (df_group['suma_fotele_nietypowe'] == 0) &
    (df_group['suma_sofy_nietypowe'] == 0)
]
pivot_mediana_jak_liczymy = df_filtrowany_jak_liczymy.pivot_table(
    index='jak_liczymy',
    columns='nazwisko',
    values='efektywnosc_przerwy',
    aggfunc='median'
)
pivot_mediana_jak_liczymy = (pivot_mediana_jak_liczymy * 100).round(0).astype('Int64')
st.dataframe(pivot_mediana_jak_liczymy.style.format("{:.0f}").set_properties(**{'text-align': 'center'}), use_container_width=True)




### TABELA Z MEDIANA EFEKTYWNOSCI
st.subheader("METODA 1: Efektywność na podstawie logowanych czasów")
efektywnosc_zakres = st.slider(
    "Zakres mediany efektywności (%)",
    min_value=0,
    max_value=300,
    value=(90, 220),
    step=5
)
dolny_prog = efektywnosc_zakres[0] / 100
gorny_prog = efektywnosc_zakres[1] / 100
df_filtrowany = df_filtrowany[
    (df_filtrowany['efektywnosc_przerwy']>=dolny_prog) &
    (df_filtrowany['efektywnosc_przerwy']<=gorny_prog)
]
st.markdown(
    "Obejmuje czasy spełniające następujące warunki:<br>"
    f"1. Zakres dat: {df_group['minimum_start'].dt.date.min()} do {df_group['minimum_start'].dt.date.max()}<br>"
    "2. Piankowanie nie obejmowało nietypwych foteli lub sof.<br>"
    f"3. Efektywność piankowania mieści się w przedziale {int(dolny_prog*100)}(%) do {int(gorny_prog*100)}(%)",
    unsafe_allow_html=True
)
st.write("### Mediana efektywności (%)")




# Obliczamy medianę efektywności
pivot_mediana = df_filtrowany.pivot_table(
    index='model',
    columns='nazwisko',
    values='efektywnosc_przerwy',
    aggfunc='median'
)

pivot_count = df_filtrowany.pivot_table(
    index='model',
    columns='nazwisko',
    values='efektywnosc_przerwy',
    aggfunc='count'
)

poprawne_wiersze = pivot_count[(pivot_count >= 20).any(axis=1)].index
pivot_mediana = pivot_mediana.loc[poprawne_wiersze]
pivot_count = pivot_count.loc[poprawne_wiersze]
pivot_median_masked = pivot_mediana.where(pivot_count >= 20)
pivot_median_percent = (pivot_median_masked * 100).round(0)

grupy = df_group[
    (df_group['jak_liczymy'] != "wyłączone z analizy - pierwsze odbicie przed 12:00") &
    (df_group['suma_fotele_nietypowe'] == 0) &
    (df_group['suma_sofy_nietypowe'] == 0)
].groupby(['model', 'nazwisko'])
liczba_wszystkich = grupy.size()
liczba_ponizej = grupy.apply(lambda x: (x['efektywnosc_przerwy'] < dolny_prog).sum())
liczba_powyzej = grupy.apply(lambda x: (x['efektywnosc_przerwy'] > gorny_prog).sum())
proc_ponizej = (liczba_ponizej / liczba_wszystkich * 100).unstack(fill_value=0)
proc_powyzej = (liczba_powyzej / liczba_wszystkich * 100).unstack(fill_value=0)
proc_ponizej = proc_ponizej.loc[poprawne_wiersze]
proc_powyzej = proc_powyzej.loc[poprawne_wiersze]
proc_ponizej_mean = proc_ponizej.mean(axis=1).round(1)
proc_powyzej_mean = proc_powyzej.mean(axis=1).round(1)
pivot_median_percent[f'% ponizej efektywności {int(dolny_prog*100)}%'] = proc_ponizej_mean
pivot_median_percent[f'% powyzej efektywności {int(gorny_prog*100)}%'] = proc_powyzej_mean

styled_median = pivot_median_percent.style.applymap(funkcje_pomocnicze.szary_gdy_nan).format("{:.0f}")
#st.dataframe(styled_median, use_container_width=True)
styled_median = pivot_median_percent.style\
    .applymap(funkcje_pomocnicze.szary_gdy_nan)\
    .format("{:.0f}")\
    .set_properties(**{'text-align': 'center'})
st.write(styled_median)


### ZAPISANIE ZGRUPOWANYCH DANYCH DO EXCELA
#df_group.to_excel('df_grouped.xlsx', index=False)



### PODGLAD EFEKTYWNOSCI TAPICEROWANIE
st.subheader("METODA 2: Efektywność na podstawie róznicy między czasem rozpoczęcia a czasem zakończenia. Tylko dane od 2 lipca 2025")
st.subheader("PIANKOWANIE POKAZANE NA PLANIE DNIA")
piankarze = df_group['nazwisko'].unique()
wybrany_piankarz = st.selectbox("Wybierz piankarza", sorted(piankarze))

lata = sorted(df_group['iso_rok'].unique())
aktualny_rok = datetime.datetime.now().year
default_index = lata.index(aktualny_rok) if aktualny_rok in lata else 0
wybrany_rok = st.selectbox("Rok", lata, index=default_index)

tygodnie = sorted(df_group[df_group['iso_rok'] == wybrany_rok]['iso_tydzien'].unique())
aktualny_tydzien = datetime.datetime.now().isocalendar().week
default_tydzien_index = tygodnie.index(aktualny_tydzien) if aktualny_tydzien in tygodnie else 0
wybrany_tydzien = st.selectbox("Tydzień", tygodnie, index=default_tydzien_index)

df_kalendarz = df_group[
    (df_group['nazwisko'] == wybrany_piankarz) &
    (df_group['iso_rok'] == wybrany_rok) &
    (df_group['iso_tydzien'] == wybrany_tydzien)
].copy()
df_kalendarz['dzien_tygodnia'] = df_kalendarz['maximum_stop'].dt.day_name
dni_map = {
    'Monday': 'poniedziałek',
    'Tuesday': 'wtorek',
    'Wednesday': 'środa',
    'Thursday': 'czwartek',
    'Friday': 'piątek',
    'Saturday': 'sobota',
    'Sunday': 'niedziela'
}

df_kalendarz['dzien_tygodnia'] = df_kalendarz['dzien_tygodnia'].map(dni_map)
df_kalendarz['start'] = df_kalendarz['minimum_start']
df_kalendarz['stop'] = df_kalendarz['maximum_stop']
df_kalendarz['czas'] = (df_kalendarz['stop'] - df_kalendarz['start']).dt.total_seconds() / 60


### DRUGA WERSJA
# Przygotowanie danych
df = df_kalendarz.copy()

# Dodaj kolumnę z dniem tygodnia (np. "poniedziałek")
dni_tygodnia = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek']
df['dzien'] = df['minimum_start'].dt.dayofweek.map(lambda x: dni_tygodnia[x])

dni_w_danych = df['dzien'].unique()
dni_brakujace = [d for d in dni_tygodnia if d not in dni_w_danych]

if dni_brakujace:
    df_brakujace = pd.DataFrame({
        'dzien': dni_brakujace,
        'czas': 0,
        'y_start': 0,
        'model': None,
        'komisja': None,
        'czas_bez_przerw': None,
        'efektywnosc_przerwy': None,
        'ilosc_przerw': 0,
        'czas_cennik': 0,
        'jak_liczymy': None,
        'minimum_start': pd.to_datetime('2025-01-01 02:00'),  # dowolna godzina, np. 6:00
        'maximum_stop': pd.to_datetime('2025-01-01 02:00')
    })
    df = pd.concat([df, df_brakujace], ignore_index=True)

# Dodaj kolumny z godziną (jako timedelta od 00:00)
df['start_time'] = df['minimum_start'].dt.time
df['end_time'] = df['maximum_stop'].dt.time

# Zamiana czasu na minuty od północy (dla osi Y)
df['y_start'] = df['minimum_start'].dt.hour * 60 + df['minimum_start'].dt.minute + df['minimum_start'].dt.second / 60
df['y_end'] = df['maximum_stop'].dt.hour * 60 + df['maximum_stop'].dt.minute + df['maximum_stop'].dt.second / 60
df['czas'] = df['y_end'] - df['y_start']

kolory_map = {
    'różnica Start - Stop: ten sam dzień': 'rgba(0, 128, 0, 0.9)',               # zielony
    'różnica Start - Stop: różne dni': 'rgba(255, 0, 0, 0.9)',                 # czerwony
    'pierwsze odbicie po 12:00': 'rgba(0, 0, 255, 0.8)',                       # niebieski
    'wyłączone z analizy - pierwsze odbicie przed 12:00': 'rgba(255, 165, 0, 0.9)',  # pomarańczowy
    'różnica pomiędzy komisjami': 'rgba(0, 0, 0, 1.0)'                         # czarny
}


# Tworzenie wykresu
fig = go.Figure()

for _, row in df.iterrows():
    czas_wyswietlany = max(row['czas'], 3)
    kolor = kolory_map.get(row['jak_liczymy'], 'rgba(150, 150, 150, 0.5)')

    if pd.notnull(row['czas_bez_przerw']):
        czas_text = f"Czas wyliczony: {int(row['czas_bez_przerw']-row['ilosc_przerw']*15)}"
    else:
        czas_text = "Czas wyliczony: brak"

    if pd.notnull(row['efektywnosc_przerwy']):
        efektywnosc_text = f"Efektywność (%): {int(row['efektywnosc_przerwy']*100)}"
    else:
        efektywnosc_text = "Efektywność (%): brak"
    
    fig.add_trace(go.Bar(
        x=[row['dzien']],
        y=[czas_wyswietlany],
        base=[row['y_start']],
        offsetgroup=row['dzien'],
        name=row['model'],
        orientation='v',
        hovertemplate=(
            f"Model: {row['model']}<br>"
            f"Komisja: {row['komisja']}<br>"
            f"{row['minimum_start'].strftime('%H:%M')}–{row['maximum_stop'].strftime('%H:%M')}<br>"
            f"{efektywnosc_text}<br>"
            f"{czas_text}<br>"
            f"Czas cennikowy: {int(row['czas_cennik'])}<br>"
            f"Ilość przerw: {row['ilosc_przerw']}<br>"
            f"Jak liczony jest czas? {row['jak_liczymy']}"
        ),
        marker=dict(
            color=kolor,
            line=dict(color='black', width=0.5)  # cieniutka ciemna obwódka
        )  # można dodać kolory wg modelu
    ))

# Ustawienia osi
fig.update_layout(
    title=f"Harmonogram piankowania – {wybrany_piankarz}, tydzień {wybrany_tydzien}, {wybrany_rok}",
    xaxis=dict(
        title="Dzień tygodnia",
        type="category",
        categoryorder='array',
        categoryarray=dni_tygodnia
    ),
    yaxis=dict(
        title="Godzina dnia",
        tickvals=[i*60 for i in range(6, 17)],
        ticktext=[f"{i:02d}:00" for i in range(6, 17)],
        range=[360, 960],  # od 6:00 (360 min) do 16:00 (960 min)
    ),
    bargap=0.1,
    bargroupgap=0,
    height=600,
    barmode='group',
    showlegend=False
)

for i in range(1, len(dni_tygodnia)):
    fig.add_shape(
        type="line",
        x0=i - 0.5,
        x1=i - 0.5,
        y0=360,     # dolna granica osi y (np. 6:00)
        y1=960,     # górna granica osi y (np. 16:00)
        xref="x",
        yref="y",
        line=dict(color="LightGray", width=1, dash='dot')  # możesz zmienić dash na 'solid' lub 'dash'
    )

st.plotly_chart(fig, use_container_width=True)


### TABELA Z EFEKTYWNOŚCIA PO ZMIANE SPOSOBU KLIKANIA CZASU PRZEZ TAPICEROW
st.subheader("TABELA EFEKTYWNOŚCI PO ZMIANIE SPOSOBU REJESTRACJI CZASÓW")
df_nowe_obserwacje = df_group.copy()
df_nowe_obserwacje = df_nowe_obserwacje[df_nowe_obserwacje['jak_liczymy']=='różnica Start - Stop: ten sam dzień']
df_nowe_obserwacje = df_nowe_obserwacje[df_nowe_obserwacje['minimum_start'] >='2025-07-01']
df_nowe_obserwacje = df_nowe_obserwacje[df_nowe_obserwacje['nazwisko'].isin(ustawienia.analizowani_piankarze)]
df_nowe_obserwacje = df_nowe_obserwacje[df_nowe_obserwacje['suma_sofy_nietypowe'] == 0]
df_nowe_obserwacje = df_nowe_obserwacje[df_nowe_obserwacje['suma_fotele_nietypowe'] == 0]
efektywnosc_zakres_nowe = st.slider(
    "Zakres efektywności (%)",
    min_value=0,
    max_value=300,
    value=(90, 220),
    step=5
)
dolny_prog_nowe = efektywnosc_zakres_nowe[0] / 100
gorny_prog_nowe = efektywnosc_zakres_nowe[1] / 100
df_nowe_obserwacje = df_nowe_obserwacje[
    (df_nowe_obserwacje['efektywnosc_przerwy']>=dolny_prog_nowe) &
    (df_nowe_obserwacje['efektywnosc_przerwy']<=gorny_prog_nowe)
]
st.markdown(
    "Obejmuje czasy spełniające następujące warunki:<br>"
    f"1. Zakres dat: {df_nowe_obserwacje['minimum_start'].dt.date.min()} do {df_nowe_obserwacje['minimum_start'].dt.date.max()}<br>"
    "2. Tylko piankowania, które rozpoczęły się i zakończyły tego samego dnia.<br>"
    "3. Piankowanie nie obejmowało nietypwych foteli lub sof.<br>"
    f"4. Efektywność piankowania mieści się w przedziale {int(dolny_prog_nowe*100)}(%) do {int(gorny_prog_nowe*100)}(%)",
    unsafe_allow_html=True
)
# 1. Pivot i MultiIndex
tabela_obserwacji = df_nowe_obserwacje.pivot_table(
    index='model',
    columns='nazwisko',
    values=['minimum_start', 'efektywnosc_przerwy'],
    aggfunc={'minimum_start': 'count', 'efektywnosc_przerwy': 'median'},
    fill_value=0
)
tabela_obserwacji = tabela_obserwacji.swaplevel(axis=1)
tabela_obserwacji = tabela_obserwacji.sort_index(axis=1, level=0)

# 2. Etykiety kolumn
tabela_obserwacji.columns = [
    (nazwisko, 'ilość obserwacji' if metryka == 'minimum_start' else 'mediana efektywności (%)')
    for nazwisko, metryka in tabela_obserwacji.columns
]
tabela_obserwacji.columns = pd.MultiIndex.from_tuples(tabela_obserwacji.columns)

# 3. Zaokrąglenie median efektywności
for nazwisko in tabela_obserwacji.columns.levels[0]:
    col = (nazwisko, 'mediana efektywności (%)')
    if col in tabela_obserwacji.columns:
        tabela_obserwacji[col] = (tabela_obserwacji[col].astype(float) * 100).round(0).astype(int)

# 4. Stylowanie kolumn nazwiskami
def styluj_obserwacje(df):
    style = pd.DataFrame('', index=df.index, columns=df.columns)
    nazwiska = df.columns.get_level_values(0).unique()

    for nazwisko in nazwiska:
        col_ilosc = (nazwisko, 'ilość obserwacji')
        col_mediana = (nazwisko, 'mediana efektywności (%)')

        if col_ilosc in df.columns and col_mediana in df.columns:
            for idx in df.index:
                if df.loc[idx, col_ilosc] >= 5:
                    style.loc[idx, col_ilosc] = 'background-color: #d1e7dd;'  # jasna zieleń
                    style.loc[idx, col_mediana] = 'background-color: #d1e7dd;'

    return style

# 5. Wyświetlenie
st.dataframe(tabela_obserwacji.style.apply(styluj_obserwacje, axis=None))


### METODA 3
st.subheader("Analiza na podstawie pliku 110.101.120 WYDAJNOSC PRACOWNIKOW")
st.write("Zakres dat: 1 maja 2024 roku do 8 lipca 2025 roku")
analizy.metoda3_plik_wydajnosc(st.secrets["sciezki"]["p06_cennik"], st.secrets["sciezki"]["p06_czas_pracy"], "Valery")
analizy.metoda3_plik_wydajnosc(st.secrets["sciezki"]["p02_cennik"], st.secrets["sciezki"]["p02_czas_pracy"], "Wojtek")