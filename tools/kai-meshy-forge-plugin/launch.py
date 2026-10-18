"""Portable local entrypoint; never resolves or exports credentials."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kai_meshy.cli import main
if __name__ == '__main__':
    main()
