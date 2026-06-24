from Data_Ingestion.database import Base, engine
from Data_Ingestion.models import Channel, Video

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
