from cold_clock.reader import PackageReader, ReplayPackageClient


def test_reader_drops_unquoted_and_out_of_range_fields():
    client = ReplayPackageClient(
        {
            "transcription": "NAME OK\nLot DEMO",
            "fields": [
                {"key": "name", "value": "Name", "quote": "NAME OK", "confidence": 0.9},
                {"key": "lot", "value": "Invented", "quote": "Lot WRONG", "confidence": 0.8},
                {"key": "form", "value": "Vial", "quote": "", "confidence": 0.8},
                {"key": "strength", "value": "Bad", "quote": "NAME OK", "confidence": 1.2},
            ],
        }
    )
    result = PackageReader(client).read(b"synthetic", "image/svg+xml")
    assert len(result.fields) == 1
    assert len(result.dropped) == 3


def test_reader_requires_image_and_transcription():
    reader = PackageReader(ReplayPackageClient({"transcription": "", "fields": []}))
    try:
        reader.read(b"")
    except ValueError as exc:
        assert "image" in str(exc)
    else:
        raise AssertionError("empty image should fail")
    try:
        reader.read(b"image")
    except ValueError as exc:
        assert "transcription" in str(exc)
    else:
        raise AssertionError("empty transcription should fail")

