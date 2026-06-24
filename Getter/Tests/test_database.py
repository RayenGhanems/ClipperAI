from Data_Ingestion.models import Channel


def test_insert_channel(db):

    channel = Channel(
        channel_id="123",
        channel_name="MrBeast"
    )

    db.add(channel)
    db.commit()

    channels = db.query(Channel).all()

    assert len(channels) == 1
    assert channels[0].channel_name == "MrBeast"