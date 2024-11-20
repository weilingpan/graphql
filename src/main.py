import uvicorn
import strawberry
import dataclasses
from fastapi import FastAPI, HTTPException
from strawberry.asgi import GraphQL
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi.responses import JSONResponse


DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base =  declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)

# DB init
Base.metadata.create_all(bind=engine)

# GraphQL
@strawberry.type
class User:
    name: str
    age: int

def get_user_data(user_id: int) -> User:
    db = SessionLocal()
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    db.close()
    if not db_user:
        raise ValueError(f"User with id {user_id} not found")
    return User(name=db_user.name, age=db_user.age)

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> User:
        try:
            return get_user_data(id)
        except ValueError as e:
            raise ValueError(str(e))

schema = strawberry.Schema(query=Query)
graphql_app = GraphQL(schema)

app = FastAPI(title="FastAPI + GraphQL Example", version="1.0.0")
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

@app.get("/api/v1/health", summary="Health Check", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok", "message": "Service is running"})

@app.get("/api/v1/users/{user_id}", summary="Get User by ID", tags=["User"])
async def get_user(user_id: int):
    try:
        user = get_user_data(user_id)
        print(type(user))
        print(user)
        return JSONResponse(content=dataclasses.asdict(user))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    # insert data to db
    db = SessionLocal()
    if not db.query(UserModel).first():
        print(f"insert data to db ...")
        db.add(UserModel(name="Regina", age=20))
        db.add(UserModel(name="Amy", age=30))
        db.commit()
    else:
        print(f"data is already")
    db.close()


    uvicorn.run(app, host="0.0.0.0", port=9000)
    # go to http://localhost:9000/graphql, it will show GraphQL Playground
    # query {
    # user(id: 1) {
    #     name
    #     age
    # }
    # }

    # curl -X POST http://localhost:9000/graphql -H "Content-Type: application/json" -d '{"query": "query { user(id: 1) { name age } }"}'