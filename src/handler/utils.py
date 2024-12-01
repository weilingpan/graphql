from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import Depends

from model.sqlalchemy.user import UserModel
# from model.graphql.user import User
from database import get_db

def get_user_data(user_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[UserModel]:
    db = next(get_db())
    if user_id is None:
        db_user = db.query(UserModel).all()
    else:
        db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user:
            raise ValueError(f"User with id {user_id} not found")
        db_user = [db_user] if db_user else []
    
    print(db_user)
    user_list = [UserModel(id=user.id, name=user.name, age=user.age) for user in db_user]
    return user_list

def create_user(name: str, age: int, db: Session = Depends(get_db)) -> UserModel:
    db = next(get_db())
    user = UserModel(name=name, age=age)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserModel(id=user.id, name=user.name, age=user.age)

def update_user(id: int, name: Optional[str], age: Optional[int], db: Session = Depends(get_db)):
    db = next(get_db())
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if user:
        if name:
            user.name = name
        if age:
            user.age = age
        db.commit()
        db.refresh(user)
        return user
    return None

def delete_user(id: int, db: Session = Depends(get_db)) -> bool:
    db = next(get_db())
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False