"""Archive import isolation is an enforced runtime property."""
from tests.support.audit_runtime_imports import main


def test_product_entrypoints_cannot_import_test_or_historical_authority():
    main()
