from contextlib import asynccontextmanager
from bson import int64
from fastapi import FastAPI
from inspect import _descriptor_get
from pydantic import BaseModel, Field
from pydantic.functional_validators import model_validator
from pydantic_core.core_schema import decimal_schema
from typing import Optional ,List , Literal
import time
from random import Random

from datetime import datetime

import logging
from uvicorn.logging import DefaultFormatter  

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, Indexed, init_beanie

from bson import Int64 # перевод для mongod



logging.basicConfig(
    level=logging.INFO,            # корневой уровень
    format="[%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("app")  # свой логгер



MASK_64 = (1 << 63) - 1           # 0xFFFF_FFFF_FFFF_FFFF


def make_id(s:str="") -> int:
    """
    Генерирует 64-битный ID, детерминированно зависящий от
    времени создания и s, распределённый «случайно».
    """
    ts = time.time_ns()           # текущие наносекунды от эпохи (int)
    title_hash  =hash(s) & MASK_64  # 64-битный хэш от title
    rng = Random(ts)              # локальный PRNG, посеянный этим временем
    rand_bits = rng.getrandbits(64) & MASK_64
    return rand_bits ^ title_hash # XOR для уникальности по title

class User(Document):
    id:int
    tasks:List[int]=[] #ссылка на task


class Task(Document):
    title:str
    description:str=""
    belongsTo:User
    id:int = None
    createdAt:datetime =Field(default_factory=datetime.now)
    updatedAt:datetime =Field(default_factory=datetime.now)
    completed:bool =Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def __generate_id(cls,data): ## Мы всегда создаем свой id за это отвечает только сервер , клиент не может создать id 
        data["id"]=make_id(data["title"]+data["description"])
        return data

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    updatedAt:datetime =Field(default_factory=datetime.now)



@asynccontextmanager
async def lifespan(app:FastAPI):
    client=client = AsyncIOMotorClient("127.0.0.1:27017")
    await init_beanie(database=client.db_name,document_models=[User,Task])
    yield

app=FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message" :f"{time.time()}"}

@app.post("/tasks")
async def createTask(task: Task):
    """
    Создает задачу. 
    """
    user=await User.find_one(User.id==task.belongsTo.id)
    logger.info(f"user {user}")
    if not user:
        return {"404":"User not found"}
    else:
        
        await task.insert()
        logger.info(f"user {user}")
        user.tasks.append(task.id)
        await user.save()


    return {"201":task}

@app.get("/tasks")
async def getAllTasks(limit:int=20,offset:int=0,filter:Literal["all","completed","incompleted"]="all"):
    """
    Возвращает все таски

    offset - id последней показанной таски а не просто порядковый номер на странице
    """
    if filter!="all":
        tasks=await Task.find(Task.id>offset &Task.completed==filter).sort().limit(limit).to_list()
    else:
        tasks=await Task.find(Task.id>offset).sort().limit(limit).to_list()
    
    return {"200":tasks}



@app.patch("/tasks/{taskId}")
async def patchTaskById(taskId:int,taskUpd:TaskUpdate):
    
    task=await Task.find_one(Task.id==taskId)
    if not task:
        return {"404":"Not Found"}

    title=taskUpd.title
    description=taskUpd.description
    completed=taskUpd.completed


    if title is not None:
        task.title=title
    if description is not None:
        task.description=description
    if completed is not None:
        task.completed=completed
    
    task.updatedAt=taskUpd.updatedAt
    
    await task.save()
    return {"201":task}


@app.get("/tasks/{taskId}")
async def getTaskById(taskId:int):
    """
    Возвращает таску по id 
    """
    task=await Task.find_one(Task.id==taskId)

    if task:
        return {"200":task}
    else:
        return {"404":"Not Found"}






@app.post("/user")
async def createUser(user:User):
    """
    Создает пользователя. Если id не передан, то генерируется случайный id.
    """
    id=user.id
    logger.info(f"user id= {id}")
    if id:
        if await User.find_one(User.id==id):
            return {"409":"User already exists"}
        user=User(id=id)
    else:
        user=User(id=make_id())
    
    await user.insert()
    return {"201":user}