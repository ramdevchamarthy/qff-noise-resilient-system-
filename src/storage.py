"""
Storage Abstraction Layer for Q-ResQ Quantum Machine Learning System.
Provides resilient, tiered persistence across:
1. Persistent Cloud Object Storage (Vercel Blob / S3-compatible object stores)
2. Local Writable Filesystem (/tmp in serverless environments, data/ in local environments)
3. Bundled Read-Only Project Assets (/var/task/data/ in Vercel)
4. Fast In-Memory LRU Cache for multi-step request pipelines
"""

import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger("qresq.storage")

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_DATA_DIR = ROOT_DIR / "data"

# Cloud Storage Credentials
VERCEL_BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")
S3_BUCKET = os.environ.get("S3_BUCKET") or os.environ.get("AWS_STORAGE_BUCKET_NAME")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT_URL")

# In-Memory Cache for fast cross-request resolution within a runtime
_DATASET_CACHE: Dict[str, Tuple[str, Dict[str, Any]]] = {}
_RUN_CACHE: Dict[str, Dict[str, Any]] = {}
_MODEL_CACHE: Dict[str, Dict[str, Any]] = {}


def _is_dir_writable(path: Path) -> bool:
    """Tests whether a directory path is truly writable on the current filesystem."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe_file = path / f".probe_{os.getpid()}_{int(time.time() * 1000)}"
        with open(probe_file, "w", encoding="utf-8") as f:
            f.write("probe")
        if probe_file.exists():
            probe_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def get_writable_dir(category: str) -> Path:
    """
    Returns a guaranteed writable directory for a given category ('uploads', 'experiments', 'models').
    Prefers project 'data/<category>' if writable (local dev).
    Falls back to '/tmp/qresq_data/<category>' if project directory is read-only (serverless).
    """
    project_dir = BASE_DATA_DIR / category
    if _is_dir_writable(project_dir):
        return project_dir

    # Fallback to system temporary directory (guaranteed writable on Vercel / AWS Lambda)
    temp_dir = Path(tempfile.gettempdir()) / "qresq_data" / category
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_read_dirs(category: str) -> List[Path]:
    """
    Returns all directories where assets for a category might be found:
    1. The writable directory (e.g. /tmp/qresq_data/<category> or data/<category>)
    2. The bundled project directory (e.g. /var/task/data/<category>)
    """
    dirs = [get_writable_dir(category)]
    project_dir = BASE_DATA_DIR / category
    if project_dir.exists() and project_dir not in dirs:
        dirs.append(project_dir)
    return dirs


def is_cloud_storage_enabled() -> bool:
    """Returns True if persistent cloud storage (BLOB_READ_WRITE_TOKEN) is configured."""
    return bool(VERCEL_BLOB_TOKEN)


# --- CLOUD OBJECT STORAGE HELPERS ---

def _vercel_blob_put(pathname: str, content: bytes, content_type: str = "text/plain") -> Optional[str]:
    """Uploads a file to Vercel Blob via HTTP PUT and returns the public URL."""
    if not VERCEL_BLOB_TOKEN:
        return None
    try:
        # Vercel Blob API PUT endpoint
        url = f"https://blob.vercel-storage.com/{pathname.lstrip('/')}?access=public"
        req = urllib.request.Request(
            url,
            data=content,
            headers={
                "Authorization": f"Bearer {VERCEL_BLOB_TOKEN}",
                "Content-Type": content_type,
                "x-api-version": "7",
                "x-add-random-suffix": "false",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("url")
    except Exception as e:
        logger.warning(f"Vercel Blob upload failed for {pathname}: {e}")
        return None


def _vercel_blob_get(url_or_pathname: str) -> Optional[bytes]:
    """Downloads a file from Vercel Blob by public URL or pathname."""
    if not url_or_pathname:
        return None
    try:
        if url_or_pathname.startswith("http://") or url_or_pathname.startswith("https://"):
            url = url_or_pathname
            req = urllib.request.Request(url)
        else:
            url = f"https://blob.vercel-storage.com/{url_or_pathname.lstrip('/')}"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {VERCEL_BLOB_TOKEN}"} if VERCEL_BLOB_TOKEN else {},
            )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read()
    except Exception as e:
        logger.warning(f"Vercel Blob download failed for {url_or_pathname}: {e}")
        return None


# --- DATASET PERSISTENCE ---

def save_dataset_files(dataset_id: str, csv_content: str, metadata: Dict[str, Any]) -> Tuple[Path, Path]:
    """
    Persists dataset CSV and inspection metadata across:
    1. Memory cache
    2. Writable filesystem (/tmp/qresq_data/uploads or data/uploads)
    3. Vercel Blob (if BLOB_READ_WRITE_TOKEN is configured)
    """
    # 1. Update in-memory cache
    _DATASET_CACHE[dataset_id] = (csv_content, metadata)

    # 2. Save to writable disk
    target_dir = get_writable_dir("uploads")
    csv_path = target_dir / f"{dataset_id}.csv"
    meta_path = target_dir / f"{dataset_id}.json"

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    # Embed cloud references if available
    cloud_csv_url = _vercel_blob_put(f"datasets/{dataset_id}.csv", csv_content.encode("utf-8"), "text/csv")
    if cloud_csv_url:
        metadata["cloud_csv_url"] = cloud_csv_url

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    if VERCEL_BLOB_TOKEN:
        _vercel_blob_put(f"datasets/{dataset_id}.json", json.dumps(metadata, indent=2).encode("utf-8"), "application/json")

    return csv_path, meta_path


def load_dataset_files(dataset_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    Loads dataset CSV and metadata by dataset_id.
    Tries:
    1. In-memory cache
    2. Writable and bundled local disk paths
    3. Vercel Blob storage (caching back to disk)
    """
    # 1. In-memory cache
    if dataset_id in _DATASET_CACHE:
        return _DATASET_CACHE[dataset_id]

    # 2. Local disk (writable or bundled)
    for search_dir in get_read_dirs("uploads"):
        csv_path = search_dir / f"{dataset_id}.csv"
        meta_path = search_dir / f"{dataset_id}.json"
        if csv_path.exists() and meta_path.exists():
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    csv_content = f.read()
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                _DATASET_CACHE[dataset_id] = (csv_content, metadata)
                return csv_content, metadata
            except Exception as e:
                logger.warning(f"Error reading local dataset files in {search_dir}: {e}")

    # 3. Cloud Object Storage (Vercel Blob)
    if VERCEL_BLOB_TOKEN:
        csv_bytes = _vercel_blob_get(f"datasets/{dataset_id}.csv")
        meta_bytes = _vercel_blob_get(f"datasets/{dataset_id}.json")
        if csv_bytes and meta_bytes:
            csv_content = csv_bytes.decode("utf-8")
            metadata = json.loads(meta_bytes.decode("utf-8"))
            # Cache locally to writable dir
            try:
                w_dir = get_writable_dir("uploads")
                with open(w_dir / f"{dataset_id}.csv", "w", encoding="utf-8") as f:
                    f.write(csv_content)
                with open(w_dir / f"{dataset_id}.json", "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
            except Exception:
                pass
            _DATASET_CACHE[dataset_id] = (csv_content, metadata)
            return csv_content, metadata

    raise FileNotFoundError(f"Dataset '{dataset_id}' not found in any storage tier.")


# --- EXPERIMENT PERSISTENCE ---

def save_experiment_run(run_data: Dict[str, Any]) -> str:
    """Saves an experiment run to memory, disk, and cloud object storage."""
    run_id = run_data.get("run_id")
    if not run_id:
        import uuid
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run_data["run_id"] = run_id

    if "timestamp" not in run_data:
        run_data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    _RUN_CACHE[run_id] = run_data

    # Save to writable disk
    try:
        w_dir = get_writable_dir("experiments")
        file_path = w_dir / f"{run_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write experiment run to disk: {e}")

    # Cloud upload if token present
    if VERCEL_BLOB_TOKEN:
        _vercel_blob_put(f"experiments/{run_id}.json", json.dumps(run_data, indent=2).encode("utf-8"), "application/json")

    return run_id


