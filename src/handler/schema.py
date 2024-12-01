
import strawberry
from typing import Optional, List

from database import SessionLocal
from handler.utils import get_user_data, create_user, update_user, delete_user
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
        new_user = create_user(name, age)
        return new_user
    
    @strawberry.mutation
    def update_user(self, id: int, name: Optional[str] = None, age: Optional[int] = None) -> User:
        user = update_user(id, name, age)
        return user

    @strawberry.mutation
    def delete_user(self, id: int) -> bool:
        user = delete_user(id)
        return user