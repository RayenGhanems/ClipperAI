from Data_Ingestion.database import Base, engine
from Data_Ingestion.models import Channel, Video
import psycopg2
import os
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL =", repr(DATABASE_URL))
Base.metadata.create_all(bind=engine)

print("Connexion OK + tables créées")