from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional, List

from model.sqlalchemy.user import UserModel
# from model.graphql.user import User


DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base =  declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_user_data(user_id: Optional[int] = None) -> List[UserModel]:
    db = SessionLocal()
    if user_id is None:
        db_user = db.query(UserModel).all()
    else:
        db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user:
            raise ValueError(f"User with id {user_id} not found")
        db_user = [db_user] if db_user else []
    db.close()
    
    print(db_user)
    user_list = [UserModel(id=user.id, name=user.name, age=user.age) for user in db_user]
    return user_list