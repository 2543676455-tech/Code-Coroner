from sample import authenticate


def test_authenticate() -> None:
    assert authenticate("token")
