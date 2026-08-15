from __future__ import annotations

import customtkinter as ctk

from expandr.models import Library
from expandr.parser import FormField, evaluate


class FillInDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        title: str,
        fields: list[FormField],
        content: str,
        library: Library,
        clipboard: str,
    ):
        super().__init__(master)
        self.title(title or "Expandr")
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.result: dict[str, str] | None = None
        self.widgets: dict[str, object] = {}
        self._content = content
        self._library = library
        self._clipboard = clipboard

        height = min(720, 220 + 72 * max(1, len(fields)))
        self.geometry(f"460x{height}")
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        for field in fields:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(row, text=field.name, anchor="w").pack(fill="x")
            if field.kind == "formparagraph":
                box = ctk.CTkTextbox(row, height=72)
                box.insert("1.0", field.default)
                box.pack(fill="x")
                box.bind("<KeyRelease>", lambda _e: self._refresh_preview())
                self.widgets[field.name] = ("text", box)
            elif field.kind == "formmenu":
                box = ctk.CTkComboBox(
                    row,
                    values=field.options or [field.default or ""],
                    command=lambda _v: self._refresh_preview(),
                )
                box.set(field.default or (field.options[0] if field.options else ""))
                box.pack(fill="x")
                self.widgets[field.name] = ("entry", box)
            elif field.kind == "formtoggle":
                on = field.default.casefold() in {"yes", "true", "1", "on"}
                var = ctk.BooleanVar(value=on)
                box = ctk.CTkSwitch(row, text="Include", variable=var, command=self._refresh_preview)
                box.pack(anchor="w")
                self.widgets[field.name] = ("toggle", var)
            else:
                box = ctk.CTkEntry(row)
                box.insert(0, field.default)
                box.pack(fill="x")
                box.bind("<KeyRelease>", lambda _e: self._refresh_preview())
                box.bind("<Return>", lambda _e: self._ok())
                self.widgets[field.name] = ("entry", box)

        ctk.CTkLabel(frame, text="Preview", anchor="w", text_color="gray").pack(fill="x", pady=(8, 4))
        self.preview = ctk.CTkTextbox(frame, height=120, state="disabled")
        self.preview.pack(fill="both", expand=True)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(buttons, text="Insert", width=100, command=self._ok).pack(side="right")
        ctk.CTkButton(buttons, text="Cancel", width=100, fg_color="gray", command=self._cancel).pack(
            side="right", padx=(0, 8)
        )
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._focus_first)
        self._refresh_preview()

    def _focus_first(self) -> None:
        self.lift()
        self.focus_force()
        for kind, widget in self.widgets.values():
            if kind in {"entry", "text"}:
                widget.focus_set()
                break

    def _collect(self) -> dict[str, str]:
        answers: dict[str, str] = {}
        for name, (kind, widget) in self.widgets.items():
            if kind == "text":
                answers[name] = widget.get("1.0", "end-1c")
            elif kind == "toggle":
                answers[name] = "yes" if widget.get() else "no"
            else:
                answers[name] = widget.get()
        return answers

    def _refresh_preview(self) -> None:
        result = evaluate(self._content, self._collect(), self._library, self._clipboard)
        text = result.text
        if len(text) > 4000:
            text = text[:4000] + "\n…"
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _ok(self) -> None:
        self.result = self._collect()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_fields(
    master,
    title: str,
    fields: list[FormField],
    content: str,
    library: Library,
    clipboard: str,
) -> dict[str, str] | None:
    dialog = FillInDialog(master, title, fields, content, library, clipboard)
    master.wait_window(dialog)
    return dialog.result
