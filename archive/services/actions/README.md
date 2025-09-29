# アーカイブされたファイル

このディレクトリには、プロジェクトの進化過程で使用されなくなったファイルが保存されています。

## act_wrapper.py

**移動日**: 2025-09-29
**理由**: EnhancedActWrapperに機能が統合されたため

### 移動の経緯

1. `ActWrapper`クラスは`EnhancedActWrapper`の基底クラスとして使用されていました
2. 機能の重複と保守性の向上のため、`EnhancedActWrapper`に統合されました
3. 今後の混乱を避けるため、元の`act_wrapper.py`をアーカイブに移動しました

### 影響を受けたファイル

- `tests/test_act_wrapper_with_tracer.py`: `EnhancedActWrapper`を使用するよう修正
- `services/actions/enhanced_act_wrapper.py`: 継承関係を削除し、基底機能を統合

### 参照

統合された機能は `services/actions/enhanced_act_wrapper.py` で利用できます。
