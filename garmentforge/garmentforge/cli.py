from __future__ import annotations
import argparse,json
from pathlib import Path
from .construction import build_package
from .validate import validate_package

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    manifest=build_package(a.output);receipt=validate_package(a.output)
    print(json.dumps({"manifest":manifest,"validation":receipt},indent=2));return 0 if receipt["passed"] else 1
if __name__=="__main__":raise SystemExit(main())
