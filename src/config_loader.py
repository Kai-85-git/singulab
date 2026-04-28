"""yaml config の階層読み込み(extends)とディープマージ。

Phase 3-1 で導入。`config/base.yaml` を継承する `scenario_*.yaml` の
仕組みを支える。
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict

import yaml


def load_config(path: str) -> Dict[str, Any]:
    """yaml を読み込み、`extends` キーがあれば再帰的にマージ。

    `extends` の値は **読み込んでいるファイルからの相対パス** を想定。
    """
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if "extends" in cfg:
        base_ref = cfg.pop("extends")
        if not os.path.isabs(base_ref):
            base_path = os.path.join(os.path.dirname(os.path.abspath(path)), base_ref)
        else:
            base_path = base_ref
        base = load_config(base_path)
        cfg = deep_merge(base, cfg)

    return cfg


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """dict を再帰的にマージ。

    - dict 同士なら再帰
    - リストやスカラは override で置き換え
    """
    result = copy.deepcopy(base)
    for k, v in override.items():
        if (
            k in result
            and isinstance(result[k], dict)
            and isinstance(v, dict)
        ):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result
