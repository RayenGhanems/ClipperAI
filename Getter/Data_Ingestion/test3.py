from Data_Ingestion.database import SessionLocal
from Data_Ingestion.download import DownloadService

db = SessionLocal()

try:
    service = DownloadService()

    result = service.download_pending_videos(db)

    print(result)

finally:
    db.close()