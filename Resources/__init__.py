"""Module of static resources."""

import os

_resource_directory = os.path.dirname(__file__)


def get_path_to_resource(name: str) -> str:
    """Resolves the absolute path to the given resource in this module named `name`."""
    return os.path.join(_resource_directory, name)
