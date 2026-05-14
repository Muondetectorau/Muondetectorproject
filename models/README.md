# Космические мюоны: Монте-Карло симуляция 

Интерактивная физическая симуляция прохождения космических мюонов через вещество и калибровка сцинтилляционного детектора.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://muondetector.streamlit.app/)

![Скриншот приложения](https://github.com/Muondetectorau/Muondetectorproject/blob/main/models/muon_simulation_live.gif) 

## Что внутри:
-  Честный Монте-Карло движок (Ray-marching) потерь энергии по формуле Бете-Блоха.
-  Моделирование спектра Ландау в тонких пластиковых сцинтилляторах.
-  Оптимизация соотношения Сигнал/Шум при наличии радиационного фона.
-  Анализ статистики Пуассона и барометрического эффекта.

## Как запустить:
1. Установите зависимости: `pip install -r requirements.txt`
2. Запустите веб-интерфейс: `streamlit run web_app.py`