'''
fig = px.timeline(
    df_kalendarz,
    x_start="start",
    x_end="stop",
    y="dzien_tygodnia",
    color="model",  # kolor wg modelu
    hover_data=["model", "czas"]
)
fig.update_yaxes(categoryorder='array', categoryarray=[
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"
])
fig.update_layout(
    title=f"Harmonogram piankowania – {wybrany_tapicer}, tydzień {wybrany_tydzien}, {wybrany_rok}",
    xaxis_title="Godzina",
    yaxis_title="Dzień tygodnia",
    bargap=0.2,
    height=500
)

st.plotly_chart(fig, use_container_width=True)
'''

'''
# Grupowanie: suma czasów_cennikowych dla każdego modelu per dzień
df_valery_cennik = pd.read_excel("valery_cennik.xlsx")
df_valery_czas_pracy = pd.read_excel("valery_czas_pracy.xlsx")
df_valery_cennik['model'] = df_valery_cennik['model'].replace(ustawienia.model_skrot_mapping)
df_pivot = df_valery_cennik.pivot_table(index='dzien', columns='model', values='cennik', aggfunc='sum', fill_value=0)

# Połączenie z czasem_realnym
df_all = df_valery_czas_pracy.merge(df_pivot, on='dzien', how='left').set_index('dzien')
df_all = df_all.dropna(subset=['czas_pracy'])
df_all = df_all[df_all['czas_pracy'] != 0]
df_all = df_all[~df_all.drop(columns='czas_pracy').isna().all(axis=1)]
data_od_ktorej_odejmowano_35_minut = pd.to_datetime('2025-01-17')
df_all.loc[df_all.index < data_od_ktorej_odejmowano_35_minut, 'czas_pracy'] -= 35


# Przygotowanie do regresji MNK
X = df_all.drop(columns='czas_pracy')
y = df_all['czas_pracy']

print("NaN w y:", y.isna().sum())

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
'''