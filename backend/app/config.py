import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# nemotron-3-super-120b-a12b rather than the 550b ultra: measured on this endpoint, ultra
# times out on essentially every request right now while super answers in 2-5s and still
# does tool calling correctly. Override with NVIDIA_MODEL if ultra becomes responsive again.
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

# An operator waiting on an in-cab assistant will give up long before 45s. Cap the wait and
# fall back to the deterministic router instead — a fast useful answer beats a slow perfect one.
NVIDIA_TIMEOUT_S = float(os.getenv("NVIDIA_TIMEOUT_S", "15"))
