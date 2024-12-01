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