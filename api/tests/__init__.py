"""
Tests for geo-base API.

Test modules:
- test_validators.py: Geometry and data validation tests
- test_tileset_models.py: Pydantic model validation tests
- test_fix_bounds.py: Bounds fix script tests

Running tests:
    # Run all tests
    cd api
    uv run pytest tests/ -v

    # Run specific test file
    uv run pytest tests/test_validators.py -v

    # Run with coverage
    uv run pytest tests/ --cov=lib --cov-report=term-missing
"""
