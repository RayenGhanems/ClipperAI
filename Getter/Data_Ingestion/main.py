from Data_Ingestion.database import SessionLocal
from Data_Ingestion.pipeline import PipelineService


def parse_max_new_videos(raw_value: str) -> int | None:
    # Une entrée vide veut dire "pas de limite", donc on prend toutes les vidéos valides.
    value = raw_value.strip()

    if value == "":
        return None

    return int(value)


db = SessionLocal()

try:
    # Mode manuel: lancer une synchronisation ponctuelle sur une seule chaîne.
    channel_url = input("Entrez l'URL de la chaîne YouTube : ").strip()
    raw_limit = input(
        "Entrez max_new_videos (vide = tout, 0 = rien, entier = limite) : "
    )

    pipeline = PipelineService()

    result = pipeline.ingest_channel(
        db,
        channel_url,
        max_new_videos=parse_max_new_videos(raw_limit),
    )

    print(result)

finally:
    db.close()
