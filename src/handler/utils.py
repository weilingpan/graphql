from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from model.sqlalchemy.user import UserModel
from model.graphql.user import User


DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base =  declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_user_data(user_id: int) -> User:
    db = SessionLocal()
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    db.close()
    if not db_user:
        raise ValueError(f"User with id {user_id} not found")
    return User(id=db_user.id, name=db_user.name, age=db_user.age)
