import os

PORT = int(os.getenv("MFLUX_PORT", "8100"))
DEFAULT_MODEL = os.getenv("MFLUX_MODEL", "mlx-community/FLUX.1-dev-4bit")
DEFAULT_WIDTH = int(os.getenv("MFLUX_WIDTH", "1024"))
DEFAULT_HEIGHT = int(os.getenv("MFLUX_HEIGHT", "1024"))
DEFAULT_STEPS = int(os.getenv("MFLUX_STEPS", "20"))
OUTPUT_DIR = os.getenv("MFLUX_OUTPUT_DIR", "./outputs")
