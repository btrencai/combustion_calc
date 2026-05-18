from __future__ import annotations

import html
import json
import re
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "CS2 Crosshair Converter Pro"
PROSETTINGS_CS2_URL = "https://prosettings.net/games/cs2/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
BASE = len(DICTIONARY)
SHARECODE_PATTERN = re.compile(r"^CSGO(-?[\w]{5}){5}$")
DATA_FILE = Path.home() / ".cs2_crosshair_converter_history.json"

STYLE_MAP = {
    "default": 0,
    "default static": 1,
    "classic": 2,
    "classic dynamic": 3,
    "classic static": 4,
    "legacy": 5,
}
COLOR_MAP = {
    "red": 0,
    "green": 1,
    "yellow": 2,
    "blue": 3,
    "cyan": 4,
    "custom": 5,
    "white": 5,
    "pink": 5,
    "purple": 5,
    "orange": 5,
}


@dataclass
class Crosshair:
    gap: float
    outline: float
    red: int
    green: int
    blue: int
    alpha: int
    split_distance: int
    follow_recoil: bool
    fixed_crosshair_gap: float
    color: int
    outline_enabled: bool
    inner_split_alpha: float
    outer_split_alpha: float
    split_size_ratio: float
    thickness: float
    center_dot_enabled: bool
    deployed_weapon_gap_enabled: bool
    alpha_enabled: bool
    t_style_enabled: bool
    style: int
    length: float


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._in_a = False
        self._href = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._in_a = True
            self._href = ""
            self._parts = []
            for key, value in attrs:
                if key.lower() == "href":
                    self._href = value or ""

    def handle_data(self, data):
        if self._in_a:
            text = data.strip()
            if text:
                self._parts.append(text)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._in_a:
            text = " ".join(self._parts).strip()
            self.links.append((self._href, text))
            self._in_a = False
            self._href = ""
            self._parts = []


