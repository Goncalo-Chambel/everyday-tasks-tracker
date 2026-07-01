from datetime import date

from pydantic import BaseModel, Field


HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6c8cff", pattern=HEX_COLOR_PATTERN)


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str


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
    category_color: str
    start_date: date
    end_date: date | None
    done: bool
