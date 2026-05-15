import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from scipy.optimize import curve_fit

V_REF = 1100.0      # Опорное напряжение АЦП (мВ)
ADC_RES = 4095.0    # Максимальное значение АЦП (12 бит)
E_MIP = 2.62        # Теоретическая энергия пика Ландау (МэВ)

print("Загрузка файла и обработка данных...")
df = pd.read_csv('1-2-3-4-5-6-7may.csv', names=['time', 'adc_value'])

df['time'] = pd.to_numeric(df['time'], errors='coerce')
df['adc_value'] = pd.to_numeric(df['adc_value'], errors='coerce')
df = df.dropna(subset=['time', 'adc_value']).reset_index(drop=True)

df['voltage_mv'] = df['adc_value'] * (V_REF / ADC_RES)

HARDCODED_ADC_THRESH = 1341.0 
noise_threshold_mv = HARDCODED_ADC_THRESH * (V_REF / ADC_RES)

mask_noise = df['voltage_mv'] <= noise_threshold_mv
mask_muon = (df['voltage_mv'] > noise_threshold_mv) & (df['adc_value'] < 4095)
mask_outlier = df['adc_value'] >= 4095

muon_data_mv = df[mask_muon]['voltage_mv']

if len(muon_data_mv) < 20:
    print("Ошибка: Слишком мало событий для калибровки!")
    exit()

kde_calib = gaussian_kde(muon_data_mv, bw_method=0.2)
x_test = np.linspace(muon_data_mv.min(), muon_data_mv.max(), 1000)
peak_mv = x_test[np.argmax(kde_calib(x_test))]

K_calib = E_MIP / peak_mv

df['energy_mev'] = df['voltage_mv'] * K_calib
threshold_mev = noise_threshold_mv * K_calib
MAX_MEV = 4095.0 * (V_REF / ADC_RES) * K_calib

BINS_COUNT = 120 
global_bins = np.linspace(0, MAX_MEV, BINS_COUNT)
bin_width = global_bins[1] - global_bins[0]

muon_energies = df[mask_muon]['energy_mev']

hist_y, edges = np.histogram(muon_energies, bins=global_bins)
hist_x = (edges[:-1] + edges[1:]) / 2

def true_landau_tail(x, amp, width):
    t = x - E_MIP + (width / 2.0)
    val = np.zeros_like(x)
    mask = t > 0
    val[mask] = amp * (1.0 / t[mask]**2) * np.exp(-width / t[mask])
    return val

# Теория строится строго по правой части
valid_idx = (hist_x >= E_MIP) & (hist_y > 0)
hist_x_fit = hist_x[valid_idx]
hist_y_fit = hist_y[valid_idx]

try:
    amp_guess = np.max(hist_y_fit) * 2.0 
    p0 = [amp_guess, 1.0]
    bounds = ([0, 0.1], [np.inf, 20.0])
    
    popt, _ = curve_fit(true_landau_tail, hist_x_fit, hist_y_fit, p0=p0, bounds=bounds)
    fit_success = True
except Exception as e:
    print(f"Ошибка фита: {e}")
    fit_success = False

plt.figure(figsize=(14, 8))
plt.style.use('default')
ax = plt.gca()
fig = plt.gcf()
ax.set_facecolor('white')
fig.patch.set_facecolor('white')

plt.grid(color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

plt.hist(df[mask_noise]['energy_mev'], bins=global_bins,
         color='#ff4d4d', alpha=0.7, edgecolor='none', label='Шум (Темновой ток + Гамма-фон)')

plt.hist(muon_energies, bins=global_bins, histtype='stepfilled', 
         color='#00bfff', alpha=0.8, edgecolor='cyan', linewidth=1.0, label='Мюоны (Сигнал)')

if mask_outlier.sum() > 0:
    plt.hist(df[mask_outlier]['energy_mev'], bins=1, range=(MAX_MEV*0.98, MAX_MEV*1.02), 
             color='#ffa500', alpha=0.9, label='Насыщение АЦП')

kde_energy = gaussian_kde(muon_energies, bw_method=0.25) 
x_env = np.linspace(threshold_mev, MAX_MEV, 500)  
y_env = kde_energy(x_env) * len(muon_energies) * bin_width
plt.plot(x_env, y_env, color='black', linewidth=3.0, label='Сглаженный спектр мюонов')

if fit_success:
    x_theory = np.linspace(0, MAX_MEV, 1000) 
    y_fit = true_landau_tail(x_theory, *popt)
    plt.plot(x_theory, y_fit, color='orange', linewidth=3.5, linestyle='--', 
             label='Теоретический Ландау (расчет по хвосту)')

plt.axvline(x=threshold_mev, color='#ffcc00', linestyle=':', linewidth=2.5)
plt.axvline(x=E_MIP, color='lime', linestyle='--', linewidth=2.5)
plt.axvline(x=MAX_MEV, color='red', linestyle='-.', linewidth=1.5, alpha=0.5)

trans = ax.get_xaxis_transform()
plt.text(threshold_mev - 0.1, 0.4, f'Порог регистрации\n({threshold_mev:.2f} МэВ)', color='#cc9900', fontsize=12, ha='right', transform=trans)
plt.text(E_MIP + 0.1, 0.7, f'Пик Ландау\n({E_MIP} МэВ)', color='green', fontsize=12, transform=trans)
plt.text(MAX_MEV - 0.1, 0.3, f'Предел АЦП\n({MAX_MEV:.1f} МэВ)', color='red', fontsize=12, ha='right', transform=trans)

plt.title('Энергетический спектр: Разделение шума и мюонного сигнала', fontsize=16, pad=15, fontweight='bold')
plt.xlabel('Энергия (МэВ)', fontsize=14)
plt.ylabel('Количество событий', fontsize=14)

plt.xlim(0, MAX_MEV * 1.05) 
plt.ylim(bottom=0) 

legend = plt.legend(loc='upper right', facecolor='white', edgecolor='black', fontsize=11, framealpha=0.9)
plt.tight_layout()
plt.show()

print("\n" + "="*55)
print(" ФИЗИЧЕСКИЙ ОТЧЕТ ЭКСПЕРИМЕНТА")
print("="*55)
print(f"Порог шума (Аппаратный): {threshold_mev:.2f} МэВ")
print(f"Пик (V_peak):            {peak_mv:.1f} мВ")
print(f"Калибровочный коэф.:     {K_calib:.4f} МэВ/мВ")
print(f"Макс. видимая энергия:   {MAX_MEV:.2f} МэВ (Предел АЦП)")
print("-" * 55)
print("="*55 + "\n")