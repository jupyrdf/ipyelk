# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
class ElkDuplicateIDError(Exception):
    """Elk Ids must be unique"""


class ElkRegistryError(Exception):
    """Transformer mark registry missing key"""
