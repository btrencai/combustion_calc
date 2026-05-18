import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


def calculate_combustion_logic(power_watts, phi, h2_pct):
    """
    核心计算逻辑，完全保留原始算法
    """
    h2_vol_fraction = h2_pct / 100.0

    # ================= 1. 物理常数定义 =================
    M_CH4 = 16.04
    M_H2 = 2.016
    M_O2 = 32.00
    M_N2 = 28.013

    LHV_CH4 = 50.0e6  # 50 MJ/kg
    LHV_H2 = 120.0e6  # 120 MJ/kg

    Y_O2_air = 0.233
    Vm_STP = 24.465

    # --- 您的修改点: 定义25摄氏度下的空气密度 ---
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
    slpm_fuel = (m_dot_fuel * 1000 / M_fuel_mix) * Vm_STP * 60
    slpm_ch4 = slpm_fuel * ch4_vol_fraction
    slpm_h2 = slpm_fuel * h2_vol_fraction

    # --- 您的修改点: 空气流量改为 质量流量 / 25度密度 ---
    vol_flow_air_25C = m_dot_air / rho_air_25C
    slpm_air = vol_flow_air_25C * 1000 * 60

    # ================= 6. 构建输出文本 =================
    lines = []
    lines.append("=" * 50)
    lines.append(f"【工况】功率: {power_watts}W | Phi: {phi} | H2比例: {h2_pct}%")
    lines.append("=" * 50)

    lines.append("\n👉 [Fluent 边界条件 - Mass Flow Rate (kg/s)]")
    lines.append(f"   Fuel Inlet: {m_dot_fuel:.4e}")
    lines.append(f"       >> CH4: {mass_CH4:.4e}")
    if h2_vol_fraction > 0:
        lines.append(f"       >> H2 : {mass_H2:.4e}")
    lines.append(f"   Air Inlet : {m_dot_air:.4e}")
    lines.append(f"   Total Flow: {m_dot_total:.4e}")

    lines.append("\n👉 [Fluent 组分 - Mass Fraction]")
    lines.append(f"   CH4: {Y_CH4_total:.5f}")
    lines.append(f"   H2 : {Y_H2_total:.5f}")
    lines.append(f"   O2 : {Y_O2_total:.5f}")
    lines.append(f"   N2 : {Y_N2_total:.5f}")

    lines.append("\n👉 [实验流量计设置]")
    lines.append(f"   Air (25℃, 1atm): {slpm_air:.2f} L/min")
    lines.append(f"   CH4 (STP):       {slpm_ch4:.2f} SLPM")
    if h2_vol_fraction > 0:
        lines.append(f"   H2  (STP):       {slpm_h2:.2f} SLPM")

    return "\n".join(lines)


class CombustionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Combustion Calc (By zzm)")
        self.root.geometry("500x650")

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')  # 使用比较现代的主题

        # 主框架
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 输入区域 ---
        input_frame = ttk.LabelFrame(main_frame, text="参数输入", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # 功率
        ttk.Label(input_frame, text="热功率 (Watts):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_power = ttk.Entry(input_frame)
        self.entry_power.grid(row=0, column=1, sticky=tk.E, padx=5)
        self.entry_power.insert(0, "400")  # 默认值

        # 当量比
        ttk.Label(input_frame, text="当量比 (Phi):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_phi = ttk.Entry(input_frame)
        self.entry_phi.grid(row=1, column=1, sticky=tk.E, padx=5)
        self.entry_phi.insert(0, "1.0")

        # 氢气比例
        ttk.Label(input_frame, text="氢气体积比 (0-100%):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_h2 = ttk.Entry(input_frame)
        self.entry_h2.grid(row=2, column=1, sticky=tk.E, padx=5)
        self.entry_h2.insert(0, "0")

        # --- 按钮区域 ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        calc_btn = ttk.Button(btn_frame, text="计算 (Calculate)", command=self.run_calculation)
        calc_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        copy_btn = ttk.Button(btn_frame, text="复制结果", command=self.copy_results)
        copy_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- 结果显示区域 ---
        result_labelframe = ttk.LabelFrame(main_frame, text="计算结果 (可直接复制)", padding="5")
        result_labelframe.pack(fill=tk.BOTH, expand=True)

        # 文本框 (带滚动条)
        self.result_text = tk.Text(result_labelframe, height=20, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(result_labelframe, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 底部状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def run_calculation(self):
        try:
            # 获取输入
            p_val = float(self.entry_power.get())
            phi_val = float(self.entry_phi.get())
            h2_val = float(self.entry_h2.get())

            # 简单验证
            if p_val <= 0 or phi_val <= 0:
                messagebox.showerror("输入错误", "功率和当量比必须大于0")
                return
            if h2_val < 0 or h2_val > 100:
                messagebox.showerror("输入错误", "氢气比例必须在 0-100 之间")
                return

            # 执行计算
            result_str = calculate_combustion_logic(p_val, phi_val, h2_val)

            # 显示结果
            self.result_text.delete(1.0, tk.END)  # 清空
            self.result_text.insert(tk.END, result_str)
            self.status_var.set("计算成功")

        except ValueError:
            messagebox.showerror("格式错误", "请输入有效的数字！")
        except Exception as e:
            messagebox.showerror("未知错误", str(e))

    def copy_results(self):
        content = self.result_text.get(1.0, tk.END)
        if content.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("结果已复制到剪贴板")
        else:
            self.status_var.set("没有内容可复制")


if __name__ == "__main__":
    root = tk.Tk()
    app = CombustionApp(root)
    root.mainloop()