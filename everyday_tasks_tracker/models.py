from datetime import date

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class CategoryOut(BaseModel):
    id: int
    name: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: int
    end_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    end_date: date | None = None
    done: bool | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    category_id: int
    category_name: str
    start_date: date
    end_date: date | None
    done: bool
