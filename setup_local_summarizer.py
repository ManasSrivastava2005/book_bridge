"""Explicit one-time download; inference itself always uses local files only."""
import os
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
from app.config import LOCAL_SUMMARY_MODEL_NAME, LOCAL_SUMMARY_MODEL_PATH


if __name__ == '__main__':
    # Resolve once and record exact revision for reproducibility.
    revision = HfApi().model_info(LOCAL_SUMMARY_MODEL_NAME).sha
    path = snapshot_download(
        LOCAL_SUMMARY_MODEL_NAME, revision=revision,
        local_dir=LOCAL_SUMMARY_MODEL_PATH,
        allow_patterns=['config.json', 'generation_config.json', 'model.safetensors',
                        'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json',
                        'spiece.model', 'README.md', 'LICENSE*'],
        max_workers=2,
    )
    Path(path, 'bookbridge_revision.txt').write_text(revision, encoding='utf-8')
    print({'model': LOCAL_SUMMARY_MODEL_NAME, 'revision': revision,
           'bytes': sum(p.stat().st_size for p in Path(path).iterdir() if p.is_file())})
