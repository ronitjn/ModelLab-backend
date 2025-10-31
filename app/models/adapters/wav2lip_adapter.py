"""Adapter to run the wav2lip-onnx-HQ repository inference script.

This adapter finds a checkpoint under the repo's `checkpoints/` folder
and invokes `inference_onnxModel.py` as a subprocess. It is a thin
integration layer for development; in production you might import the
repo as a package or rework the repo into reusable functions.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_checkpoint(repo_path: Path) -> Optional[Path]:
    ckpt_dir = repo_path / "checkpoints"
    if not ckpt_dir.exists():
        return None

    # Prefer files with 'wav2lip' in the name, otherwise first .onnx
    onnx_files = list(ckpt_dir.glob("*.onnx"))
    if not onnx_files:
        return None

    for f in onnx_files:
        if "wav2lip" in f.name.lower():
            return f

    return onnx_files[0]


def run_inference(repo_path: Path, checkpoint: Path, face: str, audio: str, outfile: str) -> str:
    """Run the repo's inference script synchronously and return outfile path.

    Raises subprocess.CalledProcessError on failure.
    """
    script = repo_path / "inference_onnxModel.py"
    if not script.exists():
        raise FileNotFoundError(f"inference script not found at {script}")

    python_bin = sys.executable or shutil.which("python")
    cmd = [python_bin, str(script), "--checkpoint_path", str(checkpoint), "--face", str(face), "--audio", str(audio), "--outfile", str(outfile)]

    # Run synchronously; caller should run in a thread if non-blocking required
    subprocess.run(cmd, check=True)
    return outfile


def run_repo_inference(repo_path: Path, face: str, audio: str, outfile: str) -> str:
    ckpt = find_checkpoint(repo_path)
    if not ckpt:
        raise FileNotFoundError(f"No ONNX checkpoint found in {repo_path / 'checkpoints'}")

    return run_inference(repo_path, ckpt, face, audio, outfile)
