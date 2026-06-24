from Data_Ingestion.database import SessionLocal
from Data_Ingestion.pipeline import PipelineService

db = SessionLocal()

try:
    url = input("Entrez l'URL de la chaîne YouTube : ")

    pipeline = PipelineService()

    result = pipeline.sync_and_download_channel(
        db,
        url
    )

    print(result)

finally:
    db.close()