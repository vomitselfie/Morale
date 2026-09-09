"""Native batch conversion workflow."""
import json
from collections import Counter
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QComboBox, QProgressBar, QPlainTextEdit, QFileDialog, QMessageBox)

from .batch import ConversionQueue
from .formats import file_filters, EXPORT_FORMATS


class BatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch convert embroidery designs")
        self.resize(720, 620)
        self.queue = ConversionQueue(self)
        self.sources = []
        self.closing = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Convert copies into a chosen folder. Existing files and originals are never replaced."))
        self.files = QListWidget()
        self.files.setAccessibleName("Conversion source files")
        layout.addWidget(self.files)
        row = QHBoxLayout()
        self.add = QPushButton("Add files…")
        self.add.clicked.connect(self.add_files)
        self.clear = QPushButton("Clear list")
        self.clear.clicked.connect(self.clear_files)
        row.addWidget(self.add)
        row.addWidget(self.clear)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setPlaceholderText("Choose an output folder")
        self.output.setAccessibleName("Conversion output folder")
        self.browse = QPushButton("Choose folder…")
        self.browse.clicked.connect(self.choose_output)
        row.addWidget(self.output)
        row.addWidget(self.browse)
        layout.addLayout(row)
        self.format = QComboBox()
        self.format.setAccessibleName("Conversion format")
        self.format.addItem("PES version 6 · RGB colors", ("pes", 6))
        self.format.addItem("PES version 1 · legacy palette", ("pes", 1))
        for ext in sorted(EXPORT_FORMATS - {".pes"}):
            self.format.addItem(ext[1:].upper(), (ext[1:], 6))
        layout.addWidget(self.format)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setAccessibleName("Per-file conversion results")
        layout.addWidget(self.log)
        self.summary = QLabel("Ready · Each worker has a 60-second limit.")
        layout.addWidget(self.summary)
        row = QHBoxLayout()
        self.start_button = QPushButton("Convert files")
        self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("Cancel queue")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.queue.cancel)
        self.report_button = QPushButton("Save report…")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.save_report)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        for widget in (self.start_button, self.cancel_button, self.report_button, self.close_button):
            row.addWidget(widget)
        layout.addLayout(row)
        self.queue.result.connect(self.show_result)
        self.queue.progress.connect(self.update_progress)
        self.queue.finished.connect(self.finished_queue)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select embroidery files", "", file_filters())
        for path in paths:
            if path not in self.sources and len(self.sources) < 500:
                self.sources.append(path)
                self.files.addItem(path)

    def clear_files(self):
        self.sources.clear()
        self.files.clear()

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder", self.output.text())
        if folder:
            self.output.setText(folder)

    def start(self):
        try:
            extension, version = self.format.currentData()
            self.queue.start(self.sources, self.output.text(), extension, version)
        except ValueError as exc:
            QMessageBox.warning(self, "Batch conversion", str(exc))
            return
        self.log.clear()
        self.set_running(True)

    def set_running(self, running):
        for widget in (self.add, self.clear, self.output, self.browse, self.format, self.start_button):
            widget.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.report_button.setEnabled(not running and bool(self.queue.results))

    def show_result(self, row):
        message = f"{row['status'].upper()} · {row['source']} → {row['target']}"
        if row["message"]:
            message += "\n  " + row["message"]
        for note in row["notes"]:
            message += "\n  " + note
        self.log.appendPlainText(message + "\n")

    def update_progress(self, done, total):
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.summary.setText(f"{done} / {total} files processed")

    def finished_queue(self):
        self.set_running(False)
        counts = Counter(row["status"] for row in self.queue.results)
        self.summary.setText(" · ".join(f"{count} {status}" for status, count in sorted(counts.items())))
        if self.closing:
            super().reject()

    def save_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save conversion report", "conversion-report.json", "JSON report (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps(self.queue.results, indent=2) + "\n", encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Could not save report", str(exc))

    def reject(self):
        if self.queue.running:
            self.closing = True
            self.queue.cancel()
        else:
            super().reject()

    def closeEvent(self, event):
        if self.queue.running:
            event.ignore()
            self.reject()
        else:
            event.accept()
