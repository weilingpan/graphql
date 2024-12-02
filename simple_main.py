import strawberry
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from strawberry.asgi import GraphQL
from sqlalchemy import ForeignKey, create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from strawberry.fastapi import GraphQLRouter


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

    # Relationships
    posts = relationship("PostModel", back_populates="author")


# DB init
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define GraphQL schema
@strawberry.type
class PostType:
    id: int
    title: str
    content: str
    author_id: int
    author_name: str

@strawberry.type
class UserType:
    id: int
    username: str
    email: str
    posts: List[PostType]

# Define GraphQL Query and Mutation
@strawberry.type
class Query:
    @strawberry.field
    def get_user(self, id: int) -> UserType:
        db = next(get_db())
        user = db.query(UserModel).filter(UserModel.id == id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserType(id=user.id, username=user.username, email=user.email, posts=user.posts)

    @strawberry.field
    def get_post(self, id: int) -> PostType:
        db = next(get_db())
        post = db.query(PostModel).filter(PostModel.id == id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return PostType(id=post.id, title=post.title, content=post.content, author_id=post.author.id, author_name=post.author.username)
    
    @strawberry.field
    def get_users(self) -> List[UserType]:
        db = next(get_db())
        users = db.query(UserModel).all()
        return [UserType(id=user.id, username=user.username, email=user.email, posts=user.posts) for user in users]
    
    @strawberry.field
    def get_posts(self) -> List[PostType]:
        db = next(get_db())
        posts = db.query(PostModel).all()
        return [PostType(id=post.id, title=post.title, content=post.content, author_id=post.author.id, author_name=post.author.username) for post in posts]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, username: str, email: str) -> UserType:
        db = next(get_db())
        new_user = UserModel(username=username, email=email)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserType(id=new_user.id, username=new_user.username, email=new_user.email, posts=new_user.posts)

    @strawberry.mutation
    def create_post(self, title: str, content: str, author_id: int) -> PostType:
        db = next(get_db())
        new_post = PostModel(title=title, content=content, author_id=author_id)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return PostType(id=new_post.id, title=new_post.title, content=new_post.content, author_id=new_post.author.id, author_name=new_post.author.username)

    @strawberry.mutation
    def update_user(self, id: int, username: str, email: str) -> UserType:
        db = next(get_db())
        user = db.query(UserModel).filter(UserModel.id == id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.username = username
        user.email = email
        db.commit()
        db.refresh(user)
        return UserType(id=user.id, username=user.username, email=user.email, posts=user.posts)

    @strawberry.mutation
    def delete_user(self, id: int) -> UserType:
        #TODO: posts not deleted
        db = next(get_db())
        user = db.query(UserModel).filter(UserModel.id == id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        return UserType(id=user.id, username=user.username, email=user.email, posts=user.posts)

schema = strawberry.Schema(query=Query, mutation=Mutation)
# graphql_app = GraphQL(schema)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="FastAPI + GraphQL Example", version="1.0.0")
# app.add_route("/graphql", graphql_app)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

#TODO: update/delete

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