"""
Unit tests for feature property filter parsing (parse_feature_property_filter).

Pure unit tests with no database dependency.
"""

import pytest

from lib.tiles import parse_feature_property_filter


class TestParseFeaturePropertyFilterAccepted:
    """Test accepted grammar for parse_feature_property_filter."""

    def test_simple_equality(self):
        """Test simple key=value format."""
        assert parse_feature_property_filter("type=station") == (
            "f.properties->>%s = %s",
            ["type", "station"],
        )

    def test_unicode_key_and_value(self):
        """Test Unicode characters in both key and value."""
        assert parse_feature_property_filter("properties.地震=◎") == (
            "f.properties->>%s = %s",
            ["地震", "◎"],
        )

    def test_value_contains_equals(self):
        """Test value with multiple equals signs (e.g., URL)."""
        assert parse_feature_property_filter("name=https://example.test/a=b") == (
            "f.properties->>%s = %s",
            ["name", "https://example.test/a=b"],
        )

    def test_key_with_hyphen(self):
        """Test key containing hyphen."""
        assert parse_feature_property_filter("key-with-hyphen=value") == (
            "f.properties->>%s = %s",
            ["key-with-hyphen", "value"],
        )

    def test_key_whitespace_is_stripped(self):
        """Whitespace around the key must be stripped, so a filter like
        " type =station" doesn't silently match nothing. Whitespace in the
        value is preserved, since it could be a legitimate property value.
        A whitespace-only key like "   =value" must still be rejected as
        empty, rather than silently becoming a real filter."""
        assert parse_feature_property_filter(" type =station") == (
            "f.properties->>%s = %s",
            ["type", "station"],
        )
        assert parse_feature_property_filter("type= station ") == (
            "f.properties->>%s = %s",
            ["type", " station "],
        )
        with pytest.raises(ValueError):
            parse_feature_property_filter("   =value")


class TestParseFeaturePropertyFilterRejected:
    """Test rejected grammar for parse_feature_property_filter."""

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "=value",
            "key=",
            "key!=value",
            "key>value",
            "key<value",
            "key>=value",
            "key<=value",
            "key~value",
            "key=value;other=x",
            "key=value,other=x",
            "bad!key=value",
            "bad>key=value",
        ],
    )
    def test_invalid_formats(self, invalid_input):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError):
            parse_feature_property_filter(invalid_input)
