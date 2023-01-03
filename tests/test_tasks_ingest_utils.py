import pytest

from fedimapper.tasks.ingesters import utils


def test_get_safe_fld():
    assert "google.co.uk" == utils.get_safe_fld("google.co.uk")
