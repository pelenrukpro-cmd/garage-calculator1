import streamlit as st
import plotly.graph_objects as go
import numpy as np

# Настройка страницы
st.set_page_config(page_title="🏗️ Гараж Калькулятор", layout="wide")

# Заголовок
st.title("🏗️ Калькулятор гаража")
st.markdown("**Расчёт ферм и нагрузок** 📐")

# Боковая панель
with st.sidebar:
    st.header("⚙️ Параметры")
    
    length = st.number_input("Длина гаража (м)", min_value=5.0, max_value=100.0, value=30.0, step=1.0)
    width = st.number_input("Ширина гаража (м)", min_value=3.0, max_value=30.0, value=10.0, step=1.0)
    height = st.number_input("Высота стен (м)", min_value=2.0, max_value=10.0, value=3.5, step=0.5)
    roof_pitch = st.number_input("Уклон крыши (%)", min_value=5, max_value=60, value=15, step=5)
    
    st.subheader("🌨️ Нагрузки")
    snow_region = st.selectbox("Снеговой район", ["I (0.8 кПа)", "II (1.2 кПа)", "III (1.8 кПа)", "IV (2.4 кПа)"], index=3)
    truss_step = st.slider("Шаг ферм (м)", 2.0, 6.0, 4.0, 0.5)

# Расчёт нагрузок
snow_map = {"I (0.8 кПа)": 0.8, "II (1.2 кПа)": 1.2, "III (1.8 кПа)": 1.8, "IV (2.4 кПа)": 2.4}
snow_load = snow_map.get(snow_region, 2.4)

# Общая нагрузка на одну ферму
total_load = (snow_load + 0.3) * width * truss_step  # снег + собственный вес
roof_height = height + (width / 2) * (roof_pitch / 100)

# Отображение метрик
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("❄️ Снеговая нагрузка", f"{snow_load} кПа", f"~{snow_load*100:.0f} кг/м²")
with col2:
    st.metric("🏗️ Нагрузка на ферму", f"{total_load:.1f} кН", f"~{total_load*100:.0f} кг")
with col3:
    st.metric("📐 Высота конька", f"{roof_height:.2f} м")
with col4:
    st.metric("📏 Площадь кровли", f"{length * width * 1.1:.1f} м²")

st.markdown("---")

# 3D визуализация
st.subheader("📐 3D Модель каркаса")

fig = go.Figure()

# Количество ферм
num_trusses = int(length / truss_step) + 1

# Стойки
for i in range(num_trusses):
    x = i * truss_step
    # Левая стойка
    fig.add_trace(go.Scatter3d(
        x=[x, x], y=[0, 0], z=[0, height],
        mode='lines', line=dict(color='#2E86AB', width=5),
        name='Стойки' if i == 0 else ''
    ))
    # Правая стойка
    fig.add_trace(go.Scatter3d(
        x=[x, x], y=[width, width], z=[0, height],
        mode='lines', line=dict(color='#2E86AB', width=5),
        showlegend=False
    ))

# Фермы (треугольные)
for i in range(num_trusses):
    x = i * truss_step
    fig.add_trace(go.Scatter3d(
        x=[x, x + width/2, x + width],
        y=[0, width/2, width],
        z=[height, roof_height, height],
        mode='lines', line=dict(color='#A23B72', width=4),
        name='Фермы' if i == 0 else ''
    ))

# Прогоны (горизонтальные балки)
for j in range(5):
    y_pos = (j + 1) * width / 6
    z_pos = height + min(y_pos, width - y_pos) * (roof_pitch / 100)
    fig.add_trace(go.Scatter3d(
        x=[0, length], y=[y_pos, y_pos], z=[z_pos, z_pos],
        mode='lines', line=dict(color='#F18F01', width=3),
        name='Прогоны' if j == 0 else ''
    ))

fig.update_layout(
    scene=dict(
        xaxis=dict(title='Длина (м)', range=[0, length]),
        yaxis=dict(title='Ширина (м)', range=[0, width]),
        zaxis=dict(title='Высота (м)', range=[0, roof_height + 2]),
        aspectmode='manual',
        aspectratio=dict(x=2, y=1, z=0.8)
    ),
    height=500,
    showlegend=True,
    margin=dict(l=0, r=0, t=0, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# Рекомендации по сечениям
st.subheader("🔩 Рекомендуемые сечения")

# Простой расчёт
chord_force = total_load * width / 8 / (roof_height - height) if roof_height > height else 10

st.markdown("""
**Для ферм:**
- Пояса: профильная труба **100×100×4 мм** (сталь С345)
- Раскосы: профильная труба **60×60×3 мм**
- Стойки: профильная труба **100×100×4-5 мм**

**Для прогонов:**
- Труба **60×40×3 мм** или **80×40×3 мм**
- Шаг: 1.5-2.0 м

**Для стоек:**
- Труба **100×100×4 мм** минимум
- При высоте >4м: **120×120×5 мм**
""")

# Экспорт данных
st.subheader("💾 Экспорт")

csv_data = f"""Параметры гаража:
Длина: {length} м
Ширина: {width} м
Высота: {height} м
Уклон крыши: {roof_pitch}%

Нагрузки:
Снеговая нагрузка: {snow_load} кПа
Нагрузка на ферму: {total_load:.1f} кН
Высота конька: {roof_height:.2f} м
Количество ферм: {num_trusses} шт
"""

st.download_button(
    label="📥 Скачать расчёт (TXT)",
    data=csv_data,
    file_name=f"garage_calc_{length}x{width}m.txt",
    mime="text/plain"
)

# Предупреждение
st.markdown("---")
st.warning("⚠️ **ВАЖНО:** Это предварительный расчёт. Для строительства необходим полный проект по СП 16.13330 и СП 20.13330.")

st.markdown("""
<div style='text-align: center; color: gray; margin-top: 50px;'>
🏗️ Garage Calculator v2.0 | 2026
</div>
""", unsafe_allow_html=True)