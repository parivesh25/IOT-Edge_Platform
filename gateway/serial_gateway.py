"""Keep the student command short when run from the Git root."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    script = Path(__file__).resolve().parents[1] / "edge-lab-platform-starter/edge-lab-platform/gateway/serial_gateway.py"
    runpy.run_path(str(script), run_name="__main__")
