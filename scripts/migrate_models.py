""" Convert [Elk Model Repository](https://github.com/eclipse/elk-models) into ElkJSON
"""

# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import json
import requests

from itertools import chain
from pathlib import Path
from typing import Dict
from uuid import uuid4

from .project import ELKMODELS, ELKFIXTURES


ELKMODEL_ELKT = [f for f in ELKMODELS.rglob("*.elkt")]
ELKMODEL_JSON = [f for f in ELKMODELS.rglob("*.json")]


def fixture(model:Path)->Path:
    """Get mapped fixture target

    :param model: model path
    :return: Elk fixture that should exist after migrating models
    """
    return ELKFIXTURES / model.relative_to(ELKMODELS).with_suffix(".json")

ELKMODEL_FIXTURES = [fixture(f) for f in chain(ELKMODEL_ELKT, ELKMODEL_JSON)]


def migrate_layout_options(data:Dict)->Dict:
    """The older klayjs json uses the `properties` key which needs to be
    remapped to `layoutOptions`

    :param data: klayjs JSON
    :return: Updated ElkJSON
    """
    data = {**data}
    layout_options = data.pop("properties", None)
    if layout_options:
        data["layoutOptions"] = layout_options

    for prop in ["ports", "children", "labels"]:
        value = [migrate_layout_options(d) for d in data.get(prop, [])]
        if value:
            data[prop] = value
    return data

def backfill_ids(data:Dict)->Dict:
    """Seems like some `id`s are missing. This will backfill as needed

    :param data: JSON
    :return: Updated ElkJSON
    """
    data = {**data}
    data["id"] = data.get("id", str(uuid4()))

    for prop in ["ports", "children", "labels"]:
        value = [backfill_ids(d) for d in data.get(prop, [])]
        if value:
            data[prop] = value

    edges = []
    for edge in data.get("edges", []):
        edges.append(backfill_ids(edge))
    if edges:
        data["edges"] = edges
    return data


def elkt_to_elkjson(data:str)->Dict:
    """Uses public server to convert elkt to elk json

    :param data: elkt text
    :return: ElkJSON
    """
    #TODO maybe this url can be configured elsewhere but it isn't immediately discoverable
    url = "https://rtsys.informatik.uni-kiel.de/elklive/conversion?inFormat=elkt&outFormat=json"
    headers = {
        'Content-Type': 'text/plain',
    }
    resp = requests.post(url, data=data.encode("utf-8"), headers=headers)
    if resp.status_code == 200:
        return json.loads(resp.content.decode("utf-8"))


def migrate(force=False):
    """Migrate elk-models' elkt and older json formats to fixtures"""
    ELKFIXTURES.mkdir(parents=True, exist_ok=True)

    def save(model, elkjson):
        elkjson = backfill_ids(elkjson)
        path = fixture(model)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(elkjson))

    for model in ELKMODEL_JSON:
        elkjson = migrate_layout_options(json.loads(model.read_text()))
        save(model, elkjson)

    for model in ELKMODEL_ELKT:
        path = fixture(model)
        if force or not path.exists():
            elkjson = elkt_to_elkjson(model.read_text())

            save(model, elkjson)

