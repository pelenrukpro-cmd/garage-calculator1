import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import io
from datetime import datetime

# ============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="🏗️ Профессиональный калькулятор гаража",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================================================
with st.sidebar:
    st.header("⚙️ Параметры здания")
    
    length = st.number_input("Длина гаража (м)", min_value=6.0, max_value=100.0, value=18.0, step=1.0)
    width = st.number_input("Ширина гаража (м)", min_value=3.0, max_value=30.0, value=10.0, step=1.0)
    height = st.number_input("Высота стен (м)", min_value=2.0, max_value=10.0, value=3.5, step=0.5)
    roof_pitch = st.number_input("Уклон крыши (%)", min_value=5, max_value=60, value=15, step=5)
    
    st.markdown("---")
    st.header("🌨️ Нагрузки")
    snow_region = st.selectbox("Снеговой район", ["I (0.8 кПа)", "II (1.2 кПа)", "III (1.8 кПа)", "IV (2.4 кПа)"], index=3)
    wind_region = st.selectbox("Ветровой район", ["I", "II", "III", "IV"], index=1)
    truss_step = st.slider("Шаг ферм (м)", 2.0, 6.0, 3.0, 0.5)
    
    st.markdown("---")
    st.header("🔩 Материалы")
    optimization = st.radio("Оптимизация", ["💰 Экономия", "⚖️ Баланс", "💪 Прочность"], index=1)

# ============================================================================
# РАСЧЁТНЫЕ ФУНКЦИИ
# ============================================================================

def calculate_structure(length, width, height, roof_pitch, truss_step, snow_region, optimization):
    """Расчёт всех параметров конструкции"""
    
    # Снеговая нагрузка
    snow_map = {"I (0.8 кПа)": 0.8, "II (1.2 кПа)": 1.2, "III (1.8 кПа)": 1.8, "IV (2.4 кПа)": 2.4}
    snow_load = snow_map.get(snow_region, 2.4)
    
    # Высота конька
    roof_height = height + (width / 2) * (roof_pitch / 100)
    truss_height = roof_height - height
    
    # Количество ферм
    num_trusses = int(length / truss_step) + 1
    
    # Нагрузки
    total_load = (snow_load + 0.3) * width * truss_step
    max_moment = total_load * width / 8
    
    # Коэффициенты оптимизации
    opt_factors = {
        "💰 Экономия": {"safety": 1.0, "section_factor": 0.9},
        "⚖️ Баланс": {"safety": 1.2, "section_factor": 1.0},
        "💪 Прочность": {"safety": 1.5, "section_factor": 1.2}
    }
    opt = opt_factors.get(optimization, {"safety": 1.2, "section_factor": 1.0})
    
    # Усилия в элементах фермы
    chord_force = max_moment / truss_height * opt["safety"] if truss_height > 0 else 100
    web_force = chord_force * 0.35
    post_force = total_load / 2 * opt["safety"]
    
    # Подбор сечений
    if optimization == "💰 Экономия":
        sections = {
            'top_chord': '80×80×3',
            'bottom_chord': '80×80×3',
            'web': '50×50×3',
            'posts': '80×80×3',
            'purlins': '60×40×3'
        }
    elif optimization == "💪 Прочность":
        sections = {
            'top_chord': '120×120×5',
            'bottom_chord': '120×120×5',
            'web': '80×80×4',
            'posts': '120×120×5',
            'purlins': '80×40×4'
        }
    else:  # Баланс
        sections = {
            'top_chord': '100×100×4',
            'bottom_chord': '100×100×4',
            'web': '60×60×3',
            'posts': '100×100×4',
            'purlins': '60×40×3'
        }
    
    # Расчёт напряжений (упрощённо)
    stress_chord = chord_force / 15.29 * opt["safety"]  # для 100×100×4
    stress_web = web_force / 6.69 * opt["safety"]  # для 60×60×3
    stress_post = post_force / 15.29 * opt["safety"]
    
    # Определение критических зон
    critical_elements = []
    if stress_chord > 245:
        critical_elements.append(("Пояса ферм", stress_chord, "red"))
    elif stress_chord > 200:
        critical_elements.append(("Пояса ферм", stress_chord, "yellow"))
    else:
        critical_elements.append(("Пояса ферм", stress_chord, "green"))
        
    if stress_post > 245:
        critical_elements.append(("Стойки", stress_post, "red"))
    elif stress_post > 200:
        critical_elements.append(("Стойки", stress_post, "yellow"))
    else:
        critical_elements.append(("Стойки", stress_post, "green"))
    
    return {
        'snow_load': snow_load,
        'roof_height': roof_height,
        'truss_height': truss_height,
        'num_trusses': num_trusses,
        'total_load': total_load,
        'chord_force': chord_force,
        'web_force': web_force,
        'post_force': post_force,
        'sections': sections,
        'stress_chord': stress_chord,
        'stress_web': stress_web,
        'stress_post': stress_post,
        'critical_elements': critical_elements,
        'optimization': optimization
    }

