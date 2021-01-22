# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ipyelk.schema.validator import ElkSchemaValidator


def test_label_label_schema():
    nested_label = {
        "id": "root",
        "labels": [
            {
                "id": "top_label",
                "text": "",
                "labels": [{"id": "nested_label", "text": "", "properties": {}}],
            }
        ],
    }

    ElkSchemaValidator.validate(nested_label)
