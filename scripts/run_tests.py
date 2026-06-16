import subprocess
import sys


def main() -> int:
    return subprocess.call([sys.executable, "-m", "pytest"])


if __name__ == "__main__":
    raise SystemExit(main())
