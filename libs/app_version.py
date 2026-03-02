# -*- coding: utf-8 -*-
import os
from typing import Optional, Tuple

DEFAULT_APP_VERSION_NUMBER = "2.3.9"
DEFAULT_APP_BUILD = 239


def _read_kv_file(path: str) -> dict:
    cfg = {}
    if not path or not os.path.exists(path):
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except Exception:
        pass
    return cfg


def get_app_version(base_dir: Optional[str] = None) -> Tuple[str, int]:
    """Return (version:str, build:int).

    Priority:
      1) %LOCALAPPDATA%\ZhiMoAI\config.dat
      2) base_dir/.env (dev override only)
      3) DEFAULT_APP_VERSION_NUMBER / DEFAULT_APP_BUILD
    """
    version = DEFAULT_APP_VERSION_NUMBER
    build = DEFAULT_APP_BUILD

    config_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ZhiMoAI")
    config_file = os.path.join(config_dir, "config.dat")
    cfg = _read_kv_file(config_file)

    if base_dir:
        env_path = os.path.join(base_dir, ".env")
        dev_cfg = _read_kv_file(env_path)
        cfg.update(dev_cfg)

    try:
        if "APP_VERSION_NUMBER" in cfg:
            version = str(cfg["APP_VERSION_NUMBER"]).strip()
        if "APP_BUILD" in cfg:
            build = int(str(cfg["APP_BUILD"]).strip())
    except Exception:
        pass

    return version, build
