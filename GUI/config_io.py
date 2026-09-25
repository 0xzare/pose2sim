# -*- coding: utf-8 -*-
"""Load/save helpers for Config.toml + new-project scaffolding."""
from __future__ import annotations
import shutil
from copy import deepcopy
from pathlib import Path


def _rtoml():
    try:
        import rtoml
        return rtoml
    except ImportError:
        return None


def template_path() -> Path:
    return Path(__file__).resolve().parent.parent / "Pose2Sim" / "Demo_SinglePerson" / "Config.toml"


def load_config(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        tpl = template_path()
        if tpl.is_file():
            return load_config(tpl)
        return {}
    rt = _rtoml()
    if rt is None:
        return {}
    try:
        data = rt.load(p)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_dotted(cfg: dict, dotted: str, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_dotted(cfg: dict, dotted: str, value):
    parts = dotted.split(".")
    cur = cfg
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def save_config(path: str | Path, cfg: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # project_dir must stay '.' (relative to the project folder)
    proj = cfg.get("project")
    if isinstance(proj, dict):
        proj["project_dir"] = "."
    rt = _rtoml()
    if rt is None:
        raise RuntimeError("rtoml is not installed")
    text = rt.dumps(cfg)
    p.write_text(text, encoding="utf-8")


def parse_text_value(raw: str):
    """Parse a text field: 'auto', numbers, bools, [a,b] lists."""
    s = raw.strip()
    if s.lower() in ("auto", "all", "true", "false", "none"):
        low = s.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        if low == "none":
            return None
        return low
    try:
        if "," in s.strip("[]"):
            inner = s.strip().strip("[]")
            return [float(x) if "." in x else int(x) for x in inner.split(",") if x.strip()]
    except Exception:
        pass
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def format_value(v) -> str:
    if v is None:
        return "none"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ",".join(format_value(x) for x in v) + "]"
    return str(v)


VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".mpg", ".mpeg"}

INNER_FOLDER_NAMES = {"videos", "calibration", "calib"}


def validate_project(proj: str | Path) -> dict:
    """Check a project folder. Returns {"missing": [...], "suggest_parent": bool}.

    missing codes: "config", "videos", "calib".
    """
    p = Path(proj).expanduser()
    missing: list[str] = []
    if not (p / "Config.toml").is_file():
        missing.append("config")
    vids = list((p / "videos").glob("*.*")) if (p / "videos").is_dir() else []
    if not vids:
        n = sum(1 for t in p.glob("Trial_*/videos/*.*"))
        if not n:
            # loose videos directly in the folder also count
            loose = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS] if p.is_dir() else []
            if not loose:
                missing.append("videos")
    cal_ok = calibration_status(p)["ok"]
    if not cal_ok and calibration_status(p.parent)["ok"]:
        cal_ok = True
    if not cal_ok:
        # a loose calibration file next to the folder also counts
        if not _find_calib_file(p):
            missing.append("calib")
    return {
        "missing": missing,
        "suggest_parent": p.name.lower() in INNER_FOLDER_NAMES,
    }


def _is_usable_calib_file(f: Path) -> bool:
    # NOTE: Config.toml must never count — a stray copy of it once poisoned
    # batch detection (a "trial" called calibration with no videos).
    if not f.is_file():
        return False
    if f.name.lower() in ("config.toml", "logs.txt"):
        return False
    if _guess_convert_from(f):
        return True
    return f.suffix.lower() == ".toml" and f.name.lower().startswith("calib")


def calibration_status(root: str | Path) -> dict:
    """Check <root>/calibration for a usable file. Returns {"ok", "found"}."""
    cdir = Path(root) / "calibration"
    found = None
    if cdir.is_dir():
        for f in sorted(cdir.iterdir()):
            if _is_usable_calib_file(f):
                found = f
                break
    if found is None and _is_calculate_ready(root):
        found = cdir
    return {"ok": found is not None, "found": found}


def _is_calculate_ready(root: str | Path) -> bool:
    """True when calibration/ has board material for a from-scratch run."""
    cdir = Path(root) / "calibration"
    intd = cdir / "intrinsics"
    extd = cdir / "extrinsics"
    if not intd.is_dir() or not extd.is_dir():
        return False
    cams = [d for d in intd.iterdir() if d.is_dir() and _list_images(d)]
    exts = _list_images(extd)
    return len(cams) >= 1 and len(exts) >= 1


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv"}


def _list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTS],
        key=lambda p: p.name,
    )