# ============================================================================
# 3D ВИЗУАЛИЗАЦИЯ ЗДАНИЯ
# ============================================================================

def create_building_3d(length, width, height, roof_pitch, truss_step, calc):
    """Создание 3D модели всего здания"""
    
    fig = go.Figure()
    
    num_trusses = calc['num_trusses']
    roof_height = calc['roof_height']
    
    # Цвета для элементов по напряжению
    stress_colors = {
        'red': '#FF0000',
        'yellow': '#FFA500',
        'green': '#00FF00',
        'blue': '#0066CC'
    }
    
    # Определение цветов для элементов
    chord_color = stress_colors.get(
        next((c[2] for c in calc['critical_elements'] if 'Пояса' in c[0]), 'green'),
        '#A23B72'
    )
    post_color = stress_colors.get(
        next((c[2] for c in calc['critical_elements'] if 'Стойки' in c[0]), 'green'),
        '#2E86AB'
    )
    
    # Стойки
    for i in range(num_trusses):
        x = i * truss_step
        # Левая стойка
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, 0], z=[0, height],
            mode='lines',
            line=dict(color=post_color, width=8),
            name='Стойки' if i == 0 else '',
            showlegend=(i==0)
        ))
        # Правая стойка
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[width, width], z=[0, height],
            mode='lines',
            line=dict(color=post_color, width=8),
            showlegend=False
        ))
    
    # Фермы (исправленные - не диагональные!)
    for i in range(num_trusses):
        x = i * truss_step
        
        # Левая половина фермы (правильная геометрия)
        fig.add_trace(go.Scatter3d(
            x=[x, x],
            y=[0, width/2],
            z=[height, roof_height],
            mode='lines',
            line=dict(color=chord_color, width=6),
            name='Фермы' if i == 0 else '',
            showlegend=(i==0)
        ))
        
        # Правая половина фермы
        fig.add_trace(go.Scatter3d(
            x=[x, x],
            y=[width/2, width],
            z=[roof_height, height],
            mode='lines',
            line=dict(color=chord_color, width=6),
            showlegend=False
        ))
        
        # Нижний пояс фермы
        fig.add_trace(go.Scatter3d(
            x=[x, x],
            y=[0, width],
            z=[height, height],
            mode='lines',
            line=dict(color=chord_color, width=5, dash='dash'),
            showlegend=False
        ))
        
        # Вертикальные элементы фермы (раскосы)
        for j in range(4):
            y_pos = j * width / 4
            fig.add_trace(go.Scatter3d(
                x=[x, x],
                y=[y_pos, y_pos],
                z=[height, height + (roof_height - height) * (j / 4)],
                mode='lines',
                line=dict(color='#888888', width=3),
                showlegend=False
            ))
    
    # Прогоны (горизонтальные балки)
    purlin_y = [width/6, width/3, width/2, 2*width/3, 5*width/6]
    for j, y_pos in enumerate(purlin_y):
        if y_pos <= width / 2:
            z_pos = height + y_pos * (roof_pitch / 100)
        else:
            z_pos = height + (width - y_pos) * (roof_pitch / 100)
        
        fig.add_trace(go.Scatter3d(
            x=[0, length],
            y=[y_pos, y_pos],
            z=[z_pos, z_pos],
            mode='lines',
            line=dict(color='#F18F01', width=4),
            name='Прогоны' if j == 0 else '',
            showlegend=(j==0)
        ))
    
    # Настройка сцены
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Длина (м)', range=[0, length]),
            yaxis=dict(title='Ширина (м)', range=[0, width]),
            zaxis=dict(title='Высота (м)', range=[0, roof_height + 2]),
            aspectmode='manual',
            aspectratio=dict(x=2, y=1, z=0.8),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        height=600,
        showlegend=True,
        margin=dict(l=0, r=0, t=50, b=0),
        title=dict(
            text="️ 3D Модель каркаса гаража",
            x=0.5,
            font=dict(size=20)
        )
    )
    
    return fig

