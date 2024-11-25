import strawberry

@strawberry.type
class User:
    id: str
    name: str
    age: int