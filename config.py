import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "aluno05")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "C@nes2026")
    DB_NAME = os.getenv("DB_NAME", "aluno05")

    JWT_SECRET = os.getenv("JWT_SECRET", "chave-de-desenvolvimento-troque-no-env")
    JWT_EXPIRA_MINUTOS = int(os.getenv("JWT_EXPIRA_MINUTOS", "60"))

    CORS_ORIGENS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGENS", "http://localhost:5500,http://127.0.0.1:5500"
        ).split(",")
        if o.strip()
    ]
