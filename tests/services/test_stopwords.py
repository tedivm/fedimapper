import pytest

from fedimapper.services import stopwords


def test_stopwords():
    assert "anti-trans" in stopwords.get_key_words("english", "Instance has anti-trans content.")
    assert "ignore-punctuation" in stopwords.get_key_words("english", "!@#$%^&*(ignore-punctuation)")
    assert len(stopwords.get_key_words("english", "the in a as")) == 0
