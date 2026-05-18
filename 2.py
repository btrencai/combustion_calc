import sys

def calculate_combustion(power_watts, phi, h2_vol_fraction):

    # ================= 1. 物理常数定义 =================
    M_CH4 = 16.04
    M_H2 = 2.016
    M_O2 = 32.00
    M_N2 = 28.013
    M_AIR = 28.966

    LHV_CH4 = 50.0e6  # 50 MJ/kg
    LHV_H2 = 120.0e6  # 120 MJ/kg

    Y_O2_air = 0.233
    Vm_STP = 24.465

    # --- 修改点1: 定义25摄氏度下的空气密度 ---
    # 依据 P=rho*R*T, P=101325, T=298.15K, R_air=287.05
    # rho ≈ 1.184 kg/m^3
    rho_air_25C = 1.184

    # ================= 2. 燃料物性计算 =================
    ch4_vol_fraction = 1.0 - h2_vol_fraction

    M_fuel_mix = (ch4_vol_fraction * M_CH4) + (h2_vol_fraction * M_H2)

    Y_CH4_fuel = (ch4_vol_fraction * M_CH4) / M_fuel_mix
    Y_H2_fuel = (h2_vol_fraction * M_H2) / M_fuel_mix

    LHV_mix = (Y_CH4_fuel * LHV_CH4) + (Y_H2_fuel * LHV_H2)

    # ================= 3. 流量计算 =================
    m_dot_fuel = power_watts / LHV_mix

    moles_O2_needed = (ch4_vol_fraction * 2.0) + (h2_vol_fraction * 0.5)
    mass_O2_needed = moles_O2_needed * M_O2
    OFR_st = mass_O2_needed / M_fuel_mix
    AFR_st = OFR_st / Y_O2_air

    AFR_actual = AFR_st / phi
    m_dot_air = m_dot_fuel * AFR_actual
    m_dot_total = m_dot_fuel + m_dot_air

    # ================= 4. 混合后总组分 =================
    mass_CH4 = m_dot_fuel * Y_CH4_fuel
    mass_H2 = m_dot_fuel * Y_H2_fuel
    mass_O2 = m_dot_air * Y_O2_air
    mass_N2 = m_dot_air * (1.0 - Y_O2_air)

    Y_CH4_total = mass_CH4 / m_dot_total
    Y_H2_total = mass_H2 / m_dot_total
    Y_O2_total = mass_O2 / m_dot_total
    Y_N2_total = mass_N2 / m_dot_total

    # ================= 5. SLPM 换算 =================
    # 燃料部分保持原样（通常燃料流量计基于摩尔/标准体积）
    slpm_fuel = (m_dot_fuel * 1000 / M_fuel_mix) * Vm_STP * 60
    slpm_ch4 = slpm_fuel * ch4_vol_fraction
    slpm_h2 = slpm_fuel * h2_vol_fraction

    # --- 修改点2: 空气流量改为 质量流量 / 25度密度 ---
    # m_dot_air 单位 kg/s
    # rho_air_25C 单位 kg/m^3
    # 结果单位: m^3/s -> *1000 -> L/s -> *60 -> L/min
    vol_flow_air_25C = m_dot_air / rho_air_25C
    slpm_air = vol_flow_air_25C * 1000 * 60

    # ================= 6. 打印输出 =================
    print("\n" + "=" * 60)
    print(
        f"【计算结果】 功率: {power_watts}W | Phi: {phi} | 燃料: {ch4_vol_fraction * 100:.0f}% CH4 + {h2_vol_fraction * 100:.0f}% H2")
    print("=" * 60)

    print(f"👉 [Fluent 边界条件 - 质量流量 (Mass Flow Rate)]")
    print(f"   Fuel Inlet (燃料总口): {m_dot_fuel:.4e} kg/s")
    print(f"       >> CH4 分量:       {mass_CH4:.4e} kg/s")
    if h2_vol_fraction > 0:
        print(f"       >> H2  分量:       {mass_H2:.4e} kg/s")
    print(f"   Air Inlet  (空气口):   {m_dot_air:.4e} kg/s")
    print(f"   Total Flow (预混口):   {m_dot_total:.4e} kg/s")
    print("")

    print(f"👉 [Fluent 组分设置 - Species Mass Fractions]")
    print(f"   (预混口或总出口组分)")
    print(f"   CH4: {Y_CH4_total:.5f}")
    print(f"   H2 : {Y_H2_total:.5f}")
    print(f"   O2 : {Y_O2_total:.5f}")
    print(f"   N2 : {Y_N2_total:.5f}")
    print("")

    print(f"👉 [实验流量计 - Volumetric Flow]")
    print(f"   Air 流量 (25℃, 1atm): {slpm_air:.2f} L/min")
    print(f"   CH4 流量 (STP):       {slpm_ch4:.2f} SLPM")
    if h2_vol_fraction > 0:
        print(f"   H2  流量 (STP):       {slpm_h2:.2f} SLPM")
    print("=" * 60 + "\n")


# ================= 主程序 (交互逻辑) =================
if __name__ == "__main__":
    print("\ncombustion_calc by zzm (Air flow @ 25C density)")
    print("-------------------------------------------")

    while True:
        try:
            # 1. 输入功率
            p_input = input("1. 请输入热功率 (单位 W, 例如 400): ")
            if not p_input: break  # 直接回车退出
            power = float(p_input)

            # 2. 输入当量比
            phi_input = input("2. 请输入当量比 Phi (例如 1.0, 贫燃填<1): ")
            phi = float(phi_input)

            # 3. 输入氢气比例
            h2_input = input("3. 请输入氢气体积百分比 (0-100, 例如纯甲烷填0, 掺氢20%填20): ")
            h2_pct = float(h2_input)
            h2_frac = h2_pct / 100.0  # 转换为小数

            # 调用计算
            calculate_combustion(power, phi, h2_frac)

            # 询问是否继续
            cont = input("需要计算下一个工况吗？(直接回车继续，输入 n 退出): ")
            if cont.lower() == 'n':
                print("程序已退出。祝仿真顺利！")
                break

        except ValueError:
            print("\n❌ 输入错误：请输入有效的数字！请重新开始。\n")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            break