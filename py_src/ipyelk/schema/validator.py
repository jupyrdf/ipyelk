# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.


import json
from pathlib import Path
from typing import List

import jsonschema

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / "elkschema.json").read_text(encoding="utf-8"))
SCHEMA["$ref"] = "#/definitions/AnyElkNode"

ElkSchemaValidator = jsonschema.Draft7Validator(SCHEMA)


def validate_elk_json(value) -> bool:
    errors: List[jsonschema.ValidationError] = list(
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
