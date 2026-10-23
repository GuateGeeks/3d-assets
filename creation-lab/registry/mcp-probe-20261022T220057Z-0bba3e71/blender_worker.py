import sys
sys.path.insert(0, '\\\\wsl.localhost\\Ubuntu\\home\\adawolfs\\projects\\makecode\\3d-assets\\creation-lab\\vendor\\blender-lab-mcp\\source\\addon')
from blender_mcp_addon.cli import cli_execute
raise SystemExit(cli_execute(["--host", "127.0.0.1", "--port", '52880']))
