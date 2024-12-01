import uvicorn
import strawberry

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from strawberry.asgi import GraphQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from faker import Faker
from typing import Optional, List

from router.user import router as router_user
from handler.utils import get_user_data
from model.sqlalchemy.user import UserModel
from model.graphql.user import User
from handler.schema import Query, Mutation

from database import engine, Base, SessionLocal, get_db

fake = Faker()

# DB init
Base.metadata.create_all(bind=engine)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQL(schema)

app = FastAPI(title="FastAPI + GraphQL Example", version="1.0.0")
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)
app.include_router(router_user)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/api/v1/health", summary="Health Check", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok", "message": "Service is running"})

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