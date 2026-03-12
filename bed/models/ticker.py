from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from bed.database import Base


class Ticker(Base):
    __tablename__ = "tickers"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    price: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)
