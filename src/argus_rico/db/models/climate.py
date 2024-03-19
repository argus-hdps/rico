"""Model definitions for internal climate and weather."""

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from . import Base


class BoltwoodReport(Base):
    __tablename__ = "boltwood_report"

    id = Column(Integer, primary_key=True)
    epoch = Column(DateTime, nullable=False)

    wind_hotwire_tempC = Column(Numeric(5, 2))
    wind_coldwire_tempC = Column(Numeric(5, 2))

    wind_speed_kmh = Column(Numeric(5, 2))
    pressure_hpa = Column(Numeric(6, 2))
    pressure_tempC = Column(Numeric(4, 2))
    ambient_tempC = Column(Numeric(4, 2))
    station_voltage = Column(Numeric(4, 2))
    daylight = Column(Numeric(3, 0))
    sky_tempC = Column(Numeric(5, 2))
    case_tempC = Column(Numeric(5, 2))

    # probably over-sized
    rain_raw = Column(Numeric(8, 2))
    rain_dpm = Column(Numeric(8, 2))

    humidity = Column(Numeric(5, 2))
    humidity_tempC = Column(Numeric(5, 2))
    dewpointC = Column(Numeric(5, 2))

    firmware_version = Column(String(5), nullable=False)


class PathfinderHVAC(Base):
    __tablename__ = "pathfinder_hvac"

    id = Column(Integer, primary_key=True)
    epoch = Column(DateTime, nullable=False)

    south_low_tempC = Column(Numeric(4, 1))  # 'PF_S_low'
    south_west_tempC = Column(Numeric(4, 1))  # 'PF_SW'
    south_east_tempC = Column(Numeric(4, 1))  # 'PF_SE'
    north_low_tempC = Column(Numeric(4, 1))  # 'PF_N_low'
    north_west_tempC = Column(Numeric(4, 1))  # 'PF_NW'
    north_east_tempC = Column(Numeric(4, 1))  # 'PF_NE'

    cupola_tempC = Column(Numeric(4, 1))  # 'cupola'
    supply_tempC = Column(Numeric(4, 1))  # 'SM_supply_fan'
    exhaust_tempC = Column(Numeric(4, 1))  # 'SM_N_temp'

    cradle_sw_tempC = Column(Numeric(4, 1))  # 'cradle_SW'
    cradle_w_tempC = Column(Numeric(4, 1))  # 'cradle_W'
    cradle_nw_tempC = Column(Numeric(4, 1))  # 'cradle_NW'
    cradle_cs_tempC = Column(Numeric(4, 1))  # ' cradle_ctr_S'
    cradle_cn_tempC = Column(Numeric(4, 1))  # ' cradle_ctr_N'
    cradle_se_tempC = Column(Numeric(4, 1))  # 'cradle_SE'
    cradle_e_tempC = Column(Numeric(4, 1))  # 'cradle_E'
    cradle_ne_tempC = Column(Numeric(4, 1))  # 'cradle_NE'

    wall_se_tempC = Column(Numeric(4, 1))  # 'SE_wall_temp':
    wall_ne_tempC = Column(Numeric(4, 1))  # 'NE_wall_temp':

    humidity_se = Column(Numeric(4, 1))  # 'PF_SE_hum'
    humidity_ne = Column(Numeric(4, 1))  # 'PF_NE_hum'
    humidity_sm = Column(Numeric(4, 1))  # 'SM_hum'
