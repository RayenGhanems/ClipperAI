
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")
DATABASE_URL=os.getenv("DATABASE_URL")

engine=create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


Base=declarative_base()




