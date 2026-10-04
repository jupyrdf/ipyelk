"""Fail on an ast-grep suppression comment that does not name a rule.

``ast-grep scan`` cannot flag a bare trailing suppression: it silences every
rule on its own line, including the one written to catch it.
"""

import re
import subprocess
import sys
from pathlib import Path

BARE = re.compile("ast-grep" + r"-ignore(?!:\s*[\w-])")


def main() -> int:
    files = subprocess.check_output(
        ["git", "ls-files", "*.py", "*.ts", "*.tsx"], text=True
    ).split()
    found = 0
    for path in files:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if BARE.search(line):
                print(f"{path}:{number}: name the rule in the ast-grep suppression")
                found += 1
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
