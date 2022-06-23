# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

# from https://github.com/jupyrdf/ipyradiant/blob/master/_scripts/utils.py

# Copyright (c) 2020 ipyradiant contributors.
# Distributed under the terms of the Modified BSD License.
import re

RE_TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} -\d*"
RE_PYTEST_TIMESTAMP = r"on \d{2}-[^\-]+-\d{4} at \d{2}:\d{2}:\d{2}"

PATTERNS = [RE_TIMESTAMP, RE_PYTEST_TIMESTAMP]


def strip_timestamps(*paths, slug="TIMESTAMP"):
    """replace timestamps with a less churn-y value"""
    for path in paths:
        if not path.exists():
            continue

        text = original_text = path.read_text(encoding="utf-8")

        for pattern in PATTERNS:
            if not re.findall(pattern, text):
                continue
            text = re.sub(pattern, slug, text)

        if text != original_text:
            path.write_text(text)
