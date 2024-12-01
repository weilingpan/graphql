import strawberry

@strawberry.type
class User:
    id: int
    name: str
    age: int