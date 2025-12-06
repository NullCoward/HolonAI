"""
HolonAction - A binding to an executable function with metadata for AI consumption.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional

import attrs


@attrs.define
class ActionParameter:
    """Represents a single parameter in an action's signature."""
    name: str
    type_hint: Optional[str] = None
    default: Optional[Any] = None
    has_default: bool = False


@attrs.define
class ActionSignature:
    """Auto-derived signature information from a callable."""
    parameters: list[ActionParameter] = attrs.Factory(list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None

    @classmethod
    def from_callable(cls, func: Callable) -> ActionSignature:
        """Extract signature information from a callable."""
        sig = inspect.signature(func)
        params = []

        for name, param in sig.parameters.items():
            type_hint = None
            if param.annotation != inspect.Parameter.empty:
                type_hint = (
                    param.annotation.__name__
                    if hasattr(param.annotation, '__name__')
                    else str(param.annotation)
                )

            has_default = param.default != inspect.Parameter.empty
            default = param.default if has_default else None

            params.append(ActionParameter(
                name=name,
                type_hint=type_hint,
                default=default,
                has_default=has_default
            ))

        return_type = None
        if sig.return_annotation != inspect.Signature.empty:
            return_type = (
                sig.return_annotation.__name__
                if hasattr(sig.return_annotation, '__name__')
                else str(sig.return_annotation)
            )

        return cls(
            parameters=params,
            return_type=return_type,
            docstring=inspect.getdoc(func)
        )


@attrs.define
class HolonAction:
    """
    A binding to a callable function with metadata for AI consumption.

    Attributes:
        callback: The function to execute
        name: Identifier (auto-derived from func path, or overridden)
        purpose: Optional description of what this action does
        signature: Auto-derived signature information
    """
    callback: Callable = attrs.field(repr=False)
    name: Optional[str] = None
    purpose: Optional[str] = None
    signature: Optional[ActionSignature] = attrs.field(default=None, repr=False)

    def __attrs_post_init__(self):
        # Auto-derive name from callback if not provided
        if self.name is None:
            object.__setattr__(self, 'name', self._derive_name(self.callback))

        # Auto-derive signature from callback
        if self.signature is None:
            object.__setattr__(self, 'signature', ActionSignature.from_callable(self.callback))

    def _derive_name(self, func: Callable) -> str:
        """Derive a dot.path name from a callable."""
        module = getattr(func, '__module__', None)
        qualname = getattr(func, '__qualname__', func.__name__)

        if module and module != '__main__':
            return f"{module}.{qualname}"
        return qualname

    def execute(self, **kwargs) -> Any:
        """Execute the action's callback with the given arguments."""
        return self.callback(**kwargs)
