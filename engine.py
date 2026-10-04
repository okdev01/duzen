"""Preview-first, same-volume Windows file organization with persistent undo."""
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import stat
import time
from uuid import uuid4


GROUPS = {
    "Fotoğraflar": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".tif", ".tiff"},
    "Belgeler": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".csv", ".pptx", ".odt", ".md"},
    "Videolar": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Müzikler": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Arşivler": {".zip", ".7z", ".rar", ".tar", ".gz"},
}


def identity(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or path.is_symlink():
        raise ValueError("Normal dosya değil")
    if getattr(s, "st_file_attributes", 0) & 0x400:
        raise ValueError("Bağlantı dosyaları taşınmaz")
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns]


def safe_folder(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("Bağlantı klasörleri desteklenmiyor")
    return path


def category(path):
    return next((group for group, exts in GROUPS.items() if path.suffix.lower() in exts), None)


@dataclass(frozen=True)
class Move:
    source: str
    destination: str
    identity: list
    category: str


def plan(folder):
    root = safe_folder(Path(folder).absolute())
    if not root.is_dir():
        raise ValueError("Klasör bulunamadı")
    moves, skipped = [], 0
    reserved = set()
    for path in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        group = category(path)
        try:
            info = identity(path)
            attrs = getattr(path.lstat(), "st_file_attributes", 0)
            if not group or path.name.startswith(".") or attrs & 6:
                skipped += 1
                continue
            target_dir = safe_folder(root / group)
            if target_dir.exists() and not target_dir.is_dir():
                skipped += 1
                continue
            destination = target_dir / path.name
            index = 1
            while destination.exists() or str(destination).casefold() in reserved:
                destination = target_dir / f"{path.stem} ({index}){path.suffix}"
                index += 1
            reserved.add(str(destination).casefold())
            moves.append(Move(str(path), str(destination), info, group))
        except (OSError, ValueError):
            skipped += 1
    return moves, skipped


def write_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def move_exclusive(source, destination):
    """Never replace an existing destination, including after a preview race."""
    if os.name == "nt":
        os.rename(source, destination)  # Windows rename fails if target exists.
    else:
        os.link(source, destination, follow_symlinks=False)
        os.unlink(source)


def apply(moves, history_dir):
    journal = Path(history_dir) / f"{time.time_ns()}-{uuid4().hex}.json"
    records = [{**asdict(move), "state": "pending", "error": ""} for move in moves]
    document = {"version": 1, "created": time.time(), "records": records}
    write_atomic(journal, document)
    for record in records:
        source, destination = Path(record["source"]), Path(record["destination"])
        try:
            safe_folder(source.parent)
            if destination.parent.parent != source.parent or destination.parent.name != record["category"]:
                raise ValueError("Geçersiz hedef klasör")
            safe_folder(destination.parent)
            if identity(source) != record["identity"]:
                raise ValueError("Önizlemeden sonra dosya değişti; yeniden tarayın")
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                raise FileExistsError("Hedef dosya mevcut; üzerine yazılmadı")
            record["state"] = "moving"
            write_atomic(journal, document)
            move_exclusive(source, destination)
            record["state"] = "moved"
        except (OSError, ValueError) as exc:
            record["state"], record["error"] = "failed", str(exc)
        write_atomic(journal, document)
    return journal, records


def undo(journal):
    path = Path(journal)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("Desteklenmeyen işlem kaydı")
    for record in reversed(document["records"]):
        if record["state"] not in {"moved", "moving", "undoing", "conflict"}:
            continue
        source, destination = Path(record["source"]), Path(record["destination"])
        try:
            safe_folder(source.parent)
            safe_folder(destination.parent)
            if destination.parent.parent != source.parent or destination.parent.name not in GROUPS:
                raise ValueError("Geçersiz işlem kaydı")
            if source.exists():
                if not destination.exists() and identity(source) == record["identity"]:
                    record["state"] = "undone"  # Crash before move or after undo.
                else:
                    raise FileExistsError("Eski konum dolu; dosyalara dokunulmadı")
            else:
                if identity(destination) != record["identity"]:
                    raise ValueError("Taşınan dosya değişmiş; güvenlik için atlandı")
                record["state"] = "undoing"
                write_atomic(path, document)
                move_exclusive(destination, source)
                record["state"] = "undone"
            record["error"] = ""
        except (OSError, ValueError) as exc:
            record["state"], record["error"] = "conflict", str(exc)
        write_atomic(path, document)
    return document["records"]


def latest_pending(history_dir):
    for path in sorted(Path(history_dir).glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if any(r["state"] in {"moved", "moving", "undoing", "conflict"} for r in data["records"]):
                return path
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None