def organize_board(root: str | Path, cams: dict[int, dict]) -> Path:
    """Copy checkerboard material into calibration/intrinsics + extrinsics.

    cams: {idx: {"intrinsics": [paths...], "extrinsics": path|None}}.
    Returns the calibration dir.
    """
    r = Path(root)
    intd = r / "calibration" / "intrinsics"
    extd = r / "calibration" / "extrinsics"
    intd.mkdir(parents=True, exist_ok=True)
    extd.mkdir(parents=True, exist_ok=True)
    for idx in sorted(cams):
        data = cams[idx]
        cname = f"cam{idx + 1:02d}"
        cfold = intd / cname
        cfold.mkdir(parents=True, exist_ok=True)
        for src in data.get("intrinsics", []):
            src = Path(src)
            dst = cfold / src.name
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
        ext = data.get("extrinsics")
        if ext:
            ext = Path(ext)
            if ext.is_file():
                dst = extd / f"{cname}{ext.suffix.lower()}"
                if not dst.exists():
                    shutil.copy2(ext, dst)
    return r / "calibration"


def calibration_result(root: str | Path):
    """Return an existing Calib*.toml result file, or None.

    3D needs to know where the cameras are — that math can't be removed.
    But it only has to be done ONCE per camera setup: if a Calib*.toml
    already exists, the calibration step can be skipped entirely.
    """
    cdir = Path(root) / "calibration"
    if not cdir.is_dir():
        return None
    cands = sorted(cdir.glob("Calib*.toml"))
    return cands[-1] if cands else None


def _find_calib_file(folder: Path):
    """Look for a known calibration file in folder (not recursive)."""
    if not folder.is_dir():
        return None
    for f in folder.iterdir():
        if not f.is_file():
            continue
        n = f.name.lower()
        if n.startswith("calib") and f.suffix.lower() == ".toml":
            return f
        if n.endswith((".qca.txt", ".xcp", ".pickle")):
            return f
        if n in ("intri.yml", "extri.yml"):
            return f
    return None


def _guess_convert_from(calib_file: Path) -> str | None:
    n = calib_file.name.lower()
    if n.endswith(".qca.txt"):
        return "qualisys"
    if n.endswith(".xcp"):
        return "vicon"
    if n.endswith(".pickle"):
        return "opencap"
    if n in ("intri.yml", "extri.yml"):
        return "easymocap"
    if calib_file.suffix.lower() == ".toml":
        return "caliscope"
    return None


