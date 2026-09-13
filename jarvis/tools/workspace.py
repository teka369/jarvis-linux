from __future__ import annotations

import html as htmlmod
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from ..core.permissions import Capability
from ..safety import assert_safe_path
from .base import Tool
from .desktop_control import extra_desktop_tools


def extra_tools() -> list[Tool]:
    return [
        Tool("mkdir", "Crea una carpeta dentro del home.", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, [Capability.WRITE], _mkdir),
        Tool("move_path", "Mueve o renombra un archivo/carpeta del home.", {"type": "object", "properties": {"src": {"type": "string"}, "dst": {"type": "string"}}, "required": ["src", "dst"]}, [Capability.WRITE], _move),
        Tool("copy_path", "Copia un archivo o carpeta del home.", {"type": "object", "properties": {"src": {"type": "string"}, "dst": {"type": "string"}}, "required": ["src", "dst"]}, [Capability.WRITE], _copy),
        Tool("find_files", "Busca archivos por nombre en una carpeta del home.", {"type": "object", "properties": {"root": {"type": "string"}, "name": {"type": "string"}}, "required": ["name"]}, [Capability.READ], _find),
        Tool("web_search", "Busca en DuckDuckGo y devuelve títulos y enlaces.", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, [Capability.NETWORK], _web),
        Tool("pacman_search", "Busca paquetes en pacman/CachyOS.", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, [Capability.READ, Capability.SYSTEM], _pacman_search),
        Tool("pacman_install", "Instala un paquete oficial con pacman. Requiere confirmed=true.", {"type": "object", "properties": {"package": {"type": "string"}, "confirmed": {"type": "boolean"}}, "required": ["package"]}, [Capability.EXECUTE, Capability.SYSTEM, Capability.DESTRUCTIVE], _pacman_install),
        Tool("open_editor", "Abre un archivo o carpeta en VS Code, Cursor o Kate.", {"type": "object", "properties": {"path": {"type": "string"}, "editor": {"type": "string"}}, "required": ["path"]}, [Capability.EXECUTE], _open_editor),
        Tool("scaffold_html", "Crea una carpeta con index.html y la abre en el editor.", {"type": "object", "properties": {"path": {"type": "string"}, "title": {"type": "string"}}, "required": ["path"]}, [Capability.WRITE, Capability.EXECUTE], _scaffold),
    ] + extra_desktop_tools()


def _mkdir(args: dict[str, Any], _s: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    path.mkdir(parents=True, exist_ok=True)
    return f"Carpeta lista: {path}"


def _move(args: dict[str, Any], _s: Any) -> str:
    src = assert_safe_path(str(args.get("src") or ""))
    dst = assert_safe_path(str(args.get("dst") or ""))
    if not src.exists():
        return f"No existe {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"Moví {src} → {dst}"


def _copy(args: dict[str, Any], _s: Any) -> str:
    src = assert_safe_path(str(args.get("src") or ""))
    dst = assert_safe_path(str(args.get("dst") or ""))
    if not src.exists():
        return f"No existe {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    return f"Copié {src} → {dst}"


def _find(args: dict[str, Any], _s: Any) -> str:
    root = assert_safe_path(str(args.get("root") or Path.home()))
    needle = str(args.get("name") or "").lower()
    hits = []
    for p in root.rglob("*"):
        if needle in p.name.lower():
            hits.append(str(p))
        if len(hits) >= 40:
            break
    return "\n".join(hits) or "Sin resultados."


def _web(args: dict[str, Any], _s: Any) -> str:
    q = str(args.get("query") or "").strip()
    if not q:
        return "Falta la búsqueda."
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(q)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 JarvisLinux"})
    raw = urlopen(req, timeout=12).read().decode("utf-8", "replace")
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', raw, re.S)
    hrefs = re.findall(r'class="result__a"[^>]*href="(.*?)"', raw)
    lines = []
    for title, href in zip(titles, hrefs):
        clean = re.sub("<.*?>", "", title)
        lines.append(f"- {htmlmod.unescape(clean).strip()}\n  {htmlmod.unescape(href)}")
        if len(lines) >= 6:
            break
    return "\n".join(lines) or "Sin resultados."


def _pacman_search(args: dict[str, Any], _s: Any) -> str:
    q = str(args.get("query") or "").strip()
    if not shutil.which("pacman"):
        return "No está pacman."
    out = subprocess.run(["pacman", "-Ss", q], capture_output=True, text=True, timeout=25)
    return (out.stdout or out.stderr or "Sin paquetes.")[:1500]


def _pacman_install(args: dict[str, Any], _s: Any) -> str:
    pkg = re.sub(r"[^a-zA-Z0-9_+.-]", "", str(args.get("package") or ""))
    if not pkg:
        return "Paquete inválido."
    cmd = ["pacman", "-S", "--needed", "--noconfirm", pkg]
    if os_geteuid() != 0:
        cmd = ["sudo", "-n"] + cmd
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    text = (out.stdout or "") + (out.stderr or "")
    if out.returncode != 0:
        return f"No pude instalar {pkg}.\n{text[-700:]}"
    return f"Instalé {pkg}."


def os_geteuid() -> int:
    import os
    return os.geteuid()


def _open_editor(args: dict[str, Any], _s: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    pref = str(args.get("editor") or "").strip()
    for name in ([pref] if pref else []) + ["code", "cursor", "kate", "kwrite"]:
        if name and shutil.which(name):
            subprocess.Popen([name, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abrí {path} con {name}"
    return "No encontré VS Code, Cursor ni Kate."


def _scaffold(args: dict[str, Any], settings: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    path.mkdir(parents=True, exist_ok=True)
    title = str(args.get("title") or path.name)
    (path / "index.html").write_text(
        f"<!doctype html>\n<html lang=es><meta charset=utf-8><title>{title}</title>"
        f"<body><h1>{title}</h1><p>Creado por Jarvis.</p></body></html>\n",
        encoding="utf-8",
    )
    _open_editor({"path": str(path)}, settings)
    return f"Proyecto HTML en {path}"
