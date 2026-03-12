from pydantic import BaseModel, ConfigDict


class StockCreate(BaseModel):
    ticker: str
    price: float = 0


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: float
