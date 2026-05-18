import dearpygui.dearpygui as dpg


# ==========================================
# 核心计算逻辑 (完全保留你的原始算法)
# ==========================================
def calculate_combustion_logic(power_watts, phi, h2_pct):
    h2_vol_fraction = h2_pct / 100.0

    # 1. 物理常数定义
    M_CH4 = 16.04
    M_H2 = 2.016
    M_O2 = 32.00
    M_N2 = 28.013
    LHV_CH4 = 50.0e6  # 50 MJ/kg
    LHV_H2 = 120.0e6  # 120 MJ/kg
    Y_O2_air = 0.233
    Vm_STP = 24.465
    rho_air_25C = 1.184

    # 2. 燃料物性计算
    ch4_vol_fraction = 1.0 - h2_vol_fraction
    M_fuel_mix = (ch4_vol_fraction * M_CH4) + (h2_vol_fraction * M_H2)
    Y_CH4_fuel = (ch4_vol_fraction * M_CH4) / M_fuel_mix
    Y_H2_fuel = (h2_vol_fraction * M_H2) / M_fuel_mix
    LHV_mix = (Y_CH4_fuel * LHV_CH4) + (Y_H2_fuel * LHV_H2)

    # 3. 流量计算
    m_dot_fuel = power_watts / LHV_mix
    moles_O2_needed = (ch4_vol_fraction * 2.0) + (h2_vol_fraction * 0.5)
    mass_O2_needed = moles_O2_needed * M_O2
    OFR_st = mass_O2_needed / M_fuel_mix
    AFR_st = OFR_st / Y_O2_air
    AFR_actual = AFR_st / phi
    m_dot_air = m_dot_fuel * AFR_actual
    m_dot_total = m_dot_fuel + m_dot_air

    # 4. 混合后总组分
    mass_CH4 = m_dot_fuel * Y_CH4_fuel
    mass_H2 = m_dot_fuel * Y_H2_fuel
    mass_O2 = m_dot_air * Y_O2_air
    mass_N2 = m_dot_air * (1.0 - Y_O2_air)

    Y_CH4_total = mass_CH4 / m_dot_total
    Y_H2_total = mass_H2 / m_dot_total
    Y_O2_total = mass_O2 / m_dot_total
    Y_N2_total = mass_N2 / m_dot_total

    # 5. SLPM 换算
    slpm_fuel = (m_dot_fuel * 1000 / M_fuel_mix) * Vm_STP * 60
    slpm_ch4 = slpm_fuel * ch4_vol_fraction
    slpm_h2 = slpm_fuel * h2_vol_fraction

    vol_flow_air_25C = m_dot_air / rho_air_25C
    slpm_air = vol_flow_air_25C * 1000 * 60

    # 6. 构建输出文本
    lines = []
    lines.append("=" * 50)
    lines.append(f"【工况】功率: {power_watts}W | Phi: {phi} | H2比例: {h2_pct}%")
    lines.append("=" * 50)
    lines.append("\n[Fluent 边界条件 - Mass Flow Rate (kg/s)]")
    lines.append(f"   Fuel Inlet: {m_dot_fuel:.4e}")
    lines.append(f"       >> CH4: {mass_CH4:.4e}")
    if h2_vol_fraction > 0:
        lines.append(f"       >> H2 : {mass_H2:.4e}")
    lines.append(f"   Air Inlet : {m_dot_air:.4e}")
    lines.append(f"   Total Flow: {m_dot_total:.4e}")

    lines.append("\n[Fluent 组分 - Mass Fraction]")
    lines.append(f"   CH4: {Y_CH4_total:.5f}")
    lines.append(f"   H2 : {Y_H2_total:.5f}")
    lines.append(f"   O2 : {Y_O2_total:.5f}")
    lines.append(f"   N2 : {Y_N2_total:.5f}")

    lines.append("\n[实验流量计设置]")
    lines.append(f"   Air (25℃, 1atm): {slpm_air:.2f} L/min")
    lines.append(f"   CH4 (STP):       {slpm_ch4:.2f} SLPM")
    if h2_vol_fraction > 0:
        lines.append(f"   H2  (STP):       {slpm_h2:.2f} SLPM")

    return "\n".join(lines)


