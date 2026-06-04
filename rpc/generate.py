"""Regenerate gRPC stubs from rpc/protos into echoscope_rpc/.

  cd rpc && ../.venv/Scripts/python generate.py

Generated *_pb2_grpc.py imports are rewritten to package-relative (`from . import`)
so the stubs work as part of the echoscope_rpc package.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "echoscope_rpc"
PROTOS = ["analytics.proto", "nlp.proto"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{HERE / 'protos'}",
        f"--python_out={OUT}",
        f"--grpc_python_out={OUT}",
        *[str(HERE / "protos" / p) for p in PROTOS],
    ]
    subprocess.run(cmd, check=True)

    # rewrite `import X_pb2` -> `from . import X_pb2` in the *_pb2_grpc.py files
    for grpc_file in OUT.glob("*_pb2_grpc.py"):
        text = grpc_file.read_text()
        text = re.sub(r"^import (\w+_pb2) as", r"from . import \1 as", text, flags=re.MULTILINE)
        grpc_file.write_text(text)
    print(f"generated stubs in {OUT}")


if __name__ == "__main__":
    main()
