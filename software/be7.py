import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress


INPUT_FILE = 'muons_with_pressure3.csv'
ADC_THRESHOLD = 310                 # Порог отсечения электронного шума
WINDOW_SIZE = '24H'                 # Окно агрегации (сутки)
CLEAN_START = "2026-05-03 00:00:00" # Игнорируем данные до этой даты (смена геометрии)


# 2. ФУНКЦИИ ОБРАБОТКИ ДАННЫХ

def load_and_filter_data(filepath: str, threshold: int, start_date: str) -> tuple[pd.DataFrame, int]:
    """Загружает CSV и отфильтровывает шум и нестабильные периоды."""
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    total_events = len(df)
    
    # Фильтрация по порогу и дате
    mask_valid = (df['amp'] > threshold) & (df['timestamp'] >= start_date)
    df_clean = df[mask_valid].copy()
    
    return df_clean, total_events

def calculate_live_time_rates(df: pd.DataFrame, window: str) -> pd.DataFrame:
    """Агрегирует данные по окнам с учетом ФАКТИЧЕСКОГО времени работы."""
    df['time_val'] = df['timestamp']
    df.set_index('timestamp', inplace=True)

    # Агрегация базовых метрик
    aggr = df.resample(window).agg(
        muon_count=('amp', 'count'),
        pressure=('pressure', 'mean'),
        first_event=('time_val', 'min'),
        last_event=('time_val', 'max')
    ).dropna()


    aggr['live_time_sec'] = (aggr['last_event'] - aggr['first_event']).dt.total_seconds()
    aggr = aggr[aggr['live_time_sec'] > 0] # Защита от деления на ноль


    aggr['rate_hz'] = aggr['muon_count'] / aggr['live_time_sec']
    aggr['rate_err'] = np.sqrt(aggr['muon_count']) / aggr['live_time_sec']

    return aggr


# 3.  ВИЗУАЛИЗАЦИИ И ОТЧЕТОВ


def plot_barometric_analysis(aggr_data: pd.DataFrame, window: str):
    """Строит научные графики временного ряда и линейной регрессии."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    plt.style.use('dark_background')

    # Расчет регрессии
    slope, intercept, r_val, p_val, _ = linregress(aggr_data['pressure'], aggr_data['rate_hz'])

    color_muon = '#00c0f2'
    ax1.errorbar(aggr_data.index, aggr_data['rate_hz'], yerr=aggr_data['rate_err'], 
                 fmt='-o', color=color_muon, linewidth=3, capsize=6, markersize=8, label='Rate (Мюоны)')
    ax1.set_xlabel('Дата и время', fontsize=12)
    ax1.set_ylabel('Скорость счета мюонов (Гц)', color=color_muon, fontsize=13, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color_muon)

    ax1_twin = ax1.twinx()
    color_press = '#ff4d4d'
    ax1_twin.plot(aggr_data.index, aggr_data['pressure'], color=color_press, 
                  linewidth=3, linestyle='--', marker='s', alpha=0.8, label='Давление')
    ax1_twin.set_ylabel('Атмосферное давление (мм рт. ст.)', color=color_press, fontsize=13, fontweight='bold')
    ax1_twin.tick_params(axis='y', labelcolor=color_press)

    rate_min, rate_max = aggr_data['rate_hz'].min(), aggr_data['rate_hz'].max()
    margin = (rate_max - rate_min) * 0.15
    ax1.set_ylim(rate_min - margin, rate_max + margin)

    ax1.set_title(f'Поток мюонов и Давление (Окно: {window})', fontsize=16, pad=20)
    ax1.grid(True, alpha=0.15)

    # ГРАФИК 2: Точечная корреляция
    ax2.errorbar(aggr_data['pressure'], aggr_data['rate_hz'], yerr=aggr_data['rate_err'], 
                 fmt='o', color='mediumpurple', markersize=12, ecolor='gray', capsize=5, label='Экспериментальные данные')

    x_range = np.array([aggr_data['pressure'].min(), aggr_data['pressure'].max()])
    ax2.plot(x_range, slope * x_range + intercept, color='yellow', linestyle='--', linewidth=3, 
             label=f'Линейная аппроксимация (R = {r_val:.2f})')

    ax2.set_xlabel('Атмосферное давление (мм рт. ст.)', fontsize=13)
    ax2.set_ylabel('Скорость счета мюонов (Гц)', fontsize=13)
    ax2.set_title('Барометрический эффект', fontsize=16)
    ax2.legend(fontsize=14, facecolor='#222222')
    ax2.grid(True, alpha=0.15)

    plt.tight_layout()
    plt.show()

    return r_val, p_val

def print_science_report(aggr_data: pd.DataFrame, total_raw: int, r_val: float, p_val: float):
    """Выводит формализованный отчет в консоль."""
    print("\n" + "="*50)
    print(f"ОТЧЕТ О БАРОМЕТРИЧЕСКОМ ИССЛЕДОВАНИИ")
    print("="*50)
    print(f"Сырых событий до фильтрации: {total_raw}")
    print(f"Очищенных окон агрегации: {len(aggr_data)}")
    print(f"Анализируемый период: {aggr_data.index.min().date()} — {aggr_data.index.max().date()}")
    print("-" * 50)
    print(f"Коэффициент корреляции Пирсона (R): {r_val:.4f}")
    print(f"Статистическая значимость (P-value): {p_val:.4f}")
    print("-" * 50)
    
    if r_val < 0:
        print("Обнаружена обратная зависимость.")
    else:
        print("Коэффициент положительный. Ошибка эксперимента.")

    if p_val < 0.05:
        print("Результат статистически значим (P < 0.05).")
    else:
        print("Результат статистически не значим (Требуется больше данных).")
    print("="*50 + "\n")




if __name__ == "__main__":
    print("Инициализация  данных...")
    
    df_clean, total_events = load_and_filter_data(INPUT_FILE, ADC_THRESHOLD, CLEAN_START)
    
    aggr_data = calculate_live_time_rates(df_clean, WINDOW_SIZE)
    
    r_val, p_val = plot_barometric_analysis(aggr_data, WINDOW_SIZE)
    
    print_science_report(aggr_data, total_events, r_val, p_val)