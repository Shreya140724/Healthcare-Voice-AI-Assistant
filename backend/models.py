from sqlalchemy import *

from database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Appointment(Base):

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    phone = Column(String)

    date = Column(String)

    time = Column(String)

Base.metadata.create_all(bind=engine)