from pydantic import BaseModel, ConfigDict


class TickerCreate(BaseModel):
    ticker: str
    price: float = 0


class TickerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: float