def auto_setup_project(start: str | Path) -> dict:
    """Turn a videos folder (or messy folder) into a runnable project.

    - Walks up to find an existing project root (Config.toml nearby).
    - Otherwise scaffolds in place: moves loose videos into videos/,
      creates calibration/, writes a template Config.toml with
      auto-detected calibration settings.
    Returns {"root": Path, "fixed": [...], "still_missing": [...]}.
    fixed/still_missing use the validate_project codes.
    """
    s = Path(start).expanduser().resolve()
    fixed: list[str] = []

    # 1. already valid → nothing to do
    if s.is_dir() and not validate_project(s)["missing"]:
        return {"root": s, "fixed": fixed, "still_missing": []}

    # 2. walk up (covers picking videos/ or a trial videos dir)
    cur = s if s.is_dir() else s.parent
    for _ in range(3):
        if (cur / "Config.toml").is_file() or _find_calib_file(cur):
            if not validate_project(cur)["missing"]:
                fixed.append("picked-parent")
                return {"root": cur, "fixed": fixed, "still_missing": []}
            break
        nxt = cur.parent
        if nxt == cur:
            break
        cur = nxt
    # inner folder → parent is usually the project
    if s.name.lower() in INNER_FOLDER_NAMES and s.parent.is_dir():
        par = s.parent
        if not validate_project(par)["missing"]:
            fixed.append("picked-parent")
            return {"root": par, "fixed": fixed, "still_missing": []}
        # parent + session root (batch trial): calib may live one level up
        if (par.parent / "Config.toml").is_file() or (par.parent / "calibration").is_dir():
            fixed.append("picked-parent")
            return {"root": par, "fixed": fixed,
                    "still_missing": validate_project(par)["missing"]}

    # 3. scaffold in place: loose videos → videos/
    root = s if s.is_dir() else s.parent
    vdir = root / "videos"
    loose = [f for f in root.iterdir()
             if f.is_file() and f.suffix.lower() in VIDEO_EXTS] if root.is_dir() else []
    if loose and not vdir.is_dir():
        vdir.mkdir(parents=True, exist_ok=True)
        for f in loose:
            try:
                shutil.move(str(f), str(vdir / f.name))
                fixed.append("moved-videos")
            except Exception:
                pass
    cdir = root / "calibration"
    cdir.mkdir(parents=True, exist_ok=True)

    # calibration file lying around? move it in
    if not any(cdir.iterdir()):
        for cand in [root, root.parent]:
            found = _find_calib_file(cand)
            if found and cand != cdir:
                try:
                    shutil.move(str(found), str(cdir / found.name))
                    fixed.append("moved-calib")
                    break
                except Exception:
                    pass

    # config from template, with auto-detected calibration source
    if not (root / "Config.toml").is_file():
        cfg = load_config(template_path())
        calib_files = list(cdir.glob("*")) if cdir.is_dir() else []
        guess = None
        for f in calib_files:
            if f.is_file():
                guess = _guess_convert_from(f)
                if guess:
                    break
        if guess:
            try:
                set_dotted(cfg, "calibration.calibration_type", "convert")
                set_dotted(cfg, "calibration.convert.convert_from", guess)
                fixed.append(f"calib-{guess}")
            except Exception:
                pass
        try:
            save_config(root / "Config.toml", cfg)
            fixed.append("wrote-config")
        except Exception:
            pass

    return {"root": root, "fixed": fixed,
            "still_missing": validate_project(root)["missing"]}


def _list_videos(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS],
        key=lambda p: p.name,
    )


def setup_from_videos(videos_dir: str | Path) -> dict:
    """Start ONLY from a videos folder. Returns project root + findings.

    - If a `videos/` folder is picked, root is its parent.
    - If a folder with loose videos (or a videos/ subdir) is picked, root is itself
      (loose videos are moved into videos/).
    - Searches root, root/calibration and root's parent for a calibration file.
    Returns {"root": Path, "videos": [Path...], "calib": Path|None}.
    """
    v = Path(videos_dir).expanduser().resolve()
    if v.name.lower() == "videos" and v.is_dir():
        root = v.parent
        videos = _list_videos(v)
    else:
        root = v
        videos = _list_videos(root / "videos")
        if not videos:
            loose = _list_videos(root)
            if loose:
                vdir = root / "videos"
                vdir.mkdir(parents=True, exist_ok=True)
                moved = []
                for f in loose:
                    try:
                        shutil.move(str(f), str(vdir / f.name))
                        moved.append(vdir / f.name)
                    except Exception:
                        pass
                videos = moved or _list_videos(vdir)
    calib = None
    cdir = root / "calibration"
    if cdir.is_dir():
        for f in sorted(cdir.iterdir()):
            if _is_usable_calib_file(f):
                calib = f
                break
    if calib is None:
        calib = _find_calib_file(root)
    if calib is None:
        calib = _find_calib_file(root.parent)
        if calib is None and (root.parent / "calibration").is_dir():
            for f in sorted((root.parent / "calibration").iterdir()):
                if f.is_file():
                    calib = f
                    break
    return {"root": root, "videos": videos, "calib": calib}


