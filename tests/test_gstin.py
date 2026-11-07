from gstinvoice.gstin import compute_check_char, is_valid_gstin, state_of


def make(state="27", pan="AABCS1234K"):
    base = f"{state}{pan}1Z"
    return base + compute_check_char(base)


def test_valid_gstin():
    assert is_valid_gstin(make())


def test_bad_checksum_rejected():
    g = make()
    bad = g[:-1] + ("A" if g[-1] != "A" else "B")
    assert not is_valid_gstin(bad)


def test_bad_format_and_state():
    assert not is_valid_gstin("NOTAGSTIN")
    assert not is_valid_gstin(make(state="25"))  # 25 is not an assigned state code


def test_state_lookup():
    assert state_of(make("29")) == "Karnataka"
