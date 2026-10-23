"""Launch the pinned local official stdio server; does not start Blender or edit configuration."""
from pathlib import Path
import site
import sys

LAB = Path(__file__).resolve().parents[1]
site.addsitedir(str(LAB / 'vendor/.runtime'))
sys.path.insert(0, str(LAB / 'vendor/.runtime/official-blender-mcp'))
from blmcp import main

if __name__ == '__main__':
    raise SystemExit(main())
