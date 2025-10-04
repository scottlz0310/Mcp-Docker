"""Utility for evaluating GitHub Actions style expressions."""

from __future__ import annotations

import ast
from typing import Any, Dict, Iterable, Mapping, Sequence, cast


class ExpressionEvaluationError(Exception):
    """Raised when an expression could not be evaluated safely."""


class ExpressionEvaluator:
    """Evaluate a limited subset of GitHub Actions expressions safely."""

    _TRUE_VALUES = {"true", "True"}
    _FALSE_VALUES = {"false", "False"}

    def __init__(self, functions: Mapping[str, Any] | None = None) -> None:
        self._functions: Dict[str, Any] = dict(functions or {})

    def evaluate(self, expression: str, context: Mapping[str, Any]) -> bool:
        """Return the truthiness of *expression* within *context*."""

        expr = (expression or "").strip()
        if not expr:
            return True

        if expr.startswith("${{") and expr.endswith("}}"):
            # strip template wrapper
            expr = expr[3:-2].strip()

        if not expr:
            return True

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:  # pragma: no cover - invalid expression
            raise ExpressionEvaluationError(str(exc)) from exc

        try:
            value = self._evaluate_node(tree.body, context)
        except ExpressionEvaluationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ExpressionEvaluationError(str(exc)) from exc

        return bool(value)

    def _evaluate_node(self, node: ast.AST, context: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [self._evaluate_node(value, context) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
            raise ExpressionEvaluationError(f"unsupported boolean operator: {ast.dump(node)}")

        if isinstance(node, ast.UnaryOp):
            operand = self._evaluate_node(node.operand, context)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            raise ExpressionEvaluationError(f"unsupported unary operator: {ast.dump(node)}")

        if isinstance(node, ast.Compare):
            left_value = self._evaluate_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right_value = self._evaluate_node(comparator, context)
                if not self._evaluate_compare(left_value, right_value, op):
                    return False
                left_value = right_value
            return True

        if isinstance(node, ast.Call):
            func = self._evaluate_node(node.func, context)
            if not callable(func):
                raise ExpressionEvaluationError("attempted to call a non-callable object")
            if node.keywords:
                raise ExpressionEvaluationError("keyword arguments are not supported")
            args = [self._evaluate_node(arg, context) for arg in node.args]
            try:
                return func(*args)
            except ExpressionEvaluationError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                raise ExpressionEvaluationError(str(exc)) from exc

        if isinstance(node, ast.Attribute):
            value = self._evaluate_node(node.value, context)
            if isinstance(value, Mapping):
                value_map = cast(Mapping[str, Any], value)
                if node.attr not in value_map:
                    raise ExpressionEvaluationError(f"attribute '{node.attr}' not found in mapping")
                return cast(Any, value_map[node.attr])
            try:
                return getattr(value, node.attr)
            except AttributeError as exc:
                raise ExpressionEvaluationError(f"attribute '{node.attr}' not found") from exc

        if isinstance(node, ast.Subscript):
            base_value = self._evaluate_node(node.value, context)
            index_node = node.slice
            if isinstance(index_node, ast.Slice):
                raise ExpressionEvaluationError("slice notation is not supported")
            key_value = self._evaluate_node(index_node, context)
            if isinstance(base_value, Mapping):
                return cast(Any, base_value.get(key_value))
            if isinstance(base_value, Sequence) and not isinstance(base_value, (str, bytes, bytearray)):
                try:
                    return cast(Any, base_value[key_value])
                except (IndexError, TypeError) as exc:
                    raise ExpressionEvaluationError(str(exc)) from exc
            if isinstance(base_value, (str, bytes, bytearray)):
                try:
                    return cast(Any, base_value[key_value])
                except (IndexError, TypeError) as exc:
                    raise ExpressionEvaluationError(str(exc)) from exc
            raise ExpressionEvaluationError("unsupported subscript target")

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self._resolve_name(node.id, context)

        if isinstance(node, ast.List):
            return [self._evaluate_node(elt, context) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._evaluate_node(elt, context) for elt in node.elts)

        if isinstance(node, ast.Dict):
            result: Dict[Any, Any] = {}
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:
                    raise ExpressionEvaluationError("dict unpacking is not supported")
                result[self._evaluate_node(key_node, context)] = self._evaluate_node(value_node, context)
            return result

        raise ExpressionEvaluationError(f"unsupported expression: {ast.dump(node)}")

    def _resolve_name(self, name: str, context: Mapping[str, Any]) -> Any:
        if name in self._functions:
            return self._functions[name]
        if name in context:
            return context[name]
        if name in self._TRUE_VALUES:
            return True
        if name in self._FALSE_VALUES:
            return False
        if name == "null":
            return None
        raise ExpressionEvaluationError(f"unknown name: {name}")

    @staticmethod
    def _evaluate_compare(left: Any, right: Any, operator: ast.cmpop) -> bool:
        if isinstance(operator, ast.Eq):
            return left == right  # type: ignore[no-any-return]
        if isinstance(operator, ast.NotEq):
            return left != right  # type: ignore[no-any-return]
        if isinstance(operator, ast.In):
            return left in ExpressionEvaluator._ensure_iterable(right)
        if isinstance(operator, ast.NotIn):
            return left not in ExpressionEvaluator._ensure_iterable(right)
        if isinstance(operator, ast.Gt):
            return left > right  # type: ignore[no-any-return]
        if isinstance(operator, ast.GtE):
            return left >= right  # type: ignore[no-any-return]
        if isinstance(operator, ast.Lt):
            return left < right  # type: ignore[no-any-return]
        if isinstance(operator, ast.LtE):
            return left <= right  # type: ignore[no-any-return]
        raise ExpressionEvaluationError(f"unsupported comparison operator: {operator}")

    @staticmethod
    def _ensure_iterable(value: Any) -> Iterable[Any]:
        if isinstance(value, Mapping):
            return cast(Iterable[Any], value.keys())
        if isinstance(value, (set, frozenset)):
            return cast(Iterable[Any], value)
        if isinstance(value, (str, bytes, bytearray)):
            return cast(Iterable[Any], value)
        if isinstance(value, Sequence):
            return cast(Iterable[Any], value)
        raise ExpressionEvaluationError("membership test requires an iterable")
