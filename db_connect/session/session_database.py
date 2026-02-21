import logging

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.config import Config

config = Config(".env")

user = config("DB_USER")
password = quote_plus(config("DB_PASSWORD")) # 특수문자 인코딩
host = config("DB_HOST")
db_name = config("DB_DATABASE")

DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    logging.info("[session] get_db_connection")
    db = SessionLocal()
    try:
        yield db
    finally:
        logging.info("[session] db_connection_close")
        db.close()