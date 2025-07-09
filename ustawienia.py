import pandas as pd
analizowane_modele = ['AMALFI', 'AVANT', 'CALYPSO', 'COCO', 'CUPIDO', 'DIVA A', 'DIVA B',
         'DUO II', 'ELIXIR', 'EXTREME I', 'EXTREME II', 'GOYA', 'GREY II', 'GREY I', 'GREY', 'HUDSON', 'HORIZON A',
         'KELLY', 'LENOX', 'LOBBY', 'MAXWELL', 'MYSTIC', 'MISTRAL', 'ONYX', 'OVAL', 'OXYGEN',
         'RAY', 'REVERSO', 'RITZ', 'SAMOA', 'SPECTRA', 'STONE', 'TOBAGO', 'TOPAZ', 'UNO',
         'WILLOW']

model_mapping = {
    'GREY II': 'GREY',
    'GREY I': 'GREY',
    'EXTREME II': 'EXTREME',
    'EXTREME I': 'EXTREME',
    'HORIZON A': 'HORIZON',
    'DUO II': 'DUO',
    'DIVA A': 'DIVA',
    'DIVA B': 'DIVA',
    'CUPIDO': 'STONE',
    'LOBBY': 'HORIZON',
    'TOBAGO': 'DIVA'
}

model_skrot_mapping = {
    'LOB': 'HOR',
    'TOB': 'DIV',
    'CUP': 'STO'
}

analizowani_piankarze = ['P01', 
                         'P02', 
                         'P06']

imiona_piankarzy = {
    'P01': 'Piotr',
    'P02': 'Wojtek',
    'P06': 'Valery'
}
### Zmieniamy błędnie ustawiony daty
#U P06 dwukrotnie wystapil brak odklikniencia zakonczonego piankowania
P06_zmiana ={
    pd.to_datetime('2024-07-02 14:20:14'): pd.to_datetime('2024-07-02 12:04:58'),
    pd.to_datetime('2025-04-01 14:13:08'): pd.to_datetime('2025-04-01 09:17:31')
}

P02_zmiana ={
    pd.to_datetime('2023-11-27 11:47:19'): pd.to_datetime('2024-11-27 09:43:40'),
    pd.to_datetime('2023-12-14 14:47:41'): pd.to_datetime('2024-12-14 13:35:41'),
    pd.to_datetime('2024-12-06 13:14:05'): pd.to_datetime('2024-12-06 11:34:48')
}