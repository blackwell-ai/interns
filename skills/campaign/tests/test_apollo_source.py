"""Unit tests for apollo_source pattern logic (pure functions, no network)."""

from skills.campaign.apollo_source import _obf_match, apply_pattern, infer_pattern


def test_infer_first_name():
    assert infer_pattern("Gabi", "Lewis", "gabi@magicspoon.com") == "{first}"


def test_infer_first_initial_last():
    assert infer_pattern("Jordan", "Nathan", "jnathan@carawayhome.com") == "{f}{last}"


def test_infer_first_plus_last_initial():
    # glossier-style emilyw@ — the pattern that broke the first send
    assert infer_pattern("Emily", "Weiss", "emilyw@glossier.com") == "{first}{l}"


def test_infer_first_dot_last():
    assert infer_pattern("Jane", "Doe", "jane.doe@acme.com") == "{first}.{last}"


def test_infer_unknown_returns_none():
    assert infer_pattern("Jane", "Doe", "xyz123@acme.com") is None


def test_apply_first_name_needs_no_last():
    assert apply_pattern("{first}", "Gabi", None, "", "magicspoon.com") == "gabi@magicspoon.com"


def test_apply_last_name_pattern_without_last_is_none():
    # {f}{last} needs the full last name; only the obfuscated initial is not enough
    assert apply_pattern("{f}{last}", "Jordan", None, "N", "carawayhome.com") is None


def test_apply_first_initial_last():
    assert apply_pattern("{f}{last}", "Jordan", "Nathan", "N", "carawayhome.com") == "jnathan@carawayhome.com"


def test_apply_first_plus_last_initial_from_obfuscation():
    # the fix: derive {first}{l} from first name + last initial alone (no full last name)
    assert apply_pattern("{first}{l}", "Emily", None, "W", "glossier.com") == "emilyw@glossier.com"


def test_obf_match_accepts_correct():
    assert _obf_match("Nathan", "Na***n") is True


def test_obf_match_rejects_wrong_length():
    assert _obf_match("Nat", "Na***n") is False


def test_obf_match_rejects_wrong_letters():
    assert _obf_match("Smith", "Na***n") is False


def test_obf_match_no_constraint_when_no_stars():
    assert _obf_match("Anything", "") is True