def place_calib(root: str | Path, src: str | Path) -> Path:
    """Copy a calibration file/folder content into <root>/calibration. Returns dest dir."""
    r = Path(root)
    cdir = r / "calibration"
    cdir.mkdir(parents=True, exist_ok=True)
    s = Path(src)
    if s.is_file():
        dst = cdir / s.name
        if s.resolve() != dst.resolve() and not dst.exists():
            shutil.copy2(s, dst)
    elif s.is_dir():
        for f in s.iterdir():
            if f.is_file() and f.name.lower() not in ("config.toml", "logs.txt"):
                dst = cdir / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
    return cdir


def purge_stray_configs(root: str | Path) -> list[str]:
    """Remove Config.toml files wrongly placed inside videos/calibration.

    Such strays break Pose2Sim's batch detection (it walks for Config.toml
    and mistakes e.g. calibration/ for a trial). Returns removed rel paths.
    """
    r = Path(root)
    removed = []
    for sub in ("videos", "calibration", "calib"):
        d = r / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.name.lower() == "config.toml":
                try:
                    f.unlink()
                    removed.append(f"{sub}/Config.toml")
                except Exception:
                    pass
    return removed


def build_config_for(root: str | Path, *, multi_person: bool, mode: str,
                     simple_model: bool, calib_file: str | Path | None = None,
                     board: dict | None = None) -> dict:
    """Write Config.toml at <root> from wizard answers. Returns cfg.

    Loads the existing Config.toml when present (so advanced edits survive)
    and only updates the wizard keys; otherwise starts from the template.
    board (optional): {"corners": [w,h], "square_mm": int} → switches the
    calibration section to from-scratch (calculate/board) mode.
    """
    r = Path(root)
    existing = r / "Config.toml"
    cfg = load_config(existing) if existing.is_file() else load_config(template_path())
    set_dotted(cfg, "project.multi_person", bool(multi_person))
    set_dotted(cfg, "pose.mode", mode)
    set_dotted(cfg, "kinematics.use_simple_model", bool(simple_model))
    if board:
        corners = board.get("corners", [4, 7])
        sq = board.get("square_mm", 60)
        set_dotted(cfg, "calibration.calibration_type", "calculate")
        set_dotted(cfg, "calibration.calculate.intrinsics.intrinsics_corners_nb", list(corners))
        set_dotted(cfg, "calibration.calculate.intrinsics.intrinsics_square_size", int(sq))
        set_dotted(cfg, "calibration.calculate.extrinsics.extrinsics_method", "board")
        set_dotted(cfg, "calibration.calculate.extrinsics.board.extrinsics_corners_nb", list(corners))
        set_dotted(cfg, "calibration.calculate.extrinsics.board.extrinsics_square_size", int(sq))
    elif calib_file:
        guess = _guess_convert_from(Path(calib_file))
        if guess:
            set_dotted(cfg, "calibration.calibration_type", "convert")
            set_dotted(cfg, "calibration.convert.convert_from", guess)
    save_config(r / "Config.toml", cfg)
    return cfg


def scaffold_project(dest: str | Path, video_files: list[str | Path],
                     calib_sources: list[str | Path]) -> dict:
    """Create <dest>/videos + <dest>/calibration and copy inputs.

    Returns {"videos_copied": int, "calib_copied": int}.
    Never overwrites an existing Config.toml.
    """
    d = Path(dest)
    vdir = d / "videos"
    cdir = d / "calibration"
    vdir.mkdir(parents=True, exist_ok=True)
    cdir.mkdir(parents=True, exist_ok=True)
    nv = nc = 0
    for vf in video_files:
        src = Path(vf)
        if src.is_file() and src.suffix.lower() in VIDEO_EXTS:
            dst = vdir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                nv += 1
    for cf in calib_sources:
        src = Path(cf)
        if src.is_file():
            dst = cdir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                nc += 1
        elif src.is_dir():
            for f in src.iterdir():
                if f.is_file():
                    dst = cdir / f.name
                    if not dst.exists():
                        shutil.copy2(f, dst)
                        nc += 1
    if not (d / "Config.toml").is_file():
        tpl = template_path()
        if tpl.is_file():
            cfg = load_config(tpl)
            save_config(d / "Config.toml", cfg)
    return {"videos_copied": nv, "calib_copied": nc}