# ============================================================================
# 3D ВИЗУАЛИЗАЦИЯ ФЕРМЫ (ОТДЕЛЬНО)
# ============================================================================

def create_truss_detail_3d(width, height, roof_height, calc):
    """Детальная 3D модель одной фермы с узлами"""
    
    fig = go.Figure()
    
    truss_height = roof_height - height
    
    # Пояса фермы
    # Нижний пояс
    fig.add_trace(go.Scatter3d(
        x=[0, width],
        y=[0, 0],
        z=[0, 0],
        mode='lines',
        line=dict(color='#2E86AB', width=8),
        name='Нижний пояс'
    ))
    
    # Верхний пояс (левая половина)
    fig.add_trace(go.Scatter3d(
        x=[0, width/2],
        y=[0, 0],
        z=[0, truss_height],
        mode='lines',
        line=dict(color='#A23B72', width=8),
        name='Верхний пояс'
    ))
    
    # Верхний пояс (правая половина)
    fig.add_trace(go.Scatter3d(
        x=[width/2, width],
        y=[0, 0],
        z=[truss_height, 0],
        mode='lines',
        line=dict(color='#A23B72', width=8),
        showlegend=False
    ))
    
    # Вертикальные стойки фермы
    for i in range(5):
        x_pos = i * width / 4
        z_top = min(x_pos, width - x_pos) / (width / 2) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x_pos, x_pos],
            y=[0, 0],
            z=[0, z_top],
            mode='lines',
            line=dict(color='#888888', width=5),
            name='Стойки' if i == 0 else '',
            showlegend=(i==0)
        ))
    
    # Раскосы (диагональные элементы)
    for i in range(4):
        x1 = i * width / 4
        x2 = (i + 1) * width / 4
        z1 = min(x1, width - x1) / (width / 2) * truss_height
        z2 = min(x2, width - x2) / (width / 2) * truss_height
        
        # Чередование направления раскосов
        if i % 2 == 0:
            fig.add_trace(go.Scatter3d(
                x=[x1, x2],
                y=[0, 0],
                z=[z1, 0],
                mode='lines',
                line=dict(color='#F18F01', width=4),
                name='Раскосы' if i == 0 else '',
                showlegend=(i==0)
            ))
        else:
            fig.add_trace(go.Scatter3d(
                x=[x1, x2],
                y=[0, 0],
                z=[0, z2],
                mode='lines',
                line=dict(color='#F18F01', width=4),
                showlegend=False
            ))
    
    # Узлы крепления (сферы в точках соединения)
    node_x = [0, width/4, width/2, 3*width/4, width]
    node_z = [0, truss_height/2, truss_height, truss_height/2, 0]
    
    fig.add_trace(go.Scatter3d(
        x=node_x,
        y=[0] * 5,
        z=node_z,
        mode='markers',
        marker=dict(
            size=8,
            color='#FF0000',
            opacity=0.8
        ),
        name='Узлы крепления'
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Ширина (м)', range=[0, width]),
            yaxis=dict(title='Глубина (м)', range=[-1, 1]),
            zaxis=dict(title='Высота (м)', range=[0, truss_height + 1]),
            aspectmode='manual',
            aspectratio=dict(x=2, y=0.3, z=1)
        ),
        height=400,
        showlegend=True,
        margin=dict(l=0, r=0, t=50, b=0),
        title=dict(
            text="🔩 Детальная модель фермы с узлами",
            x=0.5,
            font=dict(size=18)
        )
    )
    
    return fig

# ============================================================================
# ГЕНЕРАЦИЯ ЧЕРТЕЖЕЙ (PDF/DXF)
# ============================================================================

def generate_drawing_data(length, width, height, calc):
    """Генерация данных для чертежей"""
    
    # Чертёж фермы
    truss_drawing = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                          ФЕРМА СТРОПИЛЬНАЯ                                ║
