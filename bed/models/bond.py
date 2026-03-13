from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from bed.database import Base


class Bond(Base):
    __tablename__ = "bonds"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    price: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)
