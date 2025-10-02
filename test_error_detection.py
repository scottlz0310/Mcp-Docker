# テスト用: 意図的なエラー

def bad_function():
    # 末尾に空白がある
    x=1+2
    return x

def type_error(x: int) -> str:
    # 型エラー
    return x

# ファイル末尾に改行なし
