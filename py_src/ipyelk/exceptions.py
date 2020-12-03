class ElkDuplicateIDError(Exception):
    """Elk Ids must be unique"""


class ElkRegistryError(Exception):
    """Transformer mark registry missing key"""
