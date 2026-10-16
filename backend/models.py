from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from database import Base


class TrafficCycle(Base):
    __tablename__ = "traffic_cycles"

    cycle_id = Column(Integer, primary_key=True, index=True)

    cycle_number = Column(Integer, nullable=False)
    cycle_date = Column(Date, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    cycle_duration = Column(Integer, nullable=False)

    day_of_week = Column(String(10), nullable=False)
    part_of_day = Column(String(15), nullable=False)

    # Traffic counts
    l1_count = Column(Integer, default=0)
    l2_count = Column(Integer, default=0)
    l3_count = Column(Integer, default=0)
    l4_count = Column(Integer, default=0)

    total_count = Column(Integer, default=0)

    # Density
    l1_density = Column(String(10))
    l2_density = Column(String(10))
    l3_density = Column(String(10))
    l4_density = Column(String(10))

    # Green time
    l1_green = Column(Integer, default=30)
    l2_green = Column(Integer, default=30)
    l3_green = Column(Integer, default=30)
    l4_green = Column(Integer, default=30)

    # Extra green time
    l1_extra = Column(Integer, default=0)
    l2_extra = Column(Integer, default=0)
    l3_extra = Column(Integer, default=0)
    l4_extra = Column(Integer, default=0)

    # Cleared vehicles
    l1_cleared = Column(Integer, default=0)
    l2_cleared = Column(Integer, default=0)
    l3_cleared = Column(Integer, default=0)
    l4_cleared = Column(Integer, default=0)

    # Remaining vehicles
    l1_remaining = Column(Integer, default=0)
    l2_remaining = Column(Integer, default=0)
    l3_remaining = Column(Integer, default=0)
    l4_remaining = Column(Integer, default=0)

    # Emergency
    emergency_detected = Column(Boolean, default=False)
    emergency_lane = Column(Integer, nullable=True)
    emergency_time = Column(DateTime, nullable=True)

    # Cycle extension
    cycle_extended = Column(Boolean, default=False)
    extended_lanes = Column(String(20), nullable=True)
    extension_reason = Column(String(100), nullable=True)

    created_at = Column(
        DateTime,
        server_default="CURRENT_TIMESTAMP"
    )

    data_source = Column(String(20), default="REAL")