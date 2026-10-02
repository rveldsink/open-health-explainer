from ohe.explainer import explain

def test_cardinality_classification():
    result = explain("Patient.identifier: minimum required = 1, but only found 0")
    assert result["matched"] is True
    assert result["errorId"] == "OHE-CARD-001"
    assert result["path"] == "Patient.identifier"

def test_unknown_message():
    result = explain("A completely unknown validator message")
    assert result["matched"] is False
    assert result["errorId"] == "OHE-UNKNOWN-001"
