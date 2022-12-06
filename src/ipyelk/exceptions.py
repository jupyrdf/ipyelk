# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
class ElkDuplicateIDError(Exception):
    """Elk Ids must be unique"""


class ElkRegistryError(Exception):
    """Transformer mark registry missing key"""


class NotFoundError(Exception):
    pass


class NotUniqueError(Exception):
    pass


class BrokenPipe(Exception):
    pass
