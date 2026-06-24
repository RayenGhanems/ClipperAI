from Data_Ingestion.Youtube_service import YoutubeService


def test_extract_handle():
    service = YoutubeService()

    result = service.extract_handle(
        "https://www.youtube.com/@MrBeast"
    )

    assert result == "@MrBeast"


def test_extract_handle_with_trailing_slash():
    service = YoutubeService()

    result = service.extract_handle(
        "https://www.youtube.com/@MrBeast/"
    )

    assert result == "@MrBeast"