# ==========================================
# UI 交互回调函数
# ==========================================
def set_status(msg, color=(150, 150, 150)):
    """更新底部状态栏文本和颜色"""
    dpg.set_value("status_text", msg)
    dpg.configure_item("status_text", color=color)


def run_calculation():
    # 获取输入值
    p_val = dpg.get_value("input_power")
    phi_val = dpg.get_value("input_phi")
    h2_val = dpg.get_value("input_h2")

    # 简单验证 (替代 Tkinter 的 messagebox)
    if p_val <= 0 or phi_val <= 0:
        set_status("❌ 输入错误：功率和当量比必须大于0", color=(255, 100, 100))
        return
    if h2_val < 0 or h2_val > 100:
        set_status("❌ 输入错误：氢气比例必须在 0-100 之间", color=(255, 100, 100))
        return

    try:
        # 执行计算
        result_str = calculate_combustion_logic(p_val, phi_val, h2_val)
        # 显示结果
        dpg.set_value("result_text", result_str)
        set_status("✅ 计算成功", color=(100, 255, 100))
    except Exception as e:
        set_status(f"❌ 未知错误: {str(e)}", color=(255, 100, 100))


def copy_results():
    content = dpg.get_value("result_text")
    if content.strip():
        # DPG 自带剪贴板写入功能，抛弃麻烦的 Tkinter
        dpg.set_clipboard_text(content)
        set_status("📋 结果已成功复制到剪贴板", color=(100, 200, 255))
    else:
        set_status("⚠️ 没有内容可复制", color=(255, 200, 100))


# ==========================================
# 初始化与样式设置
# ==========================================
dpg.create_context()

# 1. 字体设置
with dpg.font_registry():
    with dpg.font("C:/Windows/Fonts/msyh.ttc", 16) as ms_font:
        pass
dpg.bind_font(ms_font)

# 2. 现代暗黑主题
with dpg.theme() as modern_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (30, 30, 32))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 45, 50))
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 110, 200))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 130, 230))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 90, 170))

        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 15, 15)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8)
        dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 12)  # 结果框需要滚动条，这里不设为0

dpg.bind_theme(modern_theme)

# ==========================================
# 构建 UI 界面
# ==========================================
# 锁死主窗口的滚动和拉伸
with dpg.window(tag="Primary_Window", no_scrollbar=True, no_scroll_with_mouse=True):
    dpg.add_text("🔥 Combustion Calc (By zzm)", color=(255, 120, 50))
    dpg.add_separator()

    # --- 输入区域 ---
    dpg.add_text("参数输入:")
    # 去掉了 add_text 里的 width 参数
    with dpg.group(horizontal=True):
        dpg.add_text("热功率 (Watts):")
        dpg.add_input_float(tag="input_power", default_value=400.0, width=200, step=0)

    with dpg.group(horizontal=True):
        dpg.add_text("当量比 (Phi):")
        dpg.add_input_float(tag="input_phi", default_value=1.0, width=200, step=0)

    with dpg.group(horizontal=True):
        dpg.add_text("H2 体积比 (0-100%):")
        dpg.add_input_float(tag="input_h2", default_value=0.0, width=200, step=0)

    # --- 按钮区域 ---
    with dpg.group(horizontal=True):
        dpg.add_button(label="执行计算", width=170, height=35, callback=run_calculation)
        dpg.add_button(label="复制结果", width=170, height=35, callback=copy_results)

    dpg.add_spacer(height=5)

    # --- 结果显示区域 ---
    dpg.add_text("计算结果 (可直接复制至 Fluent):")
    # 多行文本框，超出高度会自动出现内建的滚动条
    dpg.add_input_text(tag="result_text", multiline=True, width=350, height=280, readonly=True)

    dpg.add_separator()

    # --- 底部状态栏 ---
    dpg.add_text("就绪", tag="status_text", color=(150, 150, 150))

# ==========================================
# 渲染配置
# ==========================================
dpg.create_viewport(title='Combustion Calc - DPG Version', width=400, height=590, resizable=False)
dpg.setup_dearpygui()
dpg.set_primary_window("Primary_Window", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()