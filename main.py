from fastapi import FastAPI
from inspect import _descriptor_get
from pydantic import BaseModel, Field
from pydantic.functional_validators import model_validator
from pydantic_core.core_schema import decimal_schema
from typing import Optional
import time
from random import Random

from datetime import datetime

import logging
from uvicorn.logging import DefaultFormatter  # ← импортируем класс

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False                     # не отдаём root-логгеру

handler = logging.StreamHandler()
handler.setFormatter(DefaultFormatter())     # создаём экземпляр класса
logger.addHandler(handler)


MASK_64 = (1 << 64) - 1           # 0xFFFF_FFFF_FFFF_FFFF


def make_task_id(s:str) -> int:
    """
    Генерирует 64-битный ID, детерминированно зависящий от
    времени создания и title, распределённый «случайно».
    """
    ts = time.time_ns()           # текущие наносекунды от эпохи (int)
    title_hash  =hash(s) & MASK_64  # 64-битный хэш от title
    rng = Random(ts)              # локальный PRNG, посеянный этим временем
    rand_bits = rng.getrandbits(64) & MASK_64
    return rand_bits ^ title_hash # XOR для уникальности по title

class User(BaseModel):
    id:str


class Task(BaseModel):
    title:str
    description:str=""
    belongsTo:User
    id:int = None
    createdAt:datetime =Field(default_factory=datetime.now)
    updatedAt:datetime =Field(default_factory=datetime.now)
    completed:bool =Field(default=False)

    @model_validator(mode="after")
    @classmethod
    def __generate_id(cls,data):
        data.id=make_task_id(data.title+data.description)
        return data


app=FastAPI()


@app.get("/")
async def root():
    return {"message" :f"{time.time()}"}

@app.post("/tasks")
async def createTask(task: Task):
    return {"201":task}
