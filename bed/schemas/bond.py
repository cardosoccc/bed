from pydantic import BaseModel, ConfigDict


class BondCreate(BaseModel):
    name: str
    price: float = 0


class BondRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    price: float
