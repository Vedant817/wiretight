"""Archive import isolation is an enforced runtime property."""

import pytest

from tests.support.audit_runtime_imports import main


@pytest.mark.compliance("T-R4a")
def test_product_entrypoints_cannot_import_test_or_historical_authority():
    main()