def load_experiment_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Loads an experiment run by run_id."""
    if run_id in _RUN_CACHE:
        return _RUN_CACHE[run_id]

    for search_dir in get_read_dirs("experiments"):
        file_path = search_dir / f"{run_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _RUN_CACHE[run_id] = data
                    return data
            except Exception:
                pass

    if VERCEL_BLOB_TOKEN:
        content = _vercel_blob_get(f"experiments/{run_id}.json")
        if content:
            try:
                data = json.loads(content.decode("utf-8"))
                _RUN_CACHE[run_id] = data
                return data
            except Exception:
                pass

    return None


def list_experiment_runs(limit: int = 15) -> List[Dict[str, Any]]:
    """Lists recent experiment runs merged from disk, memory, and bundled seeds."""
    found: Dict[str, Dict[str, Any]] = dict(_RUN_CACHE)

    for search_dir in get_read_dirs("experiments"):
        if search_dir.exists():
            for p in sorted(search_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                r_id = p.stem
                if r_id not in found:
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            found[r_id] = json.load(f)
                    except Exception:
                        pass

    # Sort newest first by timestamp
    runs = list(found.values())
    runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    summaries = []
    for d in runs[:limit]:
        summaries.append({
            "run_id": d.get("run_id"),
            "timestamp": d.get("timestamp"),
            "mode": d.get("mode", "single_sample"),
            "processor": d.get("processor_name", d.get("processor")),
            "mitigation_method": d.get("mitigation_method"),
            "dataset_source": d.get("dataset_source", "official_benchmark"),
            "accuracy": d.get("ml_metrics", {}).get("accuracy") if "ml_metrics" in d else None,
            "recall": d.get("ml_metrics", {}).get("recall") if "ml_metrics" in d else None,
        })
    return summaries


# --- MODEL PERSISTENCE ---

def save_trained_model(model_data: Dict[str, Any]) -> str:
    """Saves a trained model to memory and disk."""
    model_id = model_data.get("model_id")
    if not model_id:
        import uuid
        model_id = f"model_{uuid.uuid4().hex[:10]}"
        model_data["model_id"] = model_id

    if "created_at" not in model_data:
        model_data["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    _MODEL_CACHE[model_id] = model_data

    try:
        w_dir = get_writable_dir("models")
        file_path = w_dir / f"{model_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(model_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write model to disk: {e}")

    if VERCEL_BLOB_TOKEN:
        _vercel_blob_put(f"models/{model_id}.json", json.dumps(model_data, indent=2).encode("utf-8"), "application/json")

    return model_id


def load_trained_model(model_id: str) -> Optional[Dict[str, Any]]:
    """Loads a trained model by model_id."""
    if model_id in _MODEL_CACHE:
        return _MODEL_CACHE[model_id]

    for search_dir in get_read_dirs("models"):
        file_path = search_dir / f"{model_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _MODEL_CACHE[model_id] = data
                    return data
            except Exception:
                pass

    if VERCEL_BLOB_TOKEN:
        content = _vercel_blob_get(f"models/{model_id}.json")
        if content:
            try:
                data = json.loads(content.decode("utf-8"))
                _MODEL_CACHE[model_id] = data
                return data
            except Exception:
                pass

    return None


def list_trained_models() -> List[Dict[str, Any]]:
    """Lists saved models merged across memory and disk."""
    found: Dict[str, Dict[str, Any]] = dict(_MODEL_CACHE)

    for search_dir in get_read_dirs("models"):
        if search_dir.exists():
            for p in sorted(search_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                m_id = p.stem
                if m_id not in found:
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            found[m_id] = json.load(f)
                    except Exception:
                        pass

    models = list(found.values())
    models.sort(key=lambda m: m.get("created_at", ""), reverse=True)

    summaries = []
    for d in models:
        summaries.append({
            "model_id": d.get("model_id"),
            "name": d.get("name", d.get("model_id")),
            "created_at": d.get("created_at"),
            "epochs": d.get("epochs"),
            "final_loss": d.get("train_loss_history", [-1])[-1] if d.get("train_loss_history") else None,
            "dataset_fingerprint": d.get("dataset_fingerprint"),
            "num_qubits": d.get("num_qubits", 4),
            "layers": d.get("layers", 2),
        })
    return summaries
