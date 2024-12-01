
import strawberry
from typing import Optional, List

from database import SessionLocal
from handler.utils import get_user_data
from model.graphql.user import User
from model.sqlalchemy.user import UserModel

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: Optional[int] = None) -> List[User]:
        try:
            return get_user_data(id)
        except ValueError as e:
            raise ValueError(str(e))
    
# fake data
# @strawberry.type
# class Query:
#     @strawberry.field
#     def user(self, id: Optional[int] = None) -> List[User]:
#         if id:
#             return [User(
#                 id=id, 
#                 name=fake.name(), 
#                 age=fake.random_int(min=18, max=80))]
        
#         return [User(
#             id=fake.uuid4(),
#             name=fake.name(),
#             age=fake.random_int(min=18, max=80)
#         ) for _ in range(5)]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, name: str, age: int) -> User:
        db = SessionLocal()
        user = UserModel(name=name, age=age)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return User(id=user.id, name=user.name, age=user.age)