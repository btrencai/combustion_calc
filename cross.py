# cs2_crosshair_converter.py
from __future__ import annotations

import re
from dataclasses import dataclass, asdict


DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
BASE = len(DICTIONARY)
SHARECODE_PATTERN = re.compile(r"^CSGO(-?[\w]{5}){5}$")


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


def uint8_to_int8(value: int) -> int:
    """把 0~255 按有符号 int8 解释。"""
    return value - 256 if value > 127 else value


def share_code_to_bytes(share_code: str) -> list[int]:
    """
    按公开实现中的规则，把 CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx
    还原成 18 字节数据。
    """
    share_code = share_code.strip()

    if not SHARECODE_PATTERN.fullmatch(share_code):
        raise ValueError("无效的分享码格式")

    code = share_code.replace("CSGO", "").replace("-", "")
    chars = list(reversed(code))

    total = 0
    for ch in chars:
        idx = DICTIONARY.find(ch)
        if idx < 0:
            raise ValueError(f"分享码里包含非法字符: {ch}")
        total = total * BASE + idx

    # TypeScript 实现里固定 padStart(36, '0')，也就是 18 字节
    hex_str = f"{total:036x}"
    return [int(hex_str[i:i + 2], 16) for i in range(0, 36, 2)]


def decode_crosshair_share_code(share_code: str) -> Crosshair:
    """
    解码 CS2/CSGO 准星分享码。
    """
    b = share_code_to_bytes(share_code)

    # 校验：第一个字节应等于后面所有字节之和 % 256
    checksum = sum(b[1:]) % 256
    if b[0] != checksum:
        raise ValueError("分享码校验失败，不是有效的准星码")

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


def crosshair_to_convars(crosshair: Crosshair, one_line: bool = False) -> str:
    """
    转成可直接粘贴到游戏控制台里的命令。
    """
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


if __name__ == "__main__":
    code = input("请输入准星分享码: ").strip()

    try:
        ch = decode_crosshair_share_code(code)
        print("\n=== 解码结果 ===")
        for k, v in asdict(ch).items():
            print(f"{k}: {v}")

        print("\n=== 控制台命令 ===")
        print(crosshair_to_convars(ch))

        print("\n=== 单行版本（适合一次性粘贴） ===")
        print(crosshair_to_convars(ch, one_line=True))

    except Exception as e:
        print(f"错误: {e}")