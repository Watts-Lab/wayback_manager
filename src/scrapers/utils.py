from collections.abc import Iterable
import numpy as np


def has_substr(substr):
    if isinstance(substr, str):
        return lambda x: substr in x if x else False
    elif isinstance(substr, Iterable):
        return lambda x: np.any([sub in x] for sub in substr) if x else False
    else:
        raise NotImplementedError


def not_has_substr(substr):
    if isinstance(substr, str):
        return lambda x: substr not in x if x else False
    elif isinstance(substr, Iterable):
        return lambda x: not np.any([sub in x] for sub in substr) if x else False
    else:
        raise NotImplementedError
