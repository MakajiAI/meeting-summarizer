import argparse

from summarizer import SummarizerError, summarize_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UTF-8形式のテキスト議事録をGoogle Gemini APIで要約します。"
    )
    parser.add_argument("file_path", help="要約する議事録テキストファイルのパス")
    parser.add_argument(
        "--output",
        help="要約結果の保存先ファイルパス。未指定の場合は summary_元ファイル名.txt に保存します。",
    )
    args = parser.parse_args()

    try:
        result = summarize_file(
            input_path=args.file_path,
            output_path=args.output,
            warning_callback=print,
        )
    except SummarizerError as error:
        print(f"エラー: {error}")
        raise SystemExit(1)

    print(result.summary_text)
    print()
    print(f"保存が完了しました: {result.output_path}")


if __name__ == "__main__":
    main()
