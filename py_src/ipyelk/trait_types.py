# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import dataclasses
import json
from typing import List

import jsonschema
import traitlets


class Schema(traitlets.Any):
    """any... but validated by a jsonschema.Validator"""

    _validator: jsonschema.Draft7Validator = None

    def __init__(self, validator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validator = validator

    def validate(self, obj, value):
        errors: List[jsonschema.ValidationError] = list(
            self._validator.iter_errors(value)
        )
        if errors:
            msg = ""
            for error in errors:
                path = "/".join(map(str, error.path))
                msg += f"\n#/{path}\n\t{error.message}"
                msg += f"\n\t\t{json.dumps(error.instance)[:70]}"
            raise traitlets.TraitError(msg)
        return value


class Dataclass(traitlets.Instance):
    def __init__(self, klass, *args, **kwargs):
        assert dataclasses.is_dataclass(klass), "Klass must be a dataclass"
        super().__init__(klass, *args, **kwargs)

    def to_json(self, value):
        return dataclasses.asdict(value)
