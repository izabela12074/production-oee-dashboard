import pandas as pd
import numpy as np

# ── Wczytaj dane ──
df = pd.read_csv('data/Machine Downtime.csv')

# ── Ustandaryzuj nazwy kolumn ──
df.columns = df.columns.str.strip().str.lower()\
    .str.replace(r'[^\w]', '_', regex=True)\
    .str.replace(r'_+', '_', regex=True)\
    .str.strip('_')

# ── Napraw datę ──
df['date'] = pd.to_datetime(df['date'], dayfirst=True)
df['week']       = df['date'].dt.isocalendar().week.astype(int)
df['month']      = df['date'].dt.month
df['month_name'] = df['date'].dt.strftime('%B')
df['year']       = df['date'].dt.year

# ── Kolumna Downtime: zamień tekst na 0/1 ──
df['failure_flag'] = df['downtime'].str.strip()\
    .map({'Machine_Failure': 1, 'No_Machine_Failure': 0})

# ── Agreguj do poziomu maszyna + dzień ──
daily = df.groupby(
    ['machine_id', 'date', 'week', 'month', 'month_name', 'year', 'assembly_line_no']
).agg(
    total_records     = ('failure_flag',     'count'),
    failure_count     = ('failure_flag',     'sum'),
    avg_spindle_speed = ('spindle_speed_rpm','mean'),
    avg_torque        = ('torque_nm',        'mean'),
    avg_vibration     = ('tool_vibration_m', 'mean'),
    avg_voltage       = ('voltage_volts',    'mean'),
    avg_cutting       = ('cutting_kn',       'mean'),
).reset_index()

# ── AVAILABILITY ──
daily['availability'] = (
    (daily['total_records'] - daily['failure_count']) / daily['total_records']
).clip(0, 1)

# ── PERFORMANCE ──
p95_speed = df['spindle_speed_rpm'].quantile(0.95)
daily['performance'] = (daily['avg_spindle_speed'] / p95_speed).clip(0, 1)

# ── QUALITY ──
p95_vib = df['tool_vibration_m'].quantile(0.95)
vib_score = (1 - daily['avg_vibration'] / p95_vib).clip(0, 1)
daily['quality'] = (vib_score * 0.7 + daily['availability'] * 0.3).clip(0, 1)

# ── OEE ──
daily['oee'] = (daily['availability'] * daily['performance'] * daily['quality']).round(4)

for col in ['availability', 'performance', 'quality']:
    daily[col] = daily[col].round(4)

# ── Klasyfikacja OEE ──
def oee_class(oee):
    if oee >= 0.85:   return 'World Class (>=85%)'
    elif oee >= 0.65: return 'Acceptable (65-84%)'
    elif oee >= 0.40: return 'Needs Improvement (40-64%)'
    else:             return 'Poor (<40%)'

daily['oee_class'] = daily['oee'].apply(oee_class)
daily['line_label'] = daily['assembly_line_no'].str.replace('_', ' ')
daily['failure_count'] = daily['failure_count'].astype(int)
daily['total_records']  = daily['total_records'].astype(int)

# ── Zapisz ──
daily.to_csv('data/oee_cleaned.csv', index=False)
daily.to_excel('data/oee_cleaned.xlsx', index=False)

print("Done! Zapisano", len(daily), "wierszy.")