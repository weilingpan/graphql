import uvicorn
import strawberry
from fastapi import FastAPI
from strawberry.asgi import GraphQL
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


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


@strawberry.type
class Query:
    # @strawberry.field
    # def user(self) -> User:
    #     return User(name="Patrick", age=100)
    
    @strawberry.field
    def user(self, id: int) -> User:
        db = SessionLocal()
        db_user = db.query(UserModel).filter(UserModel.id == id).first()
        db.close()
        if db_user:
            return User(name=db_user.name, age=db_user.age)
        raise ValueError("User not found")


schema = strawberry.Schema(query=Query)
graphql_app = GraphQL(schema)

app = FastAPI()
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

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