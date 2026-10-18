#!/usr/bin/env python3
"""把 anitabi 的圣地巡礼地图导入 Google My Maps。

用法：
    python anitabi_GoogleMaps.py                 # 交互模式，逐个输入 bangumi_id
    python anitabi_GoogleMaps.py 331884          # 直接转换一个作品
    python anitabi_GoogleMaps.py 331884 4912     # 一次转换多个作品
    python anitabi_GoogleMaps.py 331884 -o out.kml
    python anitabi_GoogleMaps.py 331884 --offline    # 只用本地缓存 {id}.json

生成的 .kml 可以直接在 https://www.google.com/maps/d/ 里“创建新地图 → 导入”。

只依赖 Python 标准库（3.8+），不需要安装 requests。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Iterable, Sequence

API_BASE = "https://api.anitabi.cn"
USER_AGENT = "anitabi-GoogleMaps/2.0 (+https://github.com/yanxijian/anitabi_GoogleMaps)"
KML_NAMESPACE = "http://www.opengis.net/kml/2.2"

DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 2
FALLBACK_NAME = "未命名地点"

# 允许测试替换真正的 HTTP 调用与等待。
_open: Callable[..., Any] = urllib.request.urlopen
_sleep: Callable[[float], None] = time.sleep


class AnitabiError(RuntimeError):
    """网络或数据格式错误。"""


# --------------------------------------------------------------------------- #
# 网络
# --------------------------------------------------------------------------- #

def fetch_json(url: str, *, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> Any:
    """读取一个 JSON 接口，失败时按指数退避重试。"""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with _open(request, timeout=timeout) as response:
                payload = response.read()
            return json.loads(payload.decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                _sleep(min(2.0, 0.5 * (attempt + 1)))

    raise AnitabiError(f"请求失败: {url} ({last_error})")


def load_local(path: str) -> Any:
    """读取浏览器里另存下来的 JSON。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise AnitabiError(f"无法读取本地文件 {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AnitabiError(f"本地文件不是合法 JSON: {path} ({exc})") from exc


def load_points(bangumi_id: str, *, offline: bool, timeout: float, retries: int) -> list[Any]:
    """优先取接口，失败时回退到同目录的 {id}.json。"""
    if not offline:
        try:
            points = fetch_json(
                f"{API_BASE}/bangumi/{urllib.parse.quote(str(bangumi_id))}/points/detail",
                timeout=timeout,
                retries=retries,
            )
            if not isinstance(points, list):
                raise AnitabiError(f"接口返回的不是数组: {type(points).__name__}")
            return points
        except AnitabiError as exc:
            print(f"[!] {exc}", file=sys.stderr)
            print(f"[!] 尝试读取本地 {bangumi_id}.json", file=sys.stderr)

    local_path = f"{bangumi_id}.json"
    if not os.path.isfile(local_path):
        if offline:
            raise AnitabiError(f"--offline 模式下找不到 {local_path}")
        raise AnitabiError(f"没有可用的数据：接口不可用，且找不到 {local_path}")
    points = load_local(local_path)
    if not isinstance(points, list):
        raise AnitabiError(f"本地文件不是数组: {local_path}")
    return points


def load_title(bangumi_id: str, *, offline: bool, timeout: float, retries: int) -> str:
    """作品标题；取不到时退回 bangumi_id。"""
    if not offline:
        try:
            info = fetch_json(
                f"{API_BASE}/bangumi/{urllib.parse.quote(str(bangumi_id))}/lite",
                timeout=timeout,
                retries=retries,
            )
            if isinstance(info, dict):
                for key in ("cn", "title", "name"):
                    value = info.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except AnitabiError as exc:
            print(f"[!] {exc}", file=sys.stderr)

    if os.path.isfile(f"{bangumi_id}.json"):
        try:
            cached = load_local(f"{bangumi_id}.json")
            if isinstance(cached, dict):
                for key in ("cn", "title", "name"):
                    value = cached.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except AnitabiError:
            pass

    return str(bangumi_id)


# --------------------------------------------------------------------------- #
# KML
# --------------------------------------------------------------------------- #

def xml_escape(text: str) -> str:
    """元素文本/属性值的转义。"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def xml_attr_escape(text: str) -> str:
    return xml_escape(text).replace('"', "&quot;")


def cdata_escape(text: str) -> str:
    """把 ]] > 拆开，避免提前结束 CDATA。"""
    return str(text).replace("]]>", "]]]]><![CDATA[>")


def _coordinate(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def build_kml(points: Iterable[Any], title: str) -> tuple[str, int, int]:
    """由点位列表生成 KML 文本。

    返回 (kml, 有效点数, 跳过数)。anitabi 的 geo 是 [纬度, 经度]，
    KML 的 <coordinates> 是 "经度,纬度,高度"，这里做一次交换。
    """
    placemarks: list[str] = []
    used = 0
    skipped = 0

    for item in points:
        if not isinstance(item, dict):
            skipped += 1
            continue

        geo = item.get("geo")
        if not isinstance(geo, (list, tuple)) or len(geo) < 2:
            skipped += 1
            continue

        latitude = _coordinate(geo[0])
        longitude = _coordinate(geo[1])
        if latitude is None or longitude is None:
            skipped += 1
            continue
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            skipped += 1
            continue

        name = item.get("cn") or item.get("name") or FALLBACK_NAME
        point_id = item.get("id", "")
        image = item.get("image") or ""

        description = f'<img src="{xml_attr_escape(image)}" width="200" />'
        if point_id != "":
            description += f"<br/>ID: {xml_escape(point_id)}"

        placemarks.append(
            "    <Placemark>\n"
            f"      <name>{xml_escape(name)}</name>\n"
            f"      <description><![CDATA[{cdata_escape(description)}]]></description>\n"
            "      <Point>\n"
            f"        <coordinates>{longitude:.6f},{latitude:.6f},0</coordinates>\n"
            "      </Point>\n"
            "    </Placemark>"
        )
        used += 1

    header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<kml xmlns="{KML_NAMESPACE}">\n'
        "  <Document>\n"
        f"    <name>{xml_escape(title)}</name>\n"
    )
    body = "\n".join(placemarks)
    footer = "\n  </Document>\n</kml>\n"
    kml = header + (body + "\n" if body else "") + footer
    return kml, used, skipped


_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename(name: str, *, max_length: int = 120) -> str:
    """把作品名变成跨平台可用的文件名（去掉 Windows 非法字符/保留名）。"""
    cleaned = _INVALID_FILENAME.sub("_", str(name))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(". ")
    if not cleaned:
        cleaned = "bangumi"
    if cleaned.split(".")[0].upper() in _RESERVED_NAMES:
        cleaned = "_" + cleaned
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")
    return cleaned


def write_text(path: str, content: str) -> None:
    """先写临时文件再替换，避免中断后留下半个文件。"""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    os.replace(temporary, path)


# --------------------------------------------------------------------------- #
# 命令行
# --------------------------------------------------------------------------- #

def convert_one(
    bangumi_id: str,
    *,
    output: str | None,
    outdir: str | None,
    offline: bool,
    timeout: float,
    retries: int,
) -> str:
    points = load_points(bangumi_id, offline=offline, timeout=timeout, retries=retries)
    title = load_title(bangumi_id, offline=offline, timeout=timeout, retries=retries)

    kml, used, skipped = build_kml(points, title)
    if used == 0:
        raise AnitabiError(f"{bangumi_id} 没有任何带坐标的点位")

    if output:
        path = output
    else:
        filename = f"{safe_filename(title)}.kml"
        path = os.path.join(outdir, filename) if outdir else filename

    write_text(path, kml)
    note = f"，跳过 {skipped} 个无效点位" if skipped else ""
    print(f"[+] {bangumi_id} -> {path}（{used} 个点位{note}）")
    return path


def _configure_console() -> None:
    """让中文提示在 Windows 控制台和重定向下都不会抛 UnicodeEncodeError。

    Windows 默认代码页不是 UTF-8 时，print 中文会直接抛异常；
    这里先尝试把控制台切到 UTF-8，再给输出流兜一个 errors="replace"。
    """
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:  # 没有控制台（重定向/服务）时忽略
            pass

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anitabi_GoogleMaps.py",
        description="把 anitabi 圣地巡礼地图导出成 Google My Maps 可导入的 KML。",
    )
    parser.add_argument("bangumi_ids", nargs="*", help="bangumi_id，可给多个；不给则进入交互模式")
    parser.add_argument("-o", "--output", help="输出文件路径（只处理一个作品时有效）")
    parser.add_argument("--outdir", help="输出目录，默认当前目录")
    parser.add_argument("--offline", action="store_true", help="只用本地 {id}.json，不访问网络")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"请求超时秒数（默认 {DEFAULT_TIMEOUT:g}）")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help=f"失败重试次数（默认 {DEFAULT_RETRIES}）")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console()
    args = build_parser().parse_args(argv)
    ids = list(args.bangumi_ids)

    if args.output and len(ids) > 1:
        print("[-] -o 只能配合单个 bangumi_id 使用", file=sys.stderr)
        return 2

    failures = 0

    if ids:
        for bangumi_id in ids:
            try:
                convert_one(
                    bangumi_id,
                    output=args.output,
                    outdir=args.outdir,
                    offline=args.offline,
                    timeout=args.timeout,
                    retries=args.retries,
                )
            except AnitabiError as exc:
                failures += 1
                print(f"[-] {bangumi_id}: {exc}", file=sys.stderr)
        return 0 if failures == 0 else 1

    # 交互模式：保持老用法的节奏。
    print("输入 bangumi_id 后回车（直接回车或 q 退出）。")
    while True:
        try:
            bangumi_id = input("bangumi_id> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not bangumi_id or bangumi_id.lower() in {"q", "quit", "exit"}:
            break
        try:
            convert_one(
                bangumi_id,
                output=None,
                outdir=args.outdir,
                offline=args.offline,
                timeout=args.timeout,
                retries=args.retries,
            )
        except AnitabiError as exc:
            failures += 1
            print(f"[-] {bangumi_id}: {exc}", file=sys.stderr)

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
