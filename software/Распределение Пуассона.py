import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


THRESHOLD_ADC = 350  # Порог отсечения шума


# ЗАГРУЗКА ДАННЫХ
print("Загрузка и обработка данных...")
df = pd.read_csv('1-2-3-4-5-6-7-8-9may.csv', names=['time', 'adc_value'])

# Переводим в числа и время, и значения АЦП
df['time'] = pd.to_numeric(df['time'], errors='coerce')
df['adc_value'] = pd.to_numeric(df['adc_value'], errors='coerce')
df = df.dropna(subset=['time', 'adc_value']).reset_index(drop=True)

# Сшивание таймера
is_reset = df['time'] < df['time'].shift(1)
offsets = np.where(is_reset, df['time'].shift(1), 0)
df['fixed_time_sec'] = df['time'] + np.cumsum(offsets)

# Отсекаем шум
df_muons = df[df['adc_value'] > THRESHOLD_ADC].copy()

# Считаем разницу времени уже между чистыми мюонами
df_muons['delta_t'] = df_muons['fixed_time_sec'].diff()
dt_values = df_muons['delta_t'].dropna().values

# Убираем дубликаты (события в одну секунду) и 1% долгих отключений
dt_values = dt_values[dt_values > 0]
plot_limit = np.percentile(dt_values, 99) 
dt_clean = dt_values[dt_values < plot_limit]

mean_dt_raw = np.mean(dt_clean)


# теоретическая кривая Пуассона
def exponential_pdf(x, lam):
    return lam * np.exp(-lam * x)

# Считаем фит с меньшим числом бинов для гладкости / бин - столбик, чем больше количество, тем меньше толщина отдельного
BINS_COUNT = 30
counts, edges = np.histogram(dt_clean, bins=BINS_COUNT, density=True)
bin_centers = (edges[:-1] + edges[1:]) / 2

try:
    p0 = [1.0 / mean_dt_raw]
    popt, _ = curve_fit(exponential_pdf, bin_centers, counts, p0=p0)
    lambda_rate = popt[0]
except Exception as e:
    print(f"Ошибка фитирования, используем грубое среднее: {e}")
    lambda_rate = 1.0 / mean_dt_raw

x_theory = np.linspace(0, max(dt_clean), 200)
y_theory = exponential_pdf(x_theory, lambda_rate)

# визуализация
plt.figure(figsize=(12, 6))

# Включаем стандартную светлую тему
plt.style.use('default')
ax = plt.gca()

# Сетка (теперь черная и полупрозрачная)
plt.grid(color='black', linestyle=':', alpha=0.15)

# Строим гистограмму чистых мюонов (фиолетовый отлично смотрится на белом)
plt.hist(dt_clean, bins=BINS_COUNT, density=True, 
         color='#8c56d2', alpha=0.8, edgecolor='black', linewidth=0.7, 
         label='Эксперимент (Δt мюонов)')

# Теоретическая кривая
plt.plot(x_theory, y_theory, color='#d62728', linewidth=3, 
         label=f'\nλ = {lambda_rate:.4f} Гц')

plt.title('Статистика Пуассона: Интервалы времени между мюонами', 
          fontsize=16, pad=15, fontweight='bold')
plt.xlabel('Интервал ожидания Δt (секунды)', fontsize=12)
plt.ylabel('Плотность вероятности', fontsize=12)

plt.xlim(0, max(dt_clean))

plt.legend(loc='upper right', facecolor='white', framealpha=1.0, edgecolor='gray', fontsize=11)

plt.tight_layout()
plt.show()


print("\n" + "="*45)
print(" ФИЗИЧЕСКИЙ ОТЧЕТ ВРЕМЕНИ (ПУАССОН)")
print("="*45)
print(f"Всего срабатываний детектора: {len(df)}")
print(f"Из них ИСТИННЫХ МЮОНОВ:       {len(df_muons)} (ADC > {THRESHOLD_ADC})")
print(f"Отфильтровано шума:           {len(df) - len(df_muons)} событий")
print("-" * 45)
print(f"Идеально подобранная λ:       {lambda_rate:.4f} Гц")
print(f"Среднее время ожидания:       {1.0/lambda_rate:.1f} сек")
print("="*45 + "\n")