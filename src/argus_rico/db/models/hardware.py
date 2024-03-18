"""Model definitions for hardware components."""

from typing import List

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class Throughput(Base):
    __tablename__ = "throughput"
    id = Column(Integer, primary_key=True)
    descriptor = Column(String(128))
    spectral_throughput: Mapped[List["SpectralThroughput"]] = relationship(
        back_populates="throughput"
    )


class SpectralThroughput(Base):
    """Actual throughput data  as a function of nanometers"""

    __tablename__ = "spectral_throughput"
    id = Column(Integer, primary_key=True)
    wavelength_nm = Column(Numeric(precision=8, scale=4))
    efficiency = Column(Numeric(precision=10, scale=7))

    throughput_id: Mapped[int] = mapped_column(ForeignKey("throughput.id"))
    throughput: Mapped["Throughput"] = relationship(
        back_populates="spectral_throughput"
    )


class Telescope(Base):
    __tablename__ = "telescope"

    id = Column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("telescope_model.id"))
    model: Mapped["TelescopeModel"] = relationship(back_populates="telescopes")
    serial: Mapped[str] = Column(String(12), nullable=False, unique=True)


class TelescopeModel(Base):
    __tablename__ = "telescope_model"
    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer = Column(String(30))
    model = Column(String(16), nullable=False, unique=True)
    revision = Column(String(5), nullable=False, unique=True)
    aperture_mm = Column(Numeric(precision=8, scale=4))
    focal_length_mm = Column(Numeric(precision=8, scale=4))

    throughput_id = Column(Integer, ForeignKey("throughput.id"))
    throughput: Mapped["Throughput"] = relationship()

    telescopes: Mapped[List["Telescope"]] = relationship(back_populates="model")


class CameraModel(Base):
    __tablename__ = "camera_model"
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(30))
    model = Column(String(16), nullable=False, unique=True)
    cameras: Mapped[List["Camera"]] = relationship(back_populates="model")


class Camera(Base):
    __tablename__ = "camera"
    id = Column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("camera_model.id"))
    model: Mapped["CameraModel"] = relationship(back_populates="cameras")
    serial: Mapped[str] = Column(String(12), nullable=False, unique=True)


class Focuser(Base):
    __tablename__ = "focuser"
    id = Column(Integer, primary_key=True)
    dynamixel_addr: Mapped[int] = Column(Integer, nullable=False, unique=True)


class FilterModel(Base):
    __tablename__ = "filter_model"

    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(30))
    name = Column(String(5), nullable=False, unique=True)

    throughput_id = Column(Integer, ForeignKey("throughput.id"))
    throughput: Mapped["Throughput"] = relationship()


class Instrument(Base):
    __tablename__ = "instrument"
    id = Column(Integer, primary_key=True)
    name = Column(String(16), nullable=False, unique=True)


class OcularUnit(Base):
    __tablename__ = "ocular_unit"
    id = Column(Integer, primary_key=True)
    telescope_id = Column(Integer, ForeignKey("telescope.id"))
    focuser_id = Column(Integer, ForeignKey("focuser.id"))
    camera_id = Column(Integer, ForeignKey("camera.id"))
    filter_id = Column(Integer, ForeignKey("filter_model.id"))
