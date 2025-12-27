from sqlalchemy.orm import declarative_base

# Single declarative base for all models (no engine here; async engine lives in database_connection)
Base = declarative_base()