def fetch_url(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="ignore")


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6|tr|td|br)>", "\n", text)
    text = re.sub(r"(?i)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n+", "\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = "\n".join(line for line in text.splitlines() if line.strip())
    return text


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def uint8_to_int8(value: int) -> int:
    return value - 256 if value > 127 else value


def share_code_to_bytes(share_code: str) -> list[int]:
    share_code = share_code.strip()

    if not SHARECODE_PATTERN.fullmatch(share_code):
        raise ValueError("无效的分享码格式。正确格式类似：CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx")

    code = share_code.replace("CSGO", "").replace("-", "")
    chars = list(reversed(code))

    total = 0
    for ch in chars:
        idx = DICTIONARY.find(ch)
        if idx < 0:
            raise ValueError(f"分享码里包含非法字符: {ch}")
        total = total * BASE + idx

    hex_str = f"{total:036x}"
    return [int(hex_str[i:i + 2], 16) for i in range(0, 36, 2)]


def bytes_to_share_code(bytes_: list[int]) -> str:
    hex_str = "".join(f"{b & 0xFF:02x}" for b in bytes_)
    total = int(hex_str, 16)

    chars = []
    for _ in range(25):
        rem = total % BASE
        chars.append(DICTIONARY[rem])
        total //= BASE

    s = "".join(chars)
    return f"CSGO-{s[0:5]}-{s[5:10]}-{s[10:15]}-{s[15:20]}-{s[20:25]}"


def decode_crosshair_share_code(share_code: str) -> Crosshair:
    b = share_code_to_bytes(share_code)

    checksum = sum(b[1:]) % 256
    if b[0] != checksum:
        raise ValueError("分享码校验失败，不是有效的准星码。")

    return Crosshair(
        gap=uint8_to_int8(b[2]) / 10.0,
        outline=b[3] / 2.0,
        red=b[4],
        green=b[5],
        blue=b[6],
        alpha=b[7],
        split_distance=b[8] & 0x07,
        follow_recoil=bool(b[8] & 0x80),
        fixed_crosshair_gap=uint8_to_int8(b[9]) / 10.0,
        color=b[10] & 0x07,
        outline_enabled=bool(b[10] & 0x08),
        inner_split_alpha=(b[10] >> 4) / 10.0,
        outer_split_alpha=(b[11] & 0x0F) / 10.0,
        split_size_ratio=(b[11] >> 4) / 10.0,
        thickness=b[12] / 10.0,
        center_dot_enabled=bool((b[13] >> 4) & 0x01),
        deployed_weapon_gap_enabled=bool((b[13] >> 4) & 0x02),
        alpha_enabled=bool((b[13] >> 4) & 0x04),
        t_style_enabled=bool((b[13] >> 4) & 0x08),
        style=(b[13] & 0x0F) >> 1,
        length=b[14] / 10.0,
    )


def encode_crosshair(crosshair: Crosshair) -> str:
    bytes_ = [
        0,
        1,
        int(round(crosshair.gap * 10)) & 0xFF,
        int(round(crosshair.outline * 2)),
        int(round(crosshair.red)),
        int(round(crosshair.green)),
        int(round(crosshair.blue)),
        int(round(crosshair.alpha)),
        (int(crosshair.split_distance) & 7) | (int(bool(crosshair.follow_recoil)) << 7),
        int(round(crosshair.fixed_crosshair_gap * 10)) & 0xFF,
        (int(crosshair.color) & 7)
        | (int(bool(crosshair.outline_enabled)) << 3)
        | (int(round(crosshair.inner_split_alpha * 10)) << 4),
        int(round(crosshair.outer_split_alpha * 10))
        | (int(round(crosshair.split_size_ratio * 10)) << 4),
        int(round(crosshair.thickness * 10)),
        (int(crosshair.style) << 1)
        | (int(bool(crosshair.center_dot_enabled)) << 4)
        | (int(bool(crosshair.deployed_weapon_gap_enabled)) << 5)
        | (int(bool(crosshair.alpha_enabled)) << 6)
        | (int(bool(crosshair.t_style_enabled)) << 7),
        int(round(crosshair.length * 10)),
        0,
        0,
        0,
    ]
    bytes_[0] = sum(bytes_) & 0xFF
    return bytes_to_share_code(bytes_)


def crosshair_to_convars(crosshair: Crosshair, one_line: bool = False) -> str:
    lines = [
        f'cl_crosshair_drawoutline "{int(crosshair.outline_enabled)}"',
        f'cl_crosshair_dynamic_maxdist_splitratio "{crosshair.split_size_ratio}"',
        f'cl_crosshair_dynamic_splitalpha_innermod "{crosshair.inner_split_alpha}"',
        f'cl_crosshair_dynamic_splitalpha_outermod "{crosshair.outer_split_alpha}"',
        f'cl_crosshair_dynamic_splitdist "{crosshair.split_distance}"',
        f'cl_crosshair_outlinethickness "{crosshair.outline}"',
        f'cl_crosshair_t "{int(crosshair.t_style_enabled)}"',
        f'cl_crosshairalpha "{crosshair.alpha}"',
        f'cl_crosshaircolor "{crosshair.color}"',
        f'cl_crosshaircolor_b "{crosshair.blue}"',
        f'cl_crosshaircolor_g "{crosshair.green}"',
        f'cl_crosshaircolor_r "{crosshair.red}"',
        f'cl_crosshairdot "{int(crosshair.center_dot_enabled)}"',
        f'cl_crosshairgap "{crosshair.gap}"',
        f'cl_crosshairgap_useweaponvalue "{int(crosshair.deployed_weapon_gap_enabled)}"',
        f'cl_crosshairsize "{crosshair.length}"',
        f'cl_crosshairstyle "{crosshair.style}"',
        f'cl_crosshairthickness "{crosshair.thickness}"',
        f'cl_crosshairusealpha "{int(crosshair.alpha_enabled)}"',
        f'cl_fixedcrosshairgap "{crosshair.fixed_crosshair_gap}"',
        f'cl_crosshair_recoil "{int(crosshair.follow_recoil)}"',
    ]
    return "; ".join(lines) if one_line else "\n".join(lines)


def bool_text(v: bool) -> str:
    return "是" if v else "否"


def parse_yes_no(value: str) -> bool:
    v = normalize_spaces(value).lower()
    return v in {"yes", "true", "enabled", "on"}


def parse_float(value: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?", value)
    if not m:
        raise ValueError(f"无法解析数字: {value}")
    return float(m.group(0))


def parse_int(value: str) -> int:
    return int(round(parse_float(value)))


def extract_block_value(section: str, label: str, next_label: str) -> str:
    pattern = re.compile(
        rf"{re.escape(label)}\s+(.*?)\s+(?={re.escape(next_label)})",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(section)
    if not m:
        raise ValueError(f"未找到字段: {label}")
    return normalize_spaces(m.group(1))


def parse_crosshair_from_player_page(raw_html: str) -> Crosshair:
    text = html_to_text(raw_html)
    compact = normalize_spaces(text)

    start_anchor = "Style"
    end_anchor_candidates = ["Crosshair History", "Viewmodel", "History Viewmodel", "Hud"]
    start = compact.find(start_anchor)
    if start == -1:
        raise ValueError("页面中没有找到 Crosshair 参数区块。")

    end = len(compact)
    for marker in end_anchor_candidates:
        pos = compact.find(marker, start)
        if pos != -1:
            end = min(end, pos)
    section = compact[start:end]

    ordered_labels = [
        "Style",
        "Follow Recoil",
        "Dot",
        "Length",
        "Thickness",
        "Gap",
        "Outline",
        "Outlinethickness",
        "Color",
        "Red",
        "Green",
        "Blue",
        "Alpha",
        "Alpha Value",
        "T Style",
        "Deployed Weapon Gap",
        "Split Distance",
        "Fixed Gap",
        "Inner Split Alpha",
        "Outer Split Alpha",
        "Split Size Ratio",
        "Sniper Width",
    ]

    values: dict[str, str] = {}
    for i in range(len(ordered_labels) - 1):
        label = ordered_labels[i]
        next_label = ordered_labels[i + 1]
        values[label] = extract_block_value(section, label, next_label)

    style_name = values["Style"].lower()
    if style_name not in STYLE_MAP:
        raise ValueError(f"暂不支持的准星样式: {values['Style']}")

    color_name = values["Color"].lower()
    color_value = COLOR_MAP.get(color_name, 5)

    return Crosshair(
        gap=parse_float(values["Gap"]),
        outline=parse_float(values["Outlinethickness"]),
        red=parse_int(values["Red"]),
        green=parse_int(values["Green"]),
        blue=parse_int(values["Blue"]),
        alpha=parse_int(values["Alpha Value"]),
        split_distance=parse_int(values["Split Distance"]),
        follow_recoil=parse_yes_no(values["Follow Recoil"]),
        fixed_crosshair_gap=parse_float(values["Fixed Gap"]),
        color=color_value,
        outline_enabled=parse_yes_no(values["Outline"]),
        inner_split_alpha=parse_float(values["Inner Split Alpha"]),
        outer_split_alpha=parse_float(values["Outer Split Alpha"]),
        split_size_ratio=parse_float(values["Split Size Ratio"]),
        thickness=parse_float(values["Thickness"]),
        center_dot_enabled=parse_yes_no(values["Dot"]),
        deployed_weapon_gap_enabled=parse_yes_no(values["Deployed Weapon Gap"]),
        alpha_enabled=parse_yes_no(values["Alpha"]),
        t_style_enabled=parse_yes_no(values["T Style"]),
        style=STYLE_MAP[style_name],
        length=parse_float(values["Length"]),
    )


def collect_player_links_from_html(base_url: str, raw_html: str) -> list[dict]:
    parser = LinkCollector()
    parser.feed(raw_html)

    seen: dict[str, dict] = {}
    for href, text in parser.links:
        if not href or not text:
            continue

        full_url = urllib.parse.urljoin(base_url, href)
        m = re.search(r"/players/([^/]+)/?$", full_url)
        if not m:
            continue

        slug = m.group(1)
        clean_text = normalize_spaces(text)
        if len(clean_text) > 40:
            continue
        if clean_text.lower() in {"players", "see all players"}:
            continue

        seen[slug] = {"name": clean_text, "slug": slug, "url": full_url}

    return sorted(seen.values(), key=lambda item: item["name"].lower())


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1450x860")
        self.minsize(1280, 760)

        self.share_code_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请输入分享码，或从左侧抓取职业哥准星。")
        self.player_filter_var = tk.StringVar()
        self.page_count_var = tk.StringVar(value="2")

        self.current_crosshair: Crosshair | None = None
        self.current_player_url: str = ""
        self.history: list[dict] = self.load_history()
        self.players: list[dict] = []

        self._build_style()
        self._build_ui()
        self.refresh_history_view()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#111827"
        panel = "#1f2937"
        panel2 = "#0f172a"
        fg = "#e5e7eb"
        subfg = "#9ca3af"
        link = "#60a5fa"

        self.colors = {
            "bg": bg,
            "panel": panel,
            "panel2": panel2,
            "fg": fg,
            "subfg": subfg,
            "link": link,
        }

        self.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg, fieldbackground=panel2)
        style.configure("Card.TFrame", background=panel, relief="flat")
        style.configure("Panel.TFrame", background=panel2, relief="flat")
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground=subfg, font=("Microsoft YaHei UI", 10))
        style.configure("CardTitle.TLabel", background=panel, foreground=fg, font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("PanelTitle.TLabel", background=panel2, foreground=fg, font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TLabel", background=bg, foreground=fg, font=("Microsoft YaHei UI", 10))
        style.configure("TEntry", padding=8)
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=8)
        style.configure("Treeview", background=panel2, foreground=fg, fieldbackground=panel2, rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background=panel, foreground=fg, font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2563eb")])
        style.configure("Status.TLabel", background=bg, foreground=subfg, font=("Microsoft YaHei UI", 9))
        style.configure("Small.TButton", padding=5)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x", pady=(0, 14))
        ttk.Label(top, text=APP_TITLE, style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            top,
            text="支持分享码转换、本地生成 cfg、近似准星预览、以及从 ProSettings 自动抓取职业哥准星参数并编码成分享码。",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(4, 0))

        link_label = tk.Label(
            top,
            text=PROSETTINGS_CS2_URL,
            fg=self.colors["link"],
            bg=self.colors["bg"],
            cursor="hand2",
            font=("Consolas", 10, "underline"),
        )
        link_label.pack(anchor="w", pady=(6, 0))
        link_label.bind("<Button-1>", lambda e: webbrowser.open(PROSETTINGS_CS2_URL))

        main = ttk.Frame(root)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=350, style="Card.TFrame", padding=12)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        center = ttk.Frame(main)
        center.pack(side="left", fill="both", expand=True)

        self.build_player_panel(left)

        input_card = ttk.Frame(center, style="Card.TFrame", padding=14)
        input_card.pack(fill="x", pady=(0, 12))

        ttk.Label(input_card, text="准星分享码", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.entry = ttk.Entry(input_card, textvariable=self.share_code_var, font=("Consolas", 11))
        self.entry.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(8, 10))
        self.entry.insert(0, "CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx")

        ttk.Button(input_card, text="转换", command=self.convert, style="Accent.TButton").grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="复制命令", command=self.copy_commands).grid(row=2, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="复制分享码", command=self.copy_share_code).grid(row=2, column=2, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="导出 cfg", command=self.export_cfg).grid(row=2, column=3, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="收藏当前", command=self.toggle_favorite_current).grid(row=2, column=4, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="清空", command=self.clear_all).grid(row=2, column=5, sticky="ew", padx=(0, 8))
        ttk.Button(input_card, text="示例格式", command=self.insert_example).grid(row=2, column=6, sticky="ew")
        for i in range(7):
            input_card.columnconfigure(i, weight=1)

        content = ttk.Frame(center)
        content.pack(fill="both", expand=True)

        mid_left = ttk.Frame(content, style="Card.TFrame", padding=12)
        mid_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        mid_right = ttk.Frame(content, style="Card.TFrame", padding=12)
        mid_right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        ttk.Label(mid_left, text="解码参数", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        self.tree = ttk.Treeview(mid_left, columns=("name", "value"), show="headings")
        self.tree.heading("name", text="参数")
        self.tree.heading("value", text="值")
        self.tree.column("name", width=230, anchor="w")
        self.tree.column("value", width=200, anchor="w")
        tree_scroll = ttk.Scrollbar(mid_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        preview_card = ttk.Frame(mid_right, style="Panel.TFrame", padding=12)
        preview_card.pack(fill="x", pady=(0, 12))
        ttk.Label(preview_card, text="准星预览（比上一版更接近，但仍非游戏逐像素还原）", style="PanelTitle.TLabel").pack(anchor="w")
        self.preview_canvas = tk.Canvas(preview_card, width=520, height=320, bg="#0b1020", highlightthickness=0)
        self.preview_canvas.pack(fill="x", expand=True, pady=(8, 0))

        ttk.Label(mid_right, text="控制台命令", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        self.output = tk.Text(
            mid_right,
            wrap="word",
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            padx=10,
            pady=10,
            height=16,
        )
        self.output.pack(fill="both", expand=True)
        self.output.insert("1.0", "转换后的 cl_crosshair 命令会显示在这里。")

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Label(bottom, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w")

        self.entry.bind("<Return>", lambda event: self.convert())
        self.player_filter_var.trace_add("write", lambda *_: self.refresh_player_view())
        self.draw_placeholder_preview()

    def build_player_panel(self, parent) -> None:
        ttk.Label(parent, text="职业哥抓取 / 历史收藏", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))

        help_text = (
            "1. 可点击上方 ProSettings 链接\n"
            "2. 抓取前 N 页职业哥列表\n"
            "3. 双击职业哥自动抓取参数并生成分享码\n"
            "4. 历史记录双击可回填"
        )
        ttk.Label(parent, text=help_text, style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        crawl_bar = ttk.Frame(parent)
        crawl_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(crawl_bar, text="页数").pack(side="left")
        page_entry = ttk.Entry(crawl_bar, textvariable=self.page_count_var, width=5)
        page_entry.pack(side="left", padx=(6, 8))
        ttk.Button(crawl_bar, text="抓取职业哥", command=self.crawl_players, style="Small.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(crawl_bar, text="打开站点", command=lambda: webbrowser.open(PROSETTINGS_CS2_URL), style="Small.TButton").pack(side="left")

        ttk.Label(parent, text="筛选职业哥", style="Sub.TLabel").pack(anchor="w", pady=(6, 4))
        ttk.Entry(parent, textvariable=self.player_filter_var).pack(fill="x", pady=(0, 8))

        player_panel = ttk.Frame(parent, style="Panel.TFrame", padding=8)
        player_panel.pack(fill="both", expand=False, pady=(0, 10))
        ttk.Label(player_panel, text="职业哥列表", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 8))

        self.player_tree = ttk.Treeview(player_panel, columns=("name", "slug"), show="headings", height=11)
        self.player_tree.heading("name", text="选手")
        self.player_tree.heading("slug", text="slug")
        self.player_tree.column("name", width=120, anchor="w")
        self.player_tree.column("slug", width=120, anchor="w")
        player_scroll = ttk.Scrollbar(player_panel, orient="vertical", command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=player_scroll.set)
        self.player_tree.pack(side="left", fill="both", expand=True)
        player_scroll.pack(side="right", fill="y")
        self.player_tree.bind("<Double-1>", self.on_player_double_click)

        player_btns = ttk.Frame(parent)
        player_btns.pack(fill="x", pady=(0, 10))
        ttk.Button(player_btns, text="抓取所选职业哥", command=self.fetch_selected_player, style="Small.TButton").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(player_btns, text="打开选手页", command=self.open_selected_player_page, style="Small.TButton").pack(side="left", fill="x", expand=True)

        ttk.Label(parent, text="历史 / 收藏", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        self.history_tree = ttk.Treeview(parent, columns=("fav", "code"), show="headings", height=10)
        self.history_tree.heading("fav", text="★")
        self.history_tree.heading("code", text="分享码")
        self.history_tree.column("fav", width=42, anchor="center")
        self.history_tree.column("code", width=220, anchor="w")
        history_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        history_scroll.pack(side="right", fill="y")
        self.history_tree.bind("<Double-1>", self.on_history_double_click)

        action_bar = ttk.Frame(parent)
        action_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(action_bar, text="删除记录", command=self.delete_selected_history, style="Small.TButton").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(action_bar, text="切换收藏", command=self.toggle_selected_history_favorite, style="Small.TButton").pack(side="left", fill="x", expand=True)

    def insert_example(self) -> None:
        self.share_code_var.set("CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx")
        self.entry.select_range(0, "end")
        self.entry.icursor("end")
        self.status_var.set("已填入示例格式，请替换成你的真实分享码。")

    def clear_all(self) -> None:
        self.share_code_var.set("")
        self.current_crosshair = None
        self.current_player_url = ""
        self.output.delete("1.0", "end")
        self.output.insert("1.0", "转换后的 cl_crosshair 命令会显示在这里。")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.draw_placeholder_preview()
        self.status_var.set("已清空。")
        self.entry.focus_set()

    def convert(self) -> None:
        code = self.share_code_var.get().strip()
        if not code or "xxxxx" in code:
            messagebox.showwarning("提示", "请先输入真实的准星分享码。")
            return

        try:
            crosshair = decode_crosshair_share_code(code)
            self.current_crosshair = crosshair
            self.populate_params(crosshair)
            self.output.delete("1.0", "end")
            self.output.insert("1.0", crosshair_to_convars(crosshair))
            self.draw_crosshair_preview(crosshair)
            self.add_to_history(code)
            fav_text = "已收藏" if self.is_favorite(code) else "未收藏"
            self.status_var.set(f"转换成功，可以复制命令或导出 cfg。当前记录：{fav_text}")
        except Exception as exc:
            messagebox.showerror("转换失败", str(exc))
            self.status_var.set("转换失败，请检查分享码格式。")

    def crawl_players(self) -> None:
        try:
            pages = max(1, int(self.page_count_var.get().strip() or "1"))
        except ValueError:
            messagebox.showwarning("提示", "页数请输入整数。")
            return

        try:
            all_players: dict[str, dict] = {}
            for page in range(1, pages + 1):
                url = PROSETTINGS_CS2_URL if page == 1 else urllib.parse.urljoin(PROSETTINGS_CS2_URL, f"page/{page}/")
                self.status_var.set(f"正在抓取职业哥列表：第 {page}/{pages} 页...")
                self.update_idletasks()
                raw_html = fetch_url(url)
                items = collect_player_links_from_html(url, raw_html)
                for item in items:
                    all_players[item["slug"]] = item

            self.players = sorted(all_players.values(), key=lambda x: x["name"].lower())
            self.refresh_player_view()
            self.status_var.set(f"抓取完成，共获取 {len(self.players)} 名职业哥。")
        except urllib.error.URLError as exc:
            messagebox.showerror("网络错误", f"抓取职业哥列表失败：\n{exc}")
            self.status_var.set("抓取失败。")
        except Exception as exc:
            messagebox.showerror("错误", str(exc))
            self.status_var.set("抓取失败。")

    def refresh_player_view(self) -> None:
        keyword = self.player_filter_var.get().strip().lower()
        for item in self.player_tree.get_children():
            self.player_tree.delete(item)

        display = self.players
        if keyword:
            display = [
                item for item in self.players
                if keyword in item["name"].lower() or keyword in item["slug"].lower()
            ]

        for idx, item in enumerate(display):
            self.player_tree.insert("", "end", iid=str(idx), values=(item["name"], item["slug"]))

    def get_selected_player(self) -> dict | None:
        selection = self.player_tree.selection()
        if not selection:
            return None

        name, slug = self.player_tree.item(selection[0], "values")
        for item in self.players:
            if item["name"] == name and item["slug"] == slug:
                return item
        return None

    def on_player_double_click(self, event=None) -> None:
        self.fetch_selected_player()

    def open_selected_player_page(self) -> None:
        player = self.get_selected_player()
        if not player:
            messagebox.showinfo("提示", "请先选中一个职业哥。")
            return
        webbrowser.open(player["url"])

    def fetch_selected_player(self) -> None:
        player = self.get_selected_player()
        if not player:
            messagebox.showinfo("提示", "请先选中一个职业哥。")
            return

        try:
            self.status_var.set(f"正在抓取 {player['name']} 的准星参数...")
            self.update_idletasks()
            raw_html = fetch_url(player["url"])
            crosshair = parse_crosshair_from_player_page(raw_html)
            share_code = encode_crosshair(crosshair)

            self.current_player_url = player["url"]
            self.current_crosshair = crosshair
            self.share_code_var.set(share_code)
            self.populate_params(crosshair)
            self.output.delete("1.0", "end")
            self.output.insert("1.0", crosshair_to_convars(crosshair))
            self.draw_crosshair_preview(crosshair)
            self.add_to_history(share_code)

            self.status_var.set(f"已抓取 {player['name']} 的准星参数，并自动编码为分享码。")
        except urllib.error.URLError as exc:
            messagebox.showerror("网络错误", f"抓取 {player['name']} 失败：\n{exc}")
            self.status_var.set("抓取失败。")
        except Exception as exc:
            messagebox.showerror("解析失败", f"{player['name']} 页面解析失败：\n{exc}")
            self.status_var.set("解析失败。")

    def populate_params(self, crosshair: Crosshair) -> None:
        data = asdict(crosshair)
        labels = {
            "gap": "中心间距",
            "outline": "描边厚度",
            "red": "红色",
            "green": "绿色",
            "blue": "蓝色",
            "alpha": "透明度",
            "split_distance": "动态分裂距离",
            "follow_recoil": "跟随压枪",
            "fixed_crosshair_gap": "固定间距",
            "color": "颜色模式",
            "outline_enabled": "启用描边",
            "inner_split_alpha": "内部分裂透明度",
            "outer_split_alpha": "外部分裂透明度",
            "split_size_ratio": "动态分裂比例",
            "thickness": "线条厚度",
            "center_dot_enabled": "启用中心点",
            "deployed_weapon_gap_enabled": "按武器变化间距",
            "alpha_enabled": "启用 Alpha",
            "t_style_enabled": "T 型准星",
            "style": "样式",
            "length": "长度",
        }

        for item in self.tree.get_children():
            self.tree.delete(item)

        for key, value in data.items():
            if isinstance(value, bool):
                value = bool_text(value)
            self.tree.insert("", "end", values=(labels.get(key, key), value))

    def color_hex(self, ch: Crosshair) -> str:
        return f"#{ch.red:02x}{ch.green:02x}{ch.blue:02x}"

    def alpha_to_stipple(self, alpha: int) -> str:
        if alpha >= 220:
            return ""
        if alpha >= 170:
            return "gray75"
        if alpha >= 110:
            return "gray50"
        return "gray25"

    def draw_placeholder_preview(self) -> None:
        self.preview_canvas.delete("all")
        w = int(self.preview_canvas["width"])
        h = int(self.preview_canvas["height"])
        self.preview_canvas.create_text(w / 2, h / 2 - 12, text="准星预览区域", fill="#94a3b8", font=("Microsoft YaHei UI", 16, "bold"))
        self.preview_canvas.create_text(w / 2, h / 2 + 18, text="转换或抓取职业哥后会在这里显示近似效果", fill="#64748b", font=("Microsoft YaHei UI", 10))

    def draw_crosshair_preview(self, ch: Crosshair) -> None:
        c = self.preview_canvas
        c.delete("all")
        w = int(c["width"])
        h = int(c["height"])
        cx, cy = w / 2, h / 2

        c.create_line(cx, 0, cx, h, fill="#162033")
        c.create_line(0, cy, w, cy, fill="#162033")

        color = self.color_hex(ch)
        stipple = self.alpha_to_stipple(ch.alpha)
        style = int(ch.style)

        line_len = max(4, ch.length * 14.0)
        thickness = max(1.5, ch.thickness * 4.0)

        # 预览上尽量贴近经典静态准星：
        # 对大多数职业哥页面来说，style 基本是 Classic / Classic Static / Legacy，
        # 这里优先使用 gap；仅在 Legacy 风格时参考 fixed gap。
        base_gap = ch.fixed_crosshair_gap if style == 5 else ch.gap
        inner = 6 + base_gap * 7.0

        # 负 gap 会让线段更靠近中心甚至部分覆盖
        if inner < -line_len + 2:
            inner = -line_len + 2

        outline_extra = ch.outline * 2.0 + 2 if ch.outline_enabled else 0

        def draw_segment(x1, y1, x2, y2):
            if ch.outline_enabled and ch.outline > 0:
                c.create_line(
                    x1, y1, x2, y2,
                    fill="black",
                    width=thickness + outline_extra,
                    capstyle=tk.ROUND,
                )
            c.create_line(
                x1, y1, x2, y2,
                fill=color,
                width=thickness,
                capstyle=tk.ROUND,
                stipple=stipple,
            )

        # 左 / 右
        draw_segment(cx - inner, cy, cx - inner - line_len, cy)
        draw_segment(cx + inner, cy, cx + inner + line_len, cy)

        # 下
        draw_segment(cx, cy + inner, cx, cy + inner + line_len)

        # 上（T 型准星时不画）
        if not ch.t_style_enabled:
            draw_segment(cx, cy - inner, cx, cy - inner - line_len)

        if ch.center_dot_enabled:
            dot = max(2.2, thickness * 0.75)
            if ch.outline_enabled and ch.outline > 0:
                c.create_oval(cx - dot - 2, cy - dot - 2, cx + dot + 2, cy + dot + 2, fill="black", outline="black")
            c.create_oval(cx - dot, cy - dot, cx + dot, cy + dot, fill=color, outline=color, stipple=stipple)

        tips = [
            f"分享码: {self.share_code_var.get().strip()[:38]}",
            f"样式: {ch.style}    T型: {bool_text(ch.t_style_enabled)}    中心点: {bool_text(ch.center_dot_enabled)}",
            f"长度: {ch.length}    间距: {ch.gap}    厚度: {ch.thickness}    RGB: {ch.red},{ch.green},{ch.blue}",
        ]
        y = h - 62
        for text in tips:
            c.create_text(14, y, anchor="w", text=text, fill="#cbd5e1", font=("Microsoft YaHei UI", 9))
            y += 18

    def copy_commands(self) -> None:
        content = self.output.get("1.0", "end").strip()
        if not content or "显示在这里" in content:
            messagebox.showinfo("提示", "当前没有可复制的命令。")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        self.status_var.set("命令已复制到剪贴板。")

    def copy_share_code(self) -> None:
        content = self.share_code_var.get().strip()
        if not content or not SHARECODE_PATTERN.fullmatch(content):
            messagebox.showinfo("提示", "当前没有可复制的有效分享码。")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        self.status_var.set("分享码已复制到剪贴板。")

    def export_cfg(self) -> None:
        if self.current_crosshair is None:
            messagebox.showinfo("提示", "请先转换一个分享码或抓取一个职业哥。")
            return

        default_name = "crosshair_autoexec.cfg"
        path = filedialog.asksaveasfilename(
            title="导出 cfg",
            defaultextension=".cfg",
            initialfile=default_name,
            filetypes=[("CFG 文件", "*.cfg"), ("所有文件", "*.*")],
        )
        if not path:
            return

        code = self.share_code_var.get().strip()
        commands = crosshair_to_convars(self.current_crosshair)
        content = "\n".join([
            "// Generated by CS2 Crosshair Converter Pro",
            f"// Share code: {code}",
            f"// Source player page: {self.current_player_url}" if self.current_player_url else "",
            "",
            commands,
            "",
        ])
        Path(path).write_text(content, encoding="utf-8")
        self.status_var.set(f"已导出 cfg: {path}")
        messagebox.showinfo("导出成功", f"cfg 已保存到：\n{path}")

    def load_history(self) -> list[dict]:
        if not DATA_FILE.exists():
            return []
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:300]
        except Exception:
            pass
        return []

    def save_history(self) -> None:
        try:
            DATA_FILE.write_text(json.dumps(self.history[:300], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def add_to_history(self, code: str) -> None:
        existing = next((item for item in self.history if item.get("code") == code), None)
        if existing:
            favorite = bool(existing.get("favorite", False))
            self.history = [item for item in self.history if item.get("code") != code]
            self.history.insert(0, {"code": code, "favorite": favorite})
        else:
            self.history.insert(0, {"code": code, "favorite": False})
        self.history = self.history[:300]
        self.save_history()
        self.refresh_history_view()

    def is_favorite(self, code: str) -> bool:
        item = next((item for item in self.history if item.get("code") == code), None)
        return bool(item and item.get("favorite"))

    def toggle_favorite_current(self) -> None:
        code = self.share_code_var.get().strip()
        if not code or self.current_crosshair is None:
            messagebox.showinfo("提示", "请先转换一个分享码。")
            return
        self.set_favorite(code, not self.is_favorite(code))

    def set_favorite(self, code: str, value: bool) -> None:
        found = False
        for item in self.history:
            if item.get("code") == code:
                item["favorite"] = value
                found = True
                break
        if not found:
            self.history.insert(0, {"code": code, "favorite": value})
        self.save_history()
        self.refresh_history_view()
        self.status_var.set("已加入收藏。" if value else "已取消收藏。")

    def refresh_history_view(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        sorted_history = sorted(
            enumerate(self.history),
            key=lambda x: (0 if x[1].get("favorite") else 1, x[0]),
        )
        for idx, item in sorted_history:
            fav = "★" if item.get("favorite") else ""
            code = item.get("code", "")
            self.history_tree.insert("", "end", iid=str(idx), values=(fav, code))

    def get_selected_history_index(self) -> int | None:
        selected = self.history_tree.selection()
        if not selected:
            return None
        try:
            return int(selected[0])
        except Exception:
            return None

    def on_history_double_click(self, event=None) -> None:
        idx = self.get_selected_history_index()
        if idx is None or idx >= len(self.history):
            return
        code = self.history[idx].get("code", "")
        self.share_code_var.set(code)
        self.convert()

    def delete_selected_history(self) -> None:
        idx = self.get_selected_history_index()
        if idx is None or idx >= len(self.history):
            messagebox.showinfo("提示", "请先选中一条记录。")
            return
        code = self.history[idx].get("code", "")
        self.history.pop(idx)
        self.save_history()
        self.refresh_history_view()
        self.status_var.set(f"已删除记录：{code}")

    def toggle_selected_history_favorite(self) -> None:
        idx = self.get_selected_history_index()
        if idx is None or idx >= len(self.history):
            messagebox.showinfo("提示", "请先选中一条记录。")
            return
        code = self.history[idx].get("code", "")
        self.set_favorite(code, not self.history[idx].get("favorite", False))


if __name__ == "__main__":
    app = App()
    app.mainloop()
