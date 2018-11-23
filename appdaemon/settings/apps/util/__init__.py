"""Define generic utils."""
import datetime
from typing import Any, Tuple, Union

import Levenshtein


def grammatical_list_join(the_list: list) -> str:
    """Return a grammatically correct list join."""
    return ', '.join(the_list[:-2] + [' and '.join(the_list[-2:])])


def most_common(the_list: list) -> Any:
    """Return the most common element in a list."""
    return max(set(the_list), key=the_list.count)


def relative_search_dict(
        candidates: dict, target: str,
        threshold: float = 0.3) -> Tuple[Union[None, str], Union[None, str]]:
    """Return a key/value pair (or its closest neighbor) from a dict."""
    if target.lower() in [k.lower() for k in candidates.keys()]:
        return (target, candidates[target])

    try:
        matches = sorted([
            k for k in candidates.keys()
            if Levenshtein.ratio(target, k) > threshold
        ], reverse=True)
        winner = matches[0]
        return (winner, candidates[winner])
    except IndexError:
        pass

    return (None, None)


def relative_search_list(
        candidates: list, target: str,
        threshold: float = 0.3) -> Union[None, str]:
    """Return an item (or its closest neighbor) from a list."""
    if target.lower() in [c.lower() for c in candidates]:
        return target

    try:
        matches = sorted([
            c for c in candidates if Levenshtein.ratio(target, c) > threshold
        ], reverse=True)
        return matches[0]
    except IndexError:
        pass

    return None


def suffix_strftime(frmt: str, input_dt: datetime.datetime) -> str:
    """Define a version of strftime() that puts a suffix on dates."""
    day_endings = {
        1: 'st',
        2: 'nd',
        3: 'rd',
        21: 'st',
        22: 'nd',
        23: 'rd',
        31: 'st'
    }
    return input_dt.strftime(frmt).replace(
        '{TH}',
        str(input_dt.day) + day_endings.get(input_dt.day, 'th'))
