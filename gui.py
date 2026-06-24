import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from summarizer import SummarizerError, make_default_output_path, summarize_file


class MeetingSummarizerApp:
    """Small tkinter GUI for the meeting summarizer."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("議事録要約AIツール")
        self.root.geometry("820x640")

        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="テキストファイルを選択してください。")

        self._build_widgets()

    def _build_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(main_frame, text="入力ファイル", padding=10)
        file_frame.pack(fill=tk.X)

        input_entry = ttk.Entry(file_frame, textvariable=self.input_path_var)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        select_button = ttk.Button(
            file_frame,
            text="選択",
            command=self.select_input_file,
        )
        select_button.pack(side=tk.LEFT, padx=(8, 0))

        output_frame = ttk.LabelFrame(main_frame, text="保存先ファイル", padding=10)
        output_frame.pack(fill=tk.X, pady=(12, 0))

        output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        output_button = ttk.Button(
            output_frame,
            text="保存先を選択",
            command=self.select_output_file,
        )
        output_button.pack(side=tk.LEFT, padx=(8, 0))

        self.summary_button = ttk.Button(
            main_frame,
            text="要約開始",
            command=self.start_summary,
        )
        self.summary_button.pack(anchor=tk.W, pady=(12, 0))

        result_frame = ttk.LabelFrame(main_frame, text="要約結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            height=20,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            foreground="#333333",
        )
        status_label.pack(anchor=tk.W, pady=(8, 0))

    def select_input_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="議事録テキストファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )

        if not file_path:
            return

        self.input_path_var.set(file_path)

        if not self.output_path_var.get().strip():
            self.output_path_var.set(str(make_default_output_path(file_path)))

        self.status_var.set("ファイルを選択しました。")

    def select_output_file(self) -> None:
        initial_file = "summary.txt"
        input_path = self.input_path_var.get().strip()

        if input_path:
            initial_file = make_default_output_path(input_path).name

        file_path = filedialog.asksaveasfilename(
            title="保存先ファイルを選択",
            defaultextension=".txt",
            initialfile=initial_file,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )

        if file_path:
            self.output_path_var.set(file_path)

    def start_summary(self) -> None:
        input_path = self.input_path_var.get().strip()

        if not input_path:
            messagebox.showerror("エラー", "入力ファイルを選択してください。")
            self.status_var.set("エラー: 入力ファイルが選択されていません。")
            return

        output_path = self.output_path_var.get().strip() or None

        self.summary_button.config(state=tk.DISABLED)
        self.status_var.set("要約中...")
        self.result_text.delete("1.0", tk.END)

        thread = threading.Thread(
            target=self._run_summary_in_thread,
            args=(input_path, output_path),
            daemon=True,
        )
        thread.start()

    def _run_summary_in_thread(self, input_path: str, output_path: str | None) -> None:
        try:
            result = summarize_file(
                input_path=input_path,
                output_path=output_path,
                warning_callback=self._show_warning_from_thread,
            )
        except SummarizerError as error:
            self.root.after(0, self._show_error, str(error))
            return

        self.root.after(0, self._show_success, result.summary_text, result.output_path)

    def _show_warning_from_thread(self, message: str) -> None:
        self.root.after(0, self.status_var.set, message)

    def _show_error(self, message: str) -> None:
        self.summary_button.config(state=tk.NORMAL)
        self.status_var.set(f"エラー: {message}")
        messagebox.showerror("エラー", message)

    def _show_success(self, summary_text: str, output_path: Path) -> None:
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, summary_text)
        self.summary_button.config(state=tk.NORMAL)
        self.status_var.set(f"保存が完了しました: {output_path}")
        messagebox.showinfo("完了", f"要約を保存しました:\n{output_path}")


def main() -> None:
    root = tk.Tk()
    app = MeetingSummarizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
