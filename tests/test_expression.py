"""
GitHub Actions Simulator - Expression テスト
GitHub Actions式評価機能のテストケース
"""

import pytest

from services.actions.expression import ExpressionEvaluator, ExpressionEvaluationError


class TestExpressionEvaluator:
    """ExpressionEvaluatorのテストクラス"""

    @pytest.fixture
    def evaluator(self):
        """ExpressionEvaluatorインスタンスを作成"""
        return ExpressionEvaluator()

    @pytest.fixture
    def evaluator_with_functions(self):
        """関数付きExpressionEvaluatorインスタンスを作成"""
        functions = {
            "contains": lambda haystack, needle: needle in haystack,
            "startsWith": lambda string, prefix: string.startswith(prefix),
            "endsWith": lambda string, suffix: string.endswith(suffix),
        }
        return ExpressionEvaluator(functions=functions)

    @pytest.fixture
    def sample_context(self):
        """サンプルコンテキストを作成"""
        return {
            "github": {
                "ref": "refs/heads/main",
                "event_name": "push",
                "actor": "test-user",
                "repository": "test/repo",
            },
            "env": {"NODE_ENV": "production", "DEBUG": "false"},
            "matrix": {"os": "ubuntu-latest", "node": "18"},
            "runner": {"os": "Linux"},
        }

    def test_init_default(self):
        """デフォルト初期化テスト"""
        evaluator = ExpressionEvaluator()
        assert evaluator._functions == {}

    def test_init_with_functions(self):
        """関数付き初期化テスト"""
        functions = {"test_func": lambda x: x}
        evaluator = ExpressionEvaluator(functions=functions)
        assert "test_func" in evaluator._functions

    def test_evaluate_empty_expression(self, evaluator, sample_context):
        """空の式評価テスト"""
        assert evaluator.evaluate("", sample_context) is True
        assert evaluator.evaluate("   ", sample_context) is True
        assert evaluator.evaluate(None, sample_context) is True

    def test_evaluate_template_wrapper(self, evaluator, sample_context):
        """テンプレートラッパー処理テスト"""
        # テンプレートラッパーあり
        result = evaluator.evaluate("${{ true }}", sample_context)
        assert result is True

        # テンプレートラッパーなし
        result = evaluator.evaluate("true", sample_context)
        assert result is True

    def test_evaluate_boolean_literals(self, evaluator, sample_context):
        """ブール値リテラル評価テスト"""
        # True値
        assert evaluator.evaluate("true", sample_context) is True
        assert evaluator.evaluate("True", sample_context) is True

        # False値
        assert evaluator.evaluate("false", sample_context) is False
        assert evaluator.evaluate("False", sample_context) is False

    def test_evaluate_string_literals(self, evaluator, sample_context):
        """文字列リテラル評価テスト"""
        assert evaluator.evaluate("'hello'", sample_context) is True
        assert evaluator.evaluate("''", sample_context) is False
        assert evaluator.evaluate("'false'", sample_context) is True  # 文字列なのでTrue

    def test_evaluate_number_literals(self, evaluator, sample_context):
        """数値リテラル評価テスト"""
        assert evaluator.evaluate("1", sample_context) is True
        assert evaluator.evaluate("0", sample_context) is False
        assert evaluator.evaluate("-1", sample_context) is True
        assert evaluator.evaluate("3.14", sample_context) is True

    def test_evaluate_context_access(self, evaluator, sample_context):
        """コンテキストアクセス評価テスト"""
        # 単純なアクセス
        assert evaluator.evaluate("github", sample_context) is True

        # ネストしたアクセス
        assert evaluator.evaluate("github.ref", sample_context) is True
        assert evaluator.evaluate("env.NODE_ENV", sample_context) is True

    def test_evaluate_comparison_operators(self, evaluator, sample_context):
        """比較演算子評価テスト"""
        # 等価比較
        assert evaluator.evaluate("github.event_name == 'push'", sample_context) is True
        assert (
            evaluator.evaluate("github.event_name == 'pull_request'", sample_context)
            is False
        )

        # 不等価比較
        assert (
            evaluator.evaluate("github.event_name != 'pull_request'", sample_context)
            is True
        )
        assert (
            evaluator.evaluate("github.event_name != 'push'", sample_context) is False
        )

    def test_evaluate_logical_operators(self, evaluator, sample_context):
        """論理演算子評価テスト"""
        # AND演算子
        assert (
            evaluator.evaluate(
                "github.event_name == 'push' and github.ref == 'refs/heads/main'",
                sample_context,
            )
            is True
        )
        assert (
            evaluator.evaluate(
                "github.event_name == 'push' and github.ref == 'refs/heads/develop'",
                sample_context,
            )
            is False
        )

        # OR演算子
        assert (
            evaluator.evaluate(
                "github.event_name == 'push' or github.event_name == 'pull_request'",
                sample_context,
            )
            is True
        )
        assert (
            evaluator.evaluate(
                "github.event_name == 'schedule' or github.event_name == 'workflow_dispatch'",
                sample_context,
            )
            is False
        )

        # NOT演算子
        assert (
            evaluator.evaluate(
                "not github.event_name == 'pull_request'", sample_context
            )
            is True
        )
        assert (
            evaluator.evaluate("not github.event_name == 'push'", sample_context)
            is False
        )

    def test_evaluate_membership_operators(self, evaluator, sample_context):
        """メンバーシップ演算子評価テスト"""
        # in演算子
        assert evaluator.evaluate("'main' in github.ref", sample_context) is True
        assert evaluator.evaluate("'develop' in github.ref", sample_context) is False

    def test_evaluate_with_functions(self, evaluator_with_functions, sample_context):
        """関数付き評価テスト"""
        # contains関数
        assert (
            evaluator_with_functions.evaluate(
                "contains(github.ref, 'main')", sample_context
            )
            is True
        )
        assert (
            evaluator_with_functions.evaluate(
                "contains(github.ref, 'develop')", sample_context
            )
            is False
        )

        # startsWith関数
        assert (
            evaluator_with_functions.evaluate(
                "startsWith(github.ref, 'refs/heads/')", sample_context
            )
            is True
        )
        assert (
            evaluator_with_functions.evaluate(
                "startsWith(github.ref, 'refs/tags/')", sample_context
            )
            is False
        )

        # endsWith関数
        assert (
            evaluator_with_functions.evaluate(
                "endsWith(github.ref, 'main')", sample_context
            )
            is True
        )
        assert (
            evaluator_with_functions.evaluate(
                "endsWith(github.ref, 'develop')", sample_context
            )
            is False
        )

    def test_evaluate_complex_expressions(
        self, evaluator_with_functions, sample_context
    ):
        """複雑な式評価テスト"""
        # 複数条件の組み合わせ
        complex_expr = "github.event_name == 'push' and contains(github.ref, 'main') and env.NODE_ENV == 'production'"
        assert evaluator_with_functions.evaluate(complex_expr, sample_context) is True

        # 括弧を使った優先順位
        priority_expr = "(github.event_name == 'push' or github.event_name == 'pull_request') and contains(github.ref, 'main')"
        assert evaluator_with_functions.evaluate(priority_expr, sample_context) is True

    def test_evaluate_syntax_error(self, evaluator, sample_context):
        """構文エラー処理テスト"""
        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("github.ref ==", sample_context)

        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("github.ref == 'main' and", sample_context)

    def test_evaluate_undefined_variable(self, evaluator, sample_context):
        """未定義変数処理テスト"""
        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("undefined_variable", sample_context)

        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("github.undefined_field", sample_context)

    def test_evaluate_undefined_function(self, evaluator, sample_context):
        """未定義関数処理テスト"""
        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("undefined_function(github.ref)", sample_context)

    def test_evaluate_type_error(self, evaluator, sample_context):
        """型エラー処理テスト"""
        # 文字列に対する不正な操作
        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("github.ref + 1", sample_context)

    def test_true_false_values_constants(self):
        """True/False値定数テスト"""
        evaluator = ExpressionEvaluator()

        assert "true" in evaluator._TRUE_VALUES
        assert "True" in evaluator._TRUE_VALUES
        assert "false" in evaluator._FALSE_VALUES
        assert "False" in evaluator._FALSE_VALUES

    def test_evaluate_nested_context_access(self, evaluator, sample_context):
        """ネストしたコンテキストアクセステスト"""
        # 深いネスト
        deep_context = {"level1": {"level2": {"level3": {"value": "deep_value"}}}}

        assert (
            evaluator.evaluate(
                "level1.level2.level3.value == 'deep_value'", deep_context
            )
            is True
        )
        assert (
            evaluator.evaluate(
                "level1.level2.level3.value == 'other_value'", deep_context
            )
            is False
        )

    def test_evaluate_array_access(self, evaluator):
        """配列アクセステスト"""
        array_context = {
            "items": ["item1", "item2", "item3"],
            "matrix": {
                "include": [
                    {"os": "ubuntu", "version": "18"},
                    {"os": "windows", "version": "20"},
                ]
            },
        }

        # 配列の存在確認
        assert evaluator.evaluate("items", array_context) is True
        assert evaluator.evaluate("matrix.include", array_context) is True

    def test_evaluate_edge_cases(self, evaluator):
        """エッジケーステスト"""
        edge_context = {
            "empty_string": "",
            "zero": 0,
            "null_value": None,
            "empty_list": [],
            "empty_dict": {},
        }

        # 空の値の評価
        assert evaluator.evaluate("empty_string", edge_context) is False
        assert evaluator.evaluate("zero", edge_context) is False
        assert evaluator.evaluate("null_value", edge_context) is False
        assert evaluator.evaluate("empty_list", edge_context) is False
        assert evaluator.evaluate("empty_dict", edge_context) is False

    def test_evaluate_whitespace_handling(self, evaluator, sample_context):
        """空白文字処理テスト"""
        # 式の前後の空白
        assert (
            evaluator.evaluate("  github.event_name == 'push'  ", sample_context)
            is True
        )

        # テンプレートラッパー内の空白
        assert (
            evaluator.evaluate("${{  github.event_name == 'push'  }}", sample_context)
            is True
        )

        # 空のテンプレートラッパー
        assert evaluator.evaluate("${{  }}", sample_context) is True

    def test_evaluate_boolean_conversion(self, evaluator):
        """ブール値変換テスト"""
        conversion_context = {
            "truthy_string": "hello",
            "falsy_string": "",
            "positive_number": 42,
            "zero_number": 0,
            "negative_number": -1,
            "non_empty_list": [1, 2, 3],
            "empty_list": [],
        }

        # 真偽値への変換
        assert evaluator.evaluate("truthy_string", conversion_context) is True
        assert evaluator.evaluate("falsy_string", conversion_context) is False
        assert evaluator.evaluate("positive_number", conversion_context) is True
        assert evaluator.evaluate("zero_number", conversion_context) is False
        assert evaluator.evaluate("negative_number", conversion_context) is True
        assert evaluator.evaluate("non_empty_list", conversion_context) is True
        assert evaluator.evaluate("empty_list", conversion_context) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