║                          Размер: {width:.1f}м × {(calc['roof_height']-height):.2f}м                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║                    /\                                                    ║
║                   /  \   Верхний пояс: {calc['sections']['top_chord']} мм                 ║
║                  /    \                                                  ║
║                 /      \                                                 ║
║                /        \                                                ║
║               /          \                                               ║
║              /____________\                                              ║
║              ←  {width:.1f}м  →                                           ║
║              Нижний пояс: {calc['sections']['bottom_chord']} мм                            ║
║                                                                          ║
║  МАТЕРИАЛЫ:                                                              ║
║  • Пояса: {calc['sections']['top_chord']} мм (сталь С345)                             ║
║  • Раскосы: {calc['sections']['web']} мм                                              ║
║  • Стойки: {calc['sections']['posts']} мм                                             ║
║                                                                          ║
║  НАГРУЗКИ:                                                               ║
║  • Усилие в поясах: {calc['chord_force']:.1f} кН                                      ║
║  • Усилие в раскосах: {calc['web_force']:.1f} кН                                      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    
    # Таблица материалов для всего здания
    total_chord_length = width * 2 * calc['num_trusses']
    total_post_length = height * 2 * calc['num_trusses']
    total_purlin_length = length * 5
    
    materials_table = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                     ВЕДОМОСТЬ МАТЕРИАЛОВ                                  ║
║                     Гараж {length}м × {width}м × {height}м                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║ № │ Наименование      │ Сечение      │ Длина, м │ Кол-во │ Масса, кг  ║
╠══════════════════════════════════════════════════════════════════════════╣
║ 1 │ Пояса ферм        │ {calc['sections']['top_chord']:>10} │ {total_chord_length:6.1f} │      1 │     0.0 │ ║
║ 2 │ Стойки            │ {calc['sections']['posts']:>10} │ {total_post_length:6.1f} │      1 │     0.0 │ ║
║ 3 │ Прогоны           │ {calc['sections']['purlins']:>10} │ {total_purlin_length:6.1f} │      1 │     0.0 │ ║
║ 4 │ Раскосы ферм      │ {calc['sections']['web']:>10} │ {width*calc['num_trusses']*4:6.1f} │      1 │     0.0 │ ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ИТОГО:                                                                  ║
║  • Общая длина профиля: {total_chord_length + total_post_length + total_purlin_length:.1f} м                       ║
║  • Снеговая нагрузка: {calc['snow_load']} кПа                                         ║
║  • Количество ферм: {calc['num_trusses']} шт.                                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    
    # Узлы крепления
    nodes_drawing = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                          УЗЛЫ КРЕПЛЕНИЯ                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  УЗЕЛ 1: Крепление стойки к фундаменту                                  ║
║  ┌─────────┐                                                            ║
║  │         │  ← Профильная труба {calc['sections']['posts']}                            ║
║  │    ██   │                                                            ║
║  │    ██   │                                                            ║
║  └────┬┬───┘                                                            ║
║       ││                                                                  ║
║  ─────┴┴─────  ← Фундаментная плита                                    ║
║       ||                                                                  ║
║       ||  ← Анкерные болты M16                                          ║
║                                                                          ║
║  УЗЕЛ 2: Соединение поясов фермы                                        ║
║     /\                                                                   ║
║    /  \   ← Сварной шов 6 мм                                           ║
║   /____\                                                                 ║
║   {calc['sections']['top_chord']} + {calc['sections']['bottom_chord']}                                           ║
║                                                                          ║
║  УЗЕЛ 3: Крепление прогонов к ферме                                     ║
║   ┌─────┐  ← Прогон {calc['sections']['purlins']}                                        ║
║   │#####│                                                                ║
║   └──┬──┘                                                                  ║
║      │  ← Болт М12                                                        ║
║   ───┴───  ← Пояс фермы {calc['sections']['top_chord']}                                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    
    return truss_drawing, materials_table, nodes_drawing

# ============================================================================
# CSV ЭКСПОРТ
# ============================================================================

