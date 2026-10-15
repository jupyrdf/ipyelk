# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Validate ELK JSON against ``elkschema.json``, the schema of the frontend.

The pipeline does not validate: on 1000 nodes, validation takes about 7 times as
long as the serialization it checks, on every refresh. The unit tests check that
the models agree with the schema. To check a payload while you debug, call
``validate_elk_json(to_json(node, None))``.
"""

import json
from pathlib import Path

import jsonschema

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / "elkschema.json").read_text(encoding="utf-8"))
SCHEMA["$ref"] = "#/definitions/AnyElkNode"


ElkSchemaValidator = jsonschema.Draft7Validator(SCHEMA)


def validate_elk_json(value) -> bool:
    """Return ``True`` if ``value`` is a valid ELK JSON root node.

    :raises jsonschema.ValidationError: with every error and its JSON path
    """
    errors: list[jsonschema.ValidationError] = list(
        ElkSchemaValidator.iter_errors(value)
    )

    if errors:
        msg = ""
        for error in errors:
            path = "/".join(map(str, error.path))
            msg += f"\n#/{path}\n\t{error.message}"
            msg += f"\n\t\t{json.dumps(error.instance)[:70]}"
        raise jsonschema.ValidationError(msg)
    return True
