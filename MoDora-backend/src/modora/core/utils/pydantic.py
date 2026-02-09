from typing import Any, Type, TypeVar, Union
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def pydantic_dump(obj: Any) -> Any:
    """兼容不同版本的 Pydantic 导出方法"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

def pydantic_validate(model_cls: Type[T], obj: Any) -> T:
    """兼容不同版本的 Pydantic 验证方法"""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(obj)
    if hasattr(model_cls, "parse_obj"):
        return model_cls.parse_obj(obj)
    return model_cls(**obj)