def generate_csv(length, width, height, calc):
    """Генерация CSV файлов с данными"""
    
    # Таблица ферм
    trusses_df = pd.DataFrame({
        '№ фермы': range(1, calc['num_trusses'] + 1),
        'Позиция_X_m': [i * truss_step for i in range(calc['num_trusses'])],
        'Ширина_m': [width] * calc['num_trusses'],
        'Высота_m': [calc['truss_height']] * calc['num_trusses'],
        'Верхний_пояс': [calc['sections']['top_chord']] * calc['num_trusses'],
        'Нижний_пояс': [calc['sections']['bottom_chord']] * calc['num_trusses'],
        'Раскосы': [calc['sections']['web']] * calc['num_trusses'],
        'Усилие_в_поясах_кН': [calc['chord_force']] * calc['num_trusses'],
        'Напряжение_МПа': [calc['stress_chord']] * calc['num_trusses']
    })
    
    # Таблица материалов
    materials_df = pd.DataFrame({
        'Элемент': ['Пояса ферм', 'Стойки', 'Прогоны', 'Раскосы'],
        'Сечение_мм': [calc['sections']['top_chord'], calc['sections']['posts'], 
                       calc['sections']['purlins'], calc['sections']['web']],
        'Длина_м': [width * 2 * calc['num_trusses'], height * 2 * calc['num_trusses'],
                    length * 5, width * calc['num_trusses'] * 4],
        'Количество': [calc['num_trusses'] * 2, calc['num_trusses'] * 2,
                       5, calc['num_trusses'] * 4],
        'Напряжение_МПа': [calc['stress_chord'], calc['stress_post'], 
                           calc['stress_web'], calc['stress_web']]
    })
    
    # Таблица нагрузок
    loads_df = pd.DataFrame({
        'Тип нагрузки': ['Снеговая', 'Собственный вес', 'Ветровая', 'Итого'],
        'Значение_кПа': [calc['snow_load'], 0.3, 0.23, calc['snow_load'] + 0.53],
        'Нагрузка_на_ферму_кН': [calc['snow_load'] * width * truss_step,
                                  0.3 * width * truss_step,
                                  0.23 * width * truss_step,
                                  calc['total_load']]
    })
    
    return trusses_df, materials_df, loads_df

# ============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС
# ============================================================================

st.title("🏗️ Профессиональный калькулятор каркаса гаража")
st.markdown("**Расчёт ферм, нагрузок и подбор сечений с визуализацией** 📐")

# Расчёт
calc = calculate_structure(length, width, height, roof_pitch, truss_step, snow_region, optimization)

# Метрики
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("❄️ Снеговая нагрузка", f"{calc['snow_load']} кПа", f"~{calc['snow_load']*100:.0f} кг/м²")
with col2:
    st.metric("🏗️ Нагрузка на ферму", f"{calc['total_load']:.1f} кН", f"~{calc['total_load']*100:.0f} кг")
with col3:
    st.metric("📐 Высота конька", f"{calc['roof_height']:.2f} м")
with col4:
    st.metric("🔩 Количество ферм", f"{calc['num_trusses']} шт")

st.markdown("---")

# 3D модель здания
st.subheader("🏢 3D Модель всего здания")
fig_building = create_building_3d(length, width, height, roof_pitch, truss_step, calc)
st.plotly_chart(fig_building, use_container_width=True)

# 3D модель фермы
st.subheader("🔧 Детальная 3D модель фермы")
fig_truss = create_truss_detail_3d(width, height, calc['roof_height'], calc)
st.plotly_chart(fig_truss, use_container_width=True)

# Анализ напряжений
st.markdown("---")
st.subheader("🔍 Анализ напряжений в элементах")

# Цветовая индикация
def get_color_html(stress):
    if stress > 245:
        return f"<span style='color:red; font-weight:bold'>🔴 {stress:.1f} МПа (КРИТИЧНО!)</span>"
    elif stress > 200:
        return f"<span style='color:orange'>🟡 {stress:.1f} МПа (Повышенное)</span>"
    else:
        return f"<span style='color:green'>🟢 {stress:.1f} МПа (Норма)</span>"

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Пояса ферм:**<br>{get_color_html(calc['stress_chord'])}", unsafe_allow_html=True)
with col2:
    st.markdown(f"**Раскосы:**<br>{get_color_html(calc['stress_web'])}", unsafe_allow_html=True)
with col3:
    st.markdown(f"**Стойки:**<br>{get_color_html(calc['stress_post'])}", unsafe_allow_html=True)

# Критические элементы
if any(elem[2] == 'red' for elem in calc['critical_elements']):
    st.error("⚠️ **ВНИМАНИЕ:** Обнаружены критические напряжения! Рекомендуется увеличить сечение элементов.")

st.markdown("---")

# Рекомендуемые сечения
st.subheader("🔩 Рекомендуемые сечения элементов")

st.markdown(f"""
**Для ферм:**
• Верхний пояс: профильная труба **{calc['sections']['top_chord']} мм** (сталь С345)
• Нижний пояс: профильная труба **{calc['sections']['bottom_chord']} мм**
• Раскосы: профильная труба **{calc['sections']['web']} мм**
• Стойки фермы: профильная труба **{calc['sections']['posts']} мм**

**Для прогонов:**
• Труба **{calc['sections']['purlins']} мм**
• Шаг: 1.5-2.0 м

**Для стоек здания:**
• Труба **{calc['sections']['posts']} мм** минимум
• При высоте >4м: **120×120×5 мм**
""")

# Альтернативные варианты
st.markdown("---")
st.subheader("💡 Альтернативные варианты оптимизации")

if optimization != "💰 Экономия":
    st.info("""
**💰 Вариант "Экономия":**
• Сечения: 80×80×3 (пояса), 50×50×3 (раскосы)
• Экономия металла: ~25%
• Подходит для: снеговых районов I-II
""")

if optimization != "💪 Прочность":
    st.success("""
**💪 Вариант "Прочность":**
• Сечения: 120×120×5 (пояса), 80×80×4 (раскосы)
• Запас прочности: +50%
• Рекомендуется для: снеговых районов III-IV, больших пролётов
""")

st.markdown("---")

# Экспорт данных
st.subheader("💾 Экспорт проектной документации")

# Генерация чертежей
truss_drawing, materials_table, nodes_drawing = generate_drawing_data(length, width, height, calc)
trusses_df, materials_df, loads_df = generate_csv(length, width, height, calc)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.download_button(
        label="📐 Чертёж фермы (TXT)",
        data=truss_drawing,
        file_name=f"truss_drawing_{width}m.txt",
        mime="text/plain",
        use_container_width=True
    )

with col2:
    st.download_button(
        label="📋 Ведомость материалов (TXT)",
        data=materials_table,
        file_name=f"materials_{length}x{width}m.txt",
        mime="text/plain",
        use_container_width=True
    )

with col3:
    st.download_button(
        label="🔩 Узлы крепления (TXT)",
        data=nodes_drawing,
        file_name="connection_nodes.txt",
        mime="text/plain",
        use_container_width=True
    )

with col4:
    # CSV файлы
    csv_zip = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(csv_zip, 'w') as zip_file:
        zip_file.writestr("trusses.csv", trusses_df.to_csv(index=False, sep=';', decimal=','))
        zip_file.writestr("materials.csv", materials_df.to_csv(index=False, sep=';', decimal=','))
        zip_file.writestr("loads.csv", loads_df.to_csv(index=False, sep=';', decimal=','))
    
    st.download_button(
        label="📊 Все таблицы (ZIP)",
        data=csv_zip.getvalue(),
        file_name=f"garage_tables_{length}x{width}m.zip",
        mime="application/zip",
        use_container_width=True
    )

# Отдельные CSV
st.markdown("**Или скачайте отдельно:**")
col1, col2, col3 = st.columns(3)

with col1:
    st.download_button(
        label="📄 Таблица ферм (CSV)",
        data=trusses_df.to_csv(index=False, sep=';', decimal=','),
        file_name="trusses.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    st.download_button(
        label="📄 Таблица материалов (CSV)",
        data=materials_df.to_csv(index=False, sep=';', decimal=','),
        file_name="materials.csv",
        mime="text/csv",
        use_container_width=True
    )

with col3:
    st.download_button(
        label="📄 Таблица нагрузок (CSV)",
        data=loads_df.to_csv(index=False, sep=';', decimal=','),
        file_name="loads.csv",
        mime="text/csv",
        use_container_width=True
    )

# Предупреждение
st.markdown("---")
st.warning("""
⚠️ **ВАЖНО:** Данный расчёт является предварительным и не заменяет проектную документацию.
Для строительства необходимо:
1. Обратиться к лицензированному проектировщику
2. Выполнить полный расчёт по СП 16.13330.2017 и СП 20.13330.2016
3. Получить экспертизу проекта
""")

# Footer
st.markdown(f"""
<div style='text-align: center; color: gray; margin-top: 50px; padding: 20px; border-top: 1px solid #ddd;'>
<strong>🏗️ Garage Calculator Professional v3.0</strong><br>
Дата расчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')} | 
Размеры: {length}м × {width}м × {height}м | 
Оптимизация: {optimization}
</div>
""", unsafe_allow_html=True)
