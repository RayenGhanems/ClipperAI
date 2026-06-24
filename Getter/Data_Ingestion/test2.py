from Data_Ingestion.database import Base, engine, SessionLocal
from Data_Ingestion.Synchronisation import SyncService

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    service = SyncService()

    result = service.sync_channel(
        db,
        "https://www.youtube.com/@MrBeast"
    )

    print(result)

finally:
    db.close()