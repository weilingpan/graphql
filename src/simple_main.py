import os
import uuid
import time
import asyncio
import strawberry
import pandas as pd
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import RedirectResponse
from strawberry.asgi import GraphQL
from sqlalchemy import ForeignKey, create_engine, Column, Integer, String, DateTime, event
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager
from strawberry.types import Info
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from rq import Queue
from redis import Redis
from pymongo import MongoClient
from pydantic import BaseModel
from tabulate import tabulate

# 建立 Redis 連線
redis_conn = Redis(host="redis", port=6379, decode_responses=True)
queue = Queue("uploads", connection=redis_conn)  # 建立 Redis 任務佇列 rq worker uploads

# MongoDB 連線
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mymongo:27017/mydatabase")
client = MongoClient(MONGO_URI)

# def create_access_token(user_info: dict, expires_delta: Optional[timedelta] = timedelta(days=1)):
#     print(user_info)
#     expire = datetime.utcnow() + expires_delta


DATABASE_URL = "sqlite:///./simple.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base =  declarative_base()

# Define SQLAlchemy models
class PostModel(Base):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    author_id = Column(Integer, ForeignKey("user.id"))

    # Relationships
    author = relationship("UserModel", back_populates="posts")


# Define SQLAlchemy models
class UserModel(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String)
    signup_time = Column(DateTime, default=datetime.utcnow())
    expired_time = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=1))

    # Relationships
    posts = relationship("PostModel", back_populates="author")

# # 使用 SQLAlchemy 事件監聽
# @event.listens_for(UserModel, "before_insert")
# def set_expired_time(mapper, connection, target):
#     if target.expired_time is None:
#         target.expired_time = datetime.utcnow() + timedelta(days=1)

# DB init
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    with SessionLocal() as db:
        return db

# Define GraphQL schema
# 使用 Strawberry 定義的 GraphQL object type
@strawberry.type
class PostType:
    id: strawberry.ID
    title: str
    content: str
    author_id: strawberry.ID
    author_name: str

# 使用 Strawberry 定義的 GraphQL object type
@strawberry.type
class UserType:
    id: strawberry.ID
    username: str
    email: str
    signup_time: datetime
    expired_time: datetime
    posts: List[PostType]
    cursor: Optional[str] = None  # 添加游標字段

@strawberry.type
class HelloResponse:
    message: str
    user_agent: str
    custom_header: str

# 定義Union型別
SearchResult = strawberry.union("SearchResult", (UserType, PostType))


# Define GraphQL Query and Mutation
@strawberry.type
class Query:
    @strawberry.field
    def hello(self, info: Info) -> HelloResponse:
        request: Request = info.context["request"]
        print(request.headers)
        user_agent = request.headers.get("user-agent", "Unknown")
        custom_header = request.headers.get("myheader", "UnDefined")
        return HelloResponse(
            message="Hello!",
            user_agent=user_agent,
            custom_header=custom_header)
    
    """
    使用 Cursored-based Pagination 時有一個非常重要的要求，那就是資料必須有明確且固定的排序機制，不然 cursor 就失去了紀錄位址的功能。
    # """
    # @strawberry.field
    # def get_user(self, 
    #             id: Optional[int] = None, 
    #             username: Optional[str] = None,
    #             cursor: Optional[int] = None, 
    #             limit: int = 10) -> List[UserType]:
    #     db = get_db_session()
    #     query = db.query(UserModel)

    #     if id:
    #         query = query.filter(UserModel.id == id)
    #     elif username:
    #         query = query.filter(UserModel.username == username)
    #     else:
    #         if cursor:
    #             query = query.filter(UserModel.id > cursor)
    #         query = query.order_by(UserModel.id).limit(limit)
        
    #     users = query.all()

    #     if not users:
    #         raise HTTPException(status_code=404, detail="No user found")
        
    #     def convert_post(post):
    #         return PostType(
    #             id=post.id,
    #             title=post.title,
    #             content=post.content,
    #             author_id=post.author.id,
    #             author_name=post.author.username
    #         )
        
    #     result = [UserType(
    #         id=user.id, 
    #         username=user.username, 
    #         email=user.email, 
    #         posts=[convert_post(p) for p in user.posts],
    #         signup_time=user.signup_time,
    #         expired_time=user.expired_time,
    #         cursor=user.id  # 設置游標字段
    #     ) for user in users]

    #     return result
    
    """
    Offset/limit-based Pagination
    """
    @strawberry.field
    def get_user(self, 
                 id: Optional[int] = None, 
                 username: Optional[str] = None,
                 limit: int = 10, 
                 offset: int = 0) -> List[UserType]:
        # db = next(get_db()) # 容易導致 Session 洩漏
        db = get_db_session()  # 正確管理 DB session
        
        query = db.query(UserModel)
    
        if id:
            query = query.filter(UserModel.id == id)
        elif username:
            query = query.filter(UserModel.username == username)
        
        query = query.offset(offset).limit(limit)
        users = query.all()

        if not users:
            raise HTTPException(status_code=404, detail="No user found")
        
        def convert_post(post):
            return PostType(
                id=post.id,
                title=post.title,
                content=post.content,
                author_id=post.author.id,
                author_name=post.author.username
            )
    
        return [UserType(
            id=_.id, 
            username=_.username, 
            email=_.email, 
            posts=[convert_post(p) for p in _.posts],
            signup_time=_.signup_time,
            expired_time=_.expired_time) for _ in users]
    

    @strawberry.field
    def get_post(self, id: int) -> PostType:
        # db = next(get_db())
        db = get_db_session()
        post = db.query(PostModel).filter(PostModel.id == id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return PostType(id=post.id, title=post.title, content=post.content, author_id=post.author.id, author_name=post.author.username)
    
    # @strawberry.field
    # def get_users(self) -> List[UserType]:
    #     # db = next(get_db())
    #     db = get_db_session()
    #     users = db.query(UserModel).all()
    #     return [UserType(
    #         id=user.id, 
    #         username=user.username, 
    #         email=user.email, 
    #         posts=user.posts,
    #         signup_time=user.signup_time,
    #         expired_time=user.expired_time) for user in users]
    
    @strawberry.field
    def get_posts(self) -> List[PostType]:
        # db = next(get_db())
        db = get_db_session()
        posts = db.query(PostModel).all()
        return [PostType(id=post.id, title=post.title, content=post.content, author_id=post.author.id, author_name=post.author.username) for post in posts]
    
    # 為查詢提供一個解析器
    @strawberry.field
    def search(self, keyword: str) -> List[SearchResult]:
        # db = next(get_db())
        db = get_db_session()
        keyword_filter = f"%{keyword}%"

        user_results = db.query(UserModel).filter(UserModel.username.ilike(keyword_filter)).all()
        post_results = db.query(PostModel).filter(PostModel.title.ilike(keyword_filter)).all()

        # 將結果轉換為 Strawberry 類型
        results = []
        for user in user_results:
            results.append(UserType(
                id=user.id,
                username=user.username,
                email=user.email,
                posts=user.posts,
                signup_time=user.signup_time,
                expired_time=user.expired_time,
            ))
        for post in post_results:
            results.append(PostType(
                id=post.id,
                title=post.title,
                content=post.content,
                author_id=post.author.id,
                author_name=post.author.username,
            ))

        return results

upload_progress = {}
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, username: str, email: str) -> UserType:
        # user_info = {
        #     "username": username,
        #     "email": email
        # }
        # gen_user_token = create_access_token(user_info)

        # db = next(get_db())
        db = get_db_session()
        new_user = UserModel(username=username, email=email)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserType(id=new_user.id, 
                        username=new_user.username, 
                        email=new_user.email, 
                        posts=new_user.posts,
                        signup_time=new_user.signup_time,
                        expired_time=new_user.expired_time)

    @strawberry.mutation
    def create_post(self, title: str, content: str, author_id: strawberry.ID) -> PostType:
        # db = next(get_db())
        db = get_db_session()
        new_post = PostModel(title=title, content=content, author_id=author_id)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return PostType(id=new_post.id, title=new_post.title, content=new_post.content, author_id=new_post.author.id, author_name=new_post.author.username)

    @strawberry.mutation
    def update_user(self, id: strawberry.ID, username: Optional[str] = None, email: Optional[str] = None) -> UserType:
        # db = next(get_db())
        db = get_db_session()
        user = db.query(UserModel).filter(UserModel.id == id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.username = username
        user.email = email
        db.commit()
        db.refresh(user)
        return UserType(
            id=user.id, 
            username=user.username, 
            email=user.email, 
            posts=user.posts,
            signup_time=user.signup_time,
            expired_time=user.expired_time)

    @strawberry.mutation
    def delete_user(self, id: strawberry.ID) -> UserType:
        #TODO: posts not deleted
        # db = next(get_db())
        db = get_db_session()
        user = db.query(UserModel).filter(UserModel.id == id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        return UserType(
            id=user.id, 
            username=user.username, 
            email=user.email, 
            posts=user.posts,
            signup_time=user.signup_time,
            expired_time=user.expired_time)
    
    # @strawberry.mutation
    # async def upload_file(self, file_id: str) -> str:
    #     """模擬上傳文件 (假設為背景任務)"""
    #     upload_progress[file_id] = 0  # 初始化進度

    #     for i in range(1, 11):
    #         await asyncio.sleep(0.5)  # 模擬處理時間
    #         upload_progress[file_id] = i * 10  # 更新進度
        
    #     return f"檔案 {file_id} 上傳完成"
    
    # """
    # mutation upoloadFile{
    #     uploadFile(fileId: "file1.txt")
    # }
    # """


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def count(self, up_to: int) -> AsyncGenerator[int, None]:
        for i in range(up_to):
            print(f"Subscription: {i}")
            yield i
            await asyncio.sleep(0.5)

    @strawberry.subscription
    async def file_upload_progress(self, file_id: str) -> AsyncGenerator[int, None]:
        """訂閱檔案上傳進度"""
        while file_id in upload_progress and upload_progress[file_id] < 100:
            yield upload_progress[file_id]
            await asyncio.sleep(0.5)  # 每 0.5 秒推送一次進度

        yield 100 # 確保最後 100% 狀態被傳送

    @strawberry.subscription
    async def upload_progress(self, file_id: str) -> AsyncGenerator[int, None]:
        """GraphQL 訂閱檔案上傳進度"""
        while True:
            progress = redis_conn.hget("upload_progress", file_id)
            if progress is None:
                yield 0  # 預設回傳 0%
            else:
                yield int(progress)
                if int(progress) == 100:
                    break  # 上傳完成後停止
            await asyncio.sleep(1)  # 每秒回傳一次

""" 應用情境 - 檔案上傳進度追蹤
使用 FastAPI POST API 處理檔案上傳，並使用 BackgroundTasks (檔案上傳可能會超過 1 分鐘，或需要追蹤進度，建議使用 Redis Queue！)
使用 GraphQL Subscription 監聽上傳進度
"""

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
# graphql_app = GraphQL(schema)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="FastAPI + GraphQL Example", version="1.0.0")
# app.add_route("/graphql", graphql_app)
app.include_router(graphql_app, prefix="/graphql")

# API 端點：處理檔案上傳
@app.post("/upload/")
async def upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """處理檔案上傳，並在背景執行模擬的上傳進度"""
    file_id = file.filename
    # background_tasks.add_task(upload_file_simulation, file_id)  # 在背景執行上傳
    queue.enqueue(upload_file_simulation2, file_id)  # 加入任務佇列
    return {"message": "上傳開始", "file_id": file_id}

# 模擬檔案上傳的背景任務
async def upload_file_simulation(file_id: str):
    upload_progress[file_id] = 0
    for i in range(1, 11):
        print(upload_progress)
        await asyncio.sleep(0.5)  # 模擬上傳過程
        upload_progress[file_id] = i * 10
    upload_progress[file_id] = 100
    print(upload_progress)

async def upload_file_simulation2(file_id: str):
    """模擬檔案上傳進度"""
    redis_conn.hset("upload_progress", file_id, 0)  # 初始化進度

    for i in range(1, 11):
        time.sleep(0.5)  # 模擬上傳過程
        redis_conn.hset("upload_progress", file_id, i * 10)  # 更新進度

    redis_conn.hset("upload_progress", file_id, 100)  # 完成

# 啟用 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 設置允許的前端 URL
    allow_credentials=True,
    allow_methods=["*"],  # 設置允許的 HTTP 方法
    allow_headers=["*"],  # 設置允許的 Header
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("Database connected on startup")

    yield

    engine.dispose()
    print("Database disconnected on shutdown")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

class Fruit(BaseModel):
	name: str
	price: float

FRUIT_DATABASE = [
	Fruit(name="蘋果", price=10.0),
	Fruit(name="香蕉", price=5.0),
	Fruit(name="橘子", price=8.0),
	Fruit(name="芭樂", price=7.0),
	Fruit(name="西瓜", price=15.0),
	Fruit(name="梨子", price=6.0),
	Fruit(name="櫻桃", price=20.0),
	Fruit(name="葡萄", price=12.0),
	Fruit(name="橙子", price=9.0),
	Fruit(name="柚子", price=11.0),
]

MAX_ITEMS = 10
DEFAULT_SKIP = 0
@app.get("/welcome", operation_id="get_welcome_message")
async def get_welcome_message():
	return {"message": "歡迎使用水果 API"}

@app.get("/fruits/{fruit_id}", operation_id="get_fruit_by_id")
async def get_fruit_by_id(fruit_id: int) -> Fruit:
	try:
		return FRUIT_DATABASE[fruit_id]
	except IndexError:
		raise HTTPException(status_code=404, detail="找不到指定 ID 的水果")
		
@app.get("/fruits/", operation_id="get_fruits")
async def get_fruits(skip: int = DEFAULT_SKIP, limit: int = MAX_ITEMS):
	return FRUIT_DATABASE[skip : skip + limit]

class ContentModel(BaseModel):
    content: str
    collection_name: str = "dify_upload"

# create a endpoint to save file to mongo
@app.post("/save_to_mongo/", operation_id="save_to_mongo")
async def save_to_mongo(input_data: ContentModel):    
    md_string = input_data.content
    data = [line.split('|')[1:-1] for line in md_string.strip().split('\n')]
    columns = [ _.strip() for _ in data[0]]
    cleaned_data = [[item.strip() for item in row] for row in data[2:]]
    df = pd.DataFrame(cleaned_data, columns=columns)
    df["created_datetime"] = datetime.now()
    data = df.to_dict(orient="records")
    # data = [dict(zip(columns, row)) for row in cleaned_data]
    
    collection_id = uuid.uuid4().hex[:16]
    db = client["dify"]
    collection = db[f"{input_data.collection_name}_{collection_id}"]
    collection.insert_many(data)
    return {"message": "Data saved successfully"}

# db = client["mydatabase"]
# collection = db["texts"]

# print("成功連接 MongoDB！")
# collection.insert_one({"message": "Hello from FastAPI & MongoDB!"})
# print("插入測試數據成功！")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple_main:app", host="0.0.0.0", port=9000, reload=True)


""" create a new user
mutation {
    createUser(username: "regina", email: "regina@example.com") {
        id
        username
        email
    }
}
"""

""" create a new post
mutation {
    createPost(title: "My First Post", content: "This is my first post!", authorId: 1) {
        id
        title
        content
    }
}
"""

""" get user by id
query {
    getUser(id: 1) {
        id
        username
        email
        posts {
                id
                title
                content
            }
    }
}


query {
    getUser(id: 1) {
        id
        username
        posts {
                id
                title
            }
    }
}

query {
    getUser(id: 1) {
        id
        username
    }
}
"""

""" get post by id
query {
    getPost(id: 1) {
        id
        title
        content
    }
}
"""

""" get all users
query{
  getUsers {
    id
    username
    email
    posts {
      id
      title
      content
    }
  }
}
"""

""" get all posts
query{
  getPosts {
    id
    title
    content
  }
}


query{
  getPosts {
    id
    title
    content
    authorId
  }
}


query{
  getPosts {
    id
    title
    content
    authorId
    authorName
  }
}
"""

""" update user
mutation {
    updateUser(id: 1, username: "regina", email: "regina@example.com") {
        id
        username
        email
    }
}
"""

""" delete user
mutation {
    deleteUser(id: 1) {
        id
        username
        email
    }
}
"""

""" CURL """
# curl -X POST http://localhost:9001/graphql -H "Content-Type: application/json" -d '{"query": "query { getPosts { id title content authorId authorName } }"}'
# curl -X POST http://localhost:9001/graphql -H "Content-Type: application/json" -d '{"query": "query { getUsers { id username email posts { id title content } } }"}'
# curl -X POST http://localhost:9001/graphql -H "Content-Type: application/json" -d '{"query": "query { getUser(id: 1) { id username email posts { id title content } } }"}'
# curl -X POST http://localhost:9001/graphql -H "Content-Type: application/json" -d '{"query": "query { getPost(id: 1) { id title content } }"}'
# curl -X POST http://localhost:9001/graphql -H "Content-Type: application/json" -d '{"query": "query { getPost(id: 1) { id title content authorName } }"}'
"""
curl -X POST http://localhost:9001/graphql \
-H "Content-Type: application/json" \
-d '{"query": "mutation { createUser(username: \"lily\", email: \"lily@example.com\") { id username email } }"}'
"""
"""
curl -X POST http://localhost:9001/graphql \
-H "Content-Type: application/json" \
-d '{"query": "mutation { createPost(title: \"My First Post\", content: \"This is my first post!\", authorId: 2) { id title content } }"}'
"""


""" curl with variable
curl -X POST http://localhost:9000/graphql -H "Content-Type: application/json" -d '{"query": "query user($username: String) { getUser(username: $username) { id username email } }", "variables": {"username": "regina"}}'

"""

""" curl with header
curl -X POST http://localhost:9000/graphql -H "Content-Type: application/json" -d '{"query": "query { hello { message userAgent customHeader } }"}'


curl -X POST http://localhost:9000/graphql -H "Content-Type: application/json" -H "myheader: exampleHeaderInfo" -d '{"query": "query { hello { message userAgent customHeader } }"}'
"""


"""
curl -X POST http://localhost:9000/graphql \
    -H "Content-Type: application/json" \
    -d '{"query": "query ReadUser { user1: getUser(username: \"regina\") { id username posts { id } signupTime expiredTime } user2: getUser(username: \"lily\") { id username posts { id } signupTime expiredTime } }"}'
"""

"""
fragment UserFields on UserType {
  id
  username
}

fragment PostFields on PostType {
  id
  title
}

query {
  search(keyword: "regina") {
    ...UserFields
    ...PostFields
  }
}
"""

"""
subscription {
  count(upTo: 5)
}

subscription sub_file_upload{
  fileUploadProgress(fileId: "example.txt")
}
"""

"""
query ReadUser {
  getUser(offset:1, limit: 3) {
    id
    username
    posts {
      id
    }
    signupTime
    expiredTime
  }
}
"""

"""
query {
  getUser(cursor: 4, limit: 5) {
    id
    username
    email
    cursor
    posts {
      id
      title
      content
      authorId
      authorName
    }
    signupTime
    expiredTime
  }
}
"""