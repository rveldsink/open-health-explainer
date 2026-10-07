from ohe.explainer import explain


def test_indexed_path_is_preserved():
    result = explain("Bundle.entry[2].resource.identifier[0]: minimum required = 1, but only found 0")
    assert result["path"] == "Bundle.entry[2].resource.identifier[0]"


def test_message_without_path_has_no_invented_location():
    assert explain("An unclassified message without location")["path"] is None

def test_cardinality_classification():
    result = explain("Patient.identifier: minimum required = 1, but only found 0")
    assert result["matched"] is True
    assert result["errorId"] == "OHE-CARD-001"
    assert result["path"] == "Patient.identifier"

def test_unknown_message():
    result = explain("A completely unknown validator message")
    assert result["matched"] is False
    assert result["errorId"] == "OHE-UNKNOWN-001"
