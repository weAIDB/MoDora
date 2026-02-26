from typing import Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def pydantic_dump(obj: Any) -> Any:
    """Compatible with different versions of Pydantic export methods.

    Args:
        obj (Any): The Pydantic model instance or object to dump.

    Returns:
        Any: The dumped data (usually a dictionary).
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def pydantic_validate(model_cls: Type[T], obj: Any) -> T:
    """Compatible with different versions of Pydantic validation methods.

    Args:
        model_cls (Type[T]): The Pydantic model class.
        obj (Any): The object to validate.

    Returns:
        T: The validated model instance.
    """
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(obj)
    if hasattr(model_cls, "parse_obj"):
        return model_cls.parse_obj(obj)
    return model_cls(**obj)
