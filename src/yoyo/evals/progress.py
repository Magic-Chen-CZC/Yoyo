from __future__ import annotations

# progress.py 负责把评测进度写成 JSON 文件，方便外部查看“现在跑到哪里了”。
import json
from pathlib import Path


def write_progress(path: str | Path, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
