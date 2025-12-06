"""
Container classes for Holon components - HolonPurpose, HolonSelf, and HolonActions.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, Callable, Iterator, Union

import attrs
import cattrs

from .action import HolonAction

if TYPE_CHECKING:
    from .holon import Holon


def _is_function(obj: Any) -> bool:
    """Check if obj is an actual function/lambda (not a callable class instance)."""
    return isinstance(obj, (types.FunctionType, types.MethodType))


def _unstructure_value(value: Any) -> Any:
    """
    Convert a value to a JSON-serializable form.

    - Nested Holons use to_dict()
    - Dataclasses/attrs classes use cattrs
    - Regular class instances use __dict__
    - Primitives pass through as-is
    """
    # Nested Holons
    if hasattr(value, 'to_dict'):
        return value.to_dict()

    # Try cattrs for dataclasses/attrs
    try:
        unstructured = cattrs.unstructure(value)
        # cattrs returns the same object for unknown types, so check if it changed
        if unstructured is not value:
            return unstructured
    except Exception:
        pass

    # Regular class instances with __dict__
    if hasattr(value, '__dict__') and not _is_function(value):
        return value.__dict__

    return value


@attrs.define
class HolonBinding:
    """
    A binding to a code object that resolves its value at runtime.

    - Functions/lambdas are automatically invoked at resolve time
    - Class instances are serialized via cattrs or __dict__
    - Primitives are returned as-is
    """
    source: Union[Callable[[], Any], Any] = attrs.field(repr=False)
    key: str | None = None

    def resolve(self) -> Any:
        """Resolve the binding to its current value."""
        if _is_function(self.source):
            return self.source()
        return _unstructure_value(self.source)


@attrs.define
class HolonPurpose:
    """
    The interpretive lens for a Holon.

    Contains bindings that define HOW the AI should interpret the Self state.
    Can hold any combination of primitives, objects, or callable bindings.
    """
    _items: list[HolonBinding] = attrs.Factory(list)

    def add(
        self,
        item: Any,
        *,
        key: str | None = None
    ) -> HolonPurpose:
        """Add an item to the purpose."""
        self._items.append(HolonBinding(source=item, key=key))
        return self

    def _has_any_keys(self) -> bool:
        return any(item.key is not None for item in self._items)

    def _all_have_keys(self) -> bool:
        return bool(self._items) and all(item.key is not None for item in self._items)

    def resolve(self) -> list[Any]:
        """Resolve all bindings as a list."""
        return [item.resolve() for item in self._items]

    def serialize(self) -> list[Any] | dict[str, Any]:
        """Smart serialization: list if unkeyed, dict if keyed, mixed handled."""
        if not self._items:
            return []

        if self._all_have_keys():
            return {item.key: item.resolve() for item in self._items}
        elif not self._has_any_keys():
            return self.resolve()
        else:
            # Mixed: list with keyed items as embedded dicts
            result = []
            for item in self._items:
                value = item.resolve()
                if item.key is not None:
                    result.append({item.key: value})
                else:
                    result.append(value)
            return result

    def __iter__(self) -> Iterator[Any]:
        return iter(self.resolve())

    def __len__(self) -> int:
        return len(self._items)


@attrs.define
class HolonSelf:
    """
    The current state/context for a Holon.

    Contains bindings that define WHAT the AI should interpret.
    Can hold any combination of primitives, objects, nested Holons, or callable bindings.
    """
    _items: list[HolonBinding] = attrs.Factory(list)

    def add(
        self,
        item: Any,
        *,
        key: str | None = None
    ) -> HolonSelf:
        """Add an item to self."""
        self._items.append(HolonBinding(source=item, key=key))
        return self

    def _has_any_keys(self) -> bool:
        return any(item.key is not None for item in self._items)

    def _all_have_keys(self) -> bool:
        return bool(self._items) and all(item.key is not None for item in self._items)

    def resolve(self) -> list[Any]:
        """Resolve all bindings as a list."""
        return [item.resolve() for item in self._items]

    def serialize(self) -> list[Any] | dict[str, Any]:
        """Smart serialization: list if unkeyed, dict if keyed, mixed handled."""
        if not self._items:
            return []

        if self._all_have_keys():
            return {item.key: item.resolve() for item in self._items}
        elif not self._has_any_keys():
            return self.resolve()
        else:
            # Mixed: list with keyed items as embedded dicts
            result = []
            for item in self._items:
                value = item.resolve()
                if item.key is not None:
                    result.append({item.key: value})
                else:
                    result.append(value)
            return result

    def __iter__(self) -> Iterator[Any]:
        return iter(self.resolve())

    def __len__(self) -> int:
        return len(self._items)


@attrs.define
class HolonActions:
    """
    Collection of available actions for a Holon.

    Contains HolonAction objects that the AI can invoke.
    """
    _actions: dict[str, HolonAction] = attrs.Factory(dict)

    def add(
        self,
        action: Union[HolonAction, Callable],
        *,
        name: str | None = None,
        purpose: str | None = None
    ) -> HolonActions:
        """Add an action."""
        if isinstance(action, HolonAction):
            self._actions[action.name] = action
        else:
            holon_action = HolonAction(
                callback=action,
                name=name,
                purpose=purpose
            )
            self._actions[holon_action.name] = holon_action
        return self

    def get(self, name: str) -> HolonAction | None:
        """Get an action by name."""
        return self._actions.get(name)

    def execute(self, name: str, **kwargs) -> Any:
        """Execute an action by name."""
        action = self._actions.get(name)
        if action is None:
            raise KeyError(f"Action not found: {name}")
        return action.execute(**kwargs)

    def __iter__(self) -> Iterator[HolonAction]:
        return iter(self._actions.values())

    def __len__(self) -> int:
        return len(self._actions)

    def __contains__(self, name: str) -> bool:
        return name in self._actions
