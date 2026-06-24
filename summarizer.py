import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MODEL_NAME = "gemini-2.5-flash"
LONG_TEXT_WARNING_THRESHOLD = 20_000


class SummarizerError(Exception):
    """User-facing error for this application."""


@dataclass
class SummaryResult:
    summary_text: str
    output_path: Path
    warning_message: str | None = None


def load_api_key() -> str:
    """Load GEMINI_API_KEY from .env in this project folder."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError as error:
        raise SummarizerError(
            "python-dotenv がインストールされていません。"
            " pip install -r requirements.txt を実行してください。"
        ) from error

    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        raise SummarizerError(
            ".env が見つかりません。"
            " .env.example をコピーして .env を作成してください。"
        )

    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise SummarizerError(
            "GEMINI_API_KEY が設定されていません。"
            " .env に GEMINI_API_KEY=your_api_key_here の形式で設定してください。"
        )

    return api_key


def read_text_file(file_path: str | Path) -> str:
    """Read a UTF-8 text file. utf-8-sig also handles files with BOM."""
    path = Path(file_path)

    if not path.exists():
        raise SummarizerError(f"入力ファイルが見つかりません: {path}")

    if not path.is_file():
        raise SummarizerError(f"指定されたパスはファイルではありません: {path}")

    try:
        meeting_text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise SummarizerError(
            f"入力ファイルをUTF-8として読み込めませんでした: {path}"
        ) from error

    if not meeting_text.strip():
        raise SummarizerError(f"入力ファイルが空です: {path}")

    return meeting_text


def get_long_text_warning(meeting_text: str) -> str | None:
    """Return a warning message when the input text is very long."""
    if len(meeting_text) >= LONG_TEXT_WARNING_THRESHOLD:
        return "警告: 入力テキストが長いため、処理に時間がかかる可能性があります。"

    return None


def build_prompt(
    meeting_text: str,
    input_file_name: str,
    processed_at: str,
    model_name: str = MODEL_NAME,
) -> str:
    """Build the prompt sent to Gemini."""
    return f"""以下の会議議事録を要約してください。

出力は必ず日本語で、指定したMarkdown見出し名を変更しないでください。
入力テキストに書かれていない内容を推測で追加しないでください。

会議本文に「会議日時」が含まれている場合は、「今週金曜」「来週月曜」「翌週」「明日」などの相対的な期限を、可能な範囲で具体的な日付に変換してください。
例: 会議日時が2026年6月23日の場合、「今週金曜」は「2026年6月26日」、「来週月曜」は「2026年6月29日」とします。
ただし、確信できない場合は無理に推測せず、元の表現のままにしてください。

出力形式は必ず次のMarkdown形式にしてください。

# 会議要約

* 入力ファイル: {input_file_name}
* 処理日時: {processed_at}
* 使用モデル: {model_name}

## 会議の目的

1文で記載。

## 決定事項

* 箇条書きで3点以内。
* 明確な決定事項がない場合は「明確な決定事項はありません」と書く。

## 次のアクション

| 担当者  | 内容   | 期限 |
| ---- | ---- | -- |
| 担当者名 | 実施内容 | 期限 |

担当者や期限が不明な場合は「不明」と書く。

## 全体要約

200文字以内で記載。

# 重要制約

* 入力テキストに書かれていない内容を推測で追加しない。
* 担当者・期限・決定事項は、議事録内に根拠があるものだけを書く。
* 日本語で出力する。
* 見出し名は変更しない。

---

会議議事録:
{meeting_text}
"""


def summarize_with_gemini(prompt: str, api_key: str) -> str:
    """Call the Gemini API and return the summary text."""
    try:
        from google import genai
    except ModuleNotFoundError as error:
        raise SummarizerError(
            "google-genai がインストールされていません。"
            " pip install -r requirements.txt を実行してください。"
        ) from error

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
    except Exception as error:
        raise SummarizerError(f"Gemini APIの呼び出しに失敗しました: {error}") from error

    summary_text = response.text
    if not summary_text:
        raise SummarizerError("Gemini APIから要約結果を取得できませんでした。")

    return summary_text.strip()


def make_default_output_path(input_path: str | Path) -> Path:
    """Create the default summary file path next to the input file."""
    path = Path(input_path)
    return path.with_name(f"summary_{path.name}")


def save_summary(
    input_path: str | Path,
    summary_text: str,
    output_path: str | Path | None = None,
) -> Path:
    """Save the summary to the selected path or the default path."""
    if output_path:
        save_path = Path(output_path)
    else:
        save_path = make_default_output_path(input_path)

    try:
        save_path.write_text(summary_text, encoding="utf-8")
    except OSError as error:
        raise SummarizerError(f"ファイル保存に失敗しました: {save_path}") from error

    return save_path


def summarize_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    warning_callback=None,
) -> SummaryResult:
    """Run the full summarization flow used by both CLI and GUI."""
    meeting_text = read_text_file(input_path)
    warning_message = get_long_text_warning(meeting_text)

    if warning_message and warning_callback:
        warning_callback(warning_message)

    api_key = load_api_key()
    processed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = build_prompt(
        meeting_text=meeting_text,
        input_file_name=Path(input_path).name,
        processed_at=processed_at,
        model_name=MODEL_NAME,
    )
    summary_text = summarize_with_gemini(prompt, api_key)
    saved_path = save_summary(input_path, summary_text, output_path)

    return SummaryResult(
        summary_text=summary_text,
        output_path=saved_path,
        warning_message=warning_message,
    )
