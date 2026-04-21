# TODO for vehicle-model: expand the schema for registration metadata, audit fields, and document storage.
from sqlalchemy import Column, Integer, String

from database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(32), unique=True, index=True, nullable=False)
    owner_name = Column(String(128), nullable=False)
    owner_contact = Column(String(64), nullable=True)
    vehicle_type = Column(String(64), nullable=False)
    registration_state = Column(String(16), nullable=True)
