# Combustion Calc

用于计算甲烷/氢气混合燃料在指定热功率和当量比下的燃烧入口参数，方便快速得到 Fluent 边界条件和实验流量计设置。

## 功能概览

- 根据热功率、当量比 `Phi`、氢气体积分数计算燃料和空气质量流量
- 输出 CH4、H2、O2、N2 的质量分数
- 输出 CH4、H2 的标准体积流量，以及空气在 25°C、1 atm 下的体积流量
- 提供命令行、Tkinter GUI、DearPyGui GUI 多种运行方式

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `combustion_cli.py` | 基础命令行版本 |
| `combustion_cli_25c.py` | 使用 25°C 空气密度修正的命令行版本 |
| `combustion_tkinter_app.py` | Tkinter 图形界面版本，也是当前打包入口 |
| `combustion_dearpygui_app.py` | DearPyGui 图形界面版本 |
| `requirements.txt` | pip 依赖 |
| `environment.yml` | Conda 环境配置 |

## 快速开始

### 方式一：使用 pip

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

运行 Tkinter GUI：

```powershell
python combustion_tkinter_app.py
```

运行 DearPyGui GUI：

```powershell
python combustion_dearpygui_app.py
```

运行命令行版本：

```powershell
python combustion_cli_25c.py
```

### 方式二：使用 Conda

```powershell
conda env create -f environment.yml
conda activate combustor
python combustion_tkinter_app.py
```

## 输入参数

| 参数 | 单位/范围 | 说明 |
| --- | --- | --- |
| 热功率 | W | 燃烧器输入热功率 |
| 当量比 `Phi` | > 0 | 混合气当量比 |
| H2 体积分数 | 0-100% | 燃料中氢气的体积百分比，其余为 CH4 |

## 输出结果

- Fluent 边界条件：燃料入口、空气入口、总流量，单位为 `kg/s`
- Fluent 组分设置：CH4、H2、O2、N2 的质量分数
- 实验流量设置：空气 `L/min`，CH4/H2 `SLPM`

## 打包发布

本项目的 GitHub Actions 会在推送 `v*` 标签时自动打包 Windows exe。当前打包入口为：

```powershell
pyinstaller -F -w -n combustion_calc combustion_tkinter_app.py
```

本地打包前需要安装 PyInstaller：

```powershell
pip install pyinstaller
```

## 注意事项

- `Phi` 和热功率必须大于 0
- H2 体积分数必须在 `0-100` 之间
- `combustion_cli_25c.py` 和 GUI 版本使用空气 25°C 密度计算空气体积流量
- 若只使用 Tkinter 版本，通常不需要额外安装 GUI 依赖；若使用 DearPyGui 版本，需要安装 `dearpygui`
