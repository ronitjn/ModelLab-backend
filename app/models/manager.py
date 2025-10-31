"""Model manager and loaders for ModelLab.

This module provides a simple ModelManager that knows how to locate and
instantiate models by name. It's deliberately lightweight: loaders are
pluggable and the default loader is a stub that returns a mock object.

Place heavier framework-specific loaders (torch/tf) here and keep model
binaries out of git (use `models/` folder, Git LFS, or remote storage).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import subprocess
import shutil
import logging

DEFAULT_MODELS_DIR = Path("./models")


@dataclass
class ModelSpec:
    name: str
    loader: Callable[[Path], Any]
    path: Optional[Path] = None


class ModelManager:
    """Simple in-process model registry/loader.

    Usage:
        from app.models.manager import ModelManager
        mm = ModelManager()
        model = mm.get("model1")

    The manager caches loaded models and uses the registered loader
    to instantiate them. By default a stub loader is registered for
    `model1`, `model2`, `model3` that returns a small callable mock.
    """

    def __init__(self, models_dir: Path = DEFAULT_MODELS_DIR):
        self.models_dir = models_dir
        self._specs: Dict[str, ModelSpec] = {}
        self._instances: Dict[str, Any] = {}

        # Ensure models dir exists (may be gitignored)
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best-effort; failure to create is non-fatal for the scaffold
            pass

        # Register default stubbed models
        for name in ("model1", "model2", "model3"):
            self.register(name, self._stub_loader)

    def register(self, name: str, loader: Callable[[Path], Any], path: Optional[Path] = None) -> None:
        self._specs[name] = ModelSpec(name=name, loader=loader, path=path)

    def register_from_git(self, name: str, git_url: str, path: Optional[Path] = None) -> None:
        """Register a model whose code/weights live in a Git repository.

        The manager will clone the repository into `models_dir / name` when
        `get(name)` is called and the path does not already exist. This is a
        convenience for development; production deployments should fetch
        artifacts during CI or provisioning.
        """

        target_path = path or (self.models_dir / name)

        def _git_loader(model_path: Path) -> Callable[..., str]:
            # Ensure repository is present (lazy clone)
            self._ensure_repo_cloned(model_path, git_url)

            def _run_repo(*args, **kwargs) -> str:
                # Try to use our wav2lip adapter if available; otherwise return path
                try:
                    from app.models.adapters.wav2lip_adapter import run_repo_inference

                    # Expecting kwargs: task_id, video, audio
                    task_id = kwargs.get("task_id") or args[0]
                    video = kwargs.get("video") or (args[1] if len(args) > 1 else None)
                    audio = kwargs.get("audio") or (args[2] if len(args) > 2 else None)

                    if not video or not audio:
                        raise ValueError("video and audio paths required for inference")

                    outfile = str(Path("./models").resolve() / "results" / f"{task_id}_lipsynced.mp4")
                    Path(outfile).parent.mkdir(parents=True, exist_ok=True)

                    run_repo_inference(model_path, video, audio, outfile)
                    return outfile
                except Exception:
                    logging.exception("Repository adapter failed; falling back to stub for %s", model_path)
                    return str(model_path)

            return _run_repo

        self.register(name, _git_loader, path=target_path)

    def _ensure_repo_cloned(self, model_path: Path, git_url: str) -> None:
        """Clone the git repo to model_path if it's not already present.

        Uses the `git` binary if available. This is a best-effort helper for
        development convenience; it raises RuntimeError on failure.
        """

        if model_path.exists() and any(model_path.iterdir()):
            return

        git_bin = shutil.which("git")
        if not git_bin:
            raise RuntimeError("git binary not found on PATH; please install git or clone manually")

        model_path_parent = model_path.parent
        model_path_parent.mkdir(parents=True, exist_ok=True)

        cmd = [git_bin, "clone", git_url, str(model_path)]
        logging.info("Cloning model repo %s -> %s", git_url, model_path)
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to clone {git_url}: {exc}") from exc

    def get(self, name: str) -> Any:
        if name in self._instances:
            return self._instances[name]

        spec = self._specs.get(name)
        if not spec:
            raise KeyError(f"Model not registered: {name}")

        model_path = spec.path or (self.models_dir / name)
        instance = spec.loader(model_path)
        self._instances[name] = instance
        return instance

    # --- example loaders ---
    def _stub_loader(self, model_path: Path) -> Callable[..., str]:
        """Return a tiny stub 'model' that pretends to process inputs.

        This keeps the rest of the codebase runnable without real models.
        """

        def _run_stub(*args, **kwargs) -> str:
            # For a real model this would perform inference and return path
            return f"stub-result-for-{model_path.name}"

        return _run_stub


# Single shared manager instance used by the app
DEFAULT_MANAGER = ModelManager()

# Optional: register an example model from a GitHub repo for convenience.
# This will lazily clone the repo into ./models/model1 when `get("model1")`
# is called. Replace or remove for production use.
try:
    DEFAULT_MANAGER.register_from_git("model1", "https://github.com/instant-high/wav2lip-onnx-HQ")
except Exception:
    # Do not fail import if registration cannot happen in the current env
    pass
