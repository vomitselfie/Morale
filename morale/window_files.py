"""Opening, saving, exporting and recovering designs."""
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QProgressDialog
from .model import Project, demo_project, satin_sample
from .hoop_dialog import HoopDialog as MultiHoopDialog
from .threads import write_chart
from .reference import decode_reference
from .templates import TemplateDialog, export_template
from .comparison import ComparisonDialog
from .library import LibraryDialog
from .batch_dialog import BatchDialog
from .engine import generate, preflight
from .formats import (export_machine, file_filters, export_notes, export_summary, IMPORT_FORMATS,
    EXPORT_FORMATS)


class FileWorkflowsMixin:
    def multihoop_dialog(self):
        dialog = MultiHoopDialog(self.project, self)
        try:
            dialog.exec()
        finally:
            dialog.cleanup()
            dialog.deleteLater()

    def compare_machine_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Compare machine file with current design","",file_filters())
        if path:
            try:
                dialog=ComparisonDialog(self.project,path,self)
                try:
                    dialog.exec()
                finally:
                    dialog.deleteLater()
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def placement_template(self):
        if not self.preview_available():
            return
        dialog = TemplateDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export placement template", "placement.pdf", "PDF document (*.pdf)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".pdf"
        try:
            plan = export_template(self.project,path,dialog.paper.currentText(),dialog.stitches.isChecked())
            self.statusBar().showMessage(f"Exported {plan.rows*plan.columns} placement pages. Print at Actual size and verify the 50 mm ruler.")
        except (OSError,ValueError) as exc:
            self.error(str(exc))

    def new(self):
        if self.confirm_discard():
            self.replace_project(Project())

    def load_demo(self):
        if self.confirm_discard():
            self.replace_project(demo_project())

    def load_satin_sample(self):
        if self.confirm_discard():
            self.replace_project(satin_sample())

    def open(self):
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open design", "", "Morale project (*.morale);;" + file_filters())
        if path:
            self.open_path(path)

    def browse_designs(self):
        dialog=LibraryDialog(self,getattr(self,"library_folder",str(self.file_path.parent) if self.file_path else None))
        try:
            accepted=dialog.exec()==dialog.DialogCode.Accepted
            self.library_folder=dialog.folder
            if accepted and dialog.selected_path and self.confirm_discard():
                self.open_path(dialog.selected_path)
        finally:
            dialog.runner.cancel()
            dialog.deleteLater()

    def open_path(self, path, merge=False):
        """Open (or, with ``merge``, import) a design; decoding runs in a worker when available."""
        if self.open_runner is not None:
            self.start_opening(path, merge)
            return
        from .open_worker import decode
        try:
            project, notes = decode(path)
        except (ValueError, OSError) as exc:
            self.error(f"Could not {'import this design' if merge else 'open this project'}.\n{exc}")
            return
        self.finish_open(path, project, notes, merge)

    def start_opening(self, path, merge):
        self.cancel_opening()
        self.opening = (str(Path(path).resolve()), merge)
        self.open_progress = QProgressDialog(f"{'Importing' if merge else 'Opening'} {Path(path).name}…", "Cancel", 0, 0, self)
        self.open_progress.setWindowTitle("Morale")
        self.open_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.open_progress.setMinimumDuration(400)
        self.open_progress.canceled.connect(self.cancel_opening)
        self.open_runner.load(path)

    def close_open_progress(self):
        if self.open_progress is not None:
            self.open_progress.canceled.disconnect(self.cancel_opening)
            self.open_progress.close()
            self.open_progress.deleteLater()
            self.open_progress = None

    def cancel_opening(self):
        if self.opening is not None:
            self.open_runner.cancel()
            self.opening = None
            self.statusBar().showMessage("Opening cancelled.")
        self.close_open_progress()

    def opened(self, path, result, _image):
        if self.opening is None or self.opening[0] != path:
            return
        _, merge = self.opening
        self.opening = None
        self.close_open_progress()
        project, notes = result
        self.finish_open(path, project, notes, merge)

    def open_failed(self, path, message):
        if self.opening is None or self.opening[0] != path:
            return
        merge = self.opening[1]
        self.opening = None
        self.close_open_progress()
        self.error(f"Could not {'import this design' if merge else 'open this project'}.\n{message}")

    def finish_open(self, path, project, notes, merge):
        try:
            if merge:
                if not project.objects:
                    raise ValueError("The design contains no stitches.")
                if len(self.project.objects) + len(project.objects) > 500:
                    raise ValueError("Combined design would exceed 500 objects.")
                combined = deepcopy(self.project)
                combined.objects.extend(project.objects)
                generate(combined)  # Check the combined command budget before mutation.
                self.selected_id = project.objects[0].id
                self.commit(lambda: self.project.objects.extend(project.objects))
                QMessageBox.information(self, "Design imported", "\n\n".join(notes))
            elif Path(path).suffix.lower() == ".morale":
                self.replace_project(project, Path(path))
            else:
                self.replace_project(project)
                self.saved = ""
                self.update_title()
                QMessageBox.information(self, "Design imported", "\n\n".join(notes))
        except (ValueError, OSError) as exc:
            self.error(f"Could not {'import this design' if merge else 'open this project'}.\n{exc}")

    def import_design(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import machine design", "", file_filters())
        if path:
            self.open_path(path, merge=True)

    def batch_convert(self):
        self.reset_playback()
        BatchDialog(self).exec()

    def compatibility(self):
        QMessageBox.information(self, "Format compatibility", f"Readers available: {len(IMPORT_FORMATS)}\n" + ", ".join(sorted(IMPORT_FORMATS)) + f"\n\nMachine writers: {len(EXPORT_FORMATS)}\n" + ", ".join(sorted(EXPORT_FORMATS)) + "\n\nReader availability is not physical machine certification. Synthetic round-trip tests cover supported writers; externally produced files are still needed to validate reader-only formats.\n\nImported designs preserve stitches, jumps, trims, stops and color changes. Needle events are converted to color blocks with a notice. Unsupported specialist commands are rejected. Proprietary editable formats such as EMB and ART are not supported.")

    def save(self, save_as=False):
        path = self.file_path
        if not path or save_as:
            name, _ = QFileDialog.getSaveFileName(self, "Save editable project", str(path or "design.morale"), "Morale project (*.morale)")
            if not name:
                return False
            path = Path(name)
            if path.suffix.lower() != ".morale":
                path = path.with_suffix(".morale")
                if not self.confirm_replacement(path):
                    return False
        try:
            self.project.save(path)
            self.file_path = path
            self.saved = self.project.dumps()
            self.checkpoint()
            self.update_title()
            self.statusBar().showMessage(f"Project saved · {path}")
            return True
        except (OSError, ValueError) as exc:
            self.error(f"Could not save your project.\n{exc}")
            return False

    def export(self):
        if not self.preview_available():
            return
        issues = [self.generation_error] if self.generation_error else preflight(self.project, self.blocks)
        if issues:
            self.error("\n".join(issues))
            return
        name, selected_filter = QFileDialog.getSaveFileName(self, "Export machine stitches", "design.pes", file_filters(export=True))
        if not name:
            return
        if not self.preview_available():
            return
        path = Path(name)
        extension = selected_filter.split("*.")[-1].split(")")[0]
        if path.suffix.lower() != f".{extension}":
            path = path.with_suffix(f".{extension}")
            if not self.confirm_replacement(path):
                return
        try:
            result=export_machine(self.project, path, self.blocks, pes_version=1 if "PES v1" in selected_filter else 6)
            self.statusBar().showMessage(f"Exported {path.name} · {result['prepared_stitches']:,} stitches prepared · {result['subdivision_added_stitches']:,} positions added")
            notes = [export_summary(result),*export_notes(path.suffix.lower(), 1 if "PES v1" in selected_filter else 6)]
            QMessageBox.information(self, "Stitches exported", f"Saved {path.name}.\n\n" + "\n\n".join(notes) + "\n\nTest on scrap fabric. Keep your editable .morale project.")
        except Exception as exc:
            self.error(f"Could not export the machine file.\n{exc}")

    def confirm_replacement(self, path):
        # A suffix correction can change the target after the native dialog's
        # overwrite check. Confirm that actual destination if it already exists.
        return not path.exists() or QMessageBox.question(
            self, "Replace existing file?", f"{path.name} already exists. Replace it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def thread_chart(self):
        if not self.preview_available():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export thread sequence", "threads.csv", "Thread chart (*.csv)")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    write_chart(self.project, self.blocks, f)
                self.statusBar().showMessage(f"Thread chart saved · {path}")
            except OSError as exc:
                self.error(str(exc))

    def checkpoint(self):
        if not self.recovery:
            return
        try:
            current = self.project.dumps()
            if current == self.saved:
                self.recovery.clear()
                self.recovery_last = None
            elif current != self.recovery_last:
                self.recovery.write(self.project, self.file_path)
                self.recovery_last = current
            self.recovery_error = ""
        except (OSError, ValueError) as exc:
            self.recovery_error = str(exc)
            self.statusBar().showMessage(f"Recovery snapshot could not be saved: {exc}")

    def restore_recovery(self, path):
        if not self.recovery:
            raise ValueError("Recovery storage is unavailable.")
        project = self.recovery.load(path)
        decode_reference(project.reference)
        # Secure the recovered copy before consuming its source. Recovered work
        # always saves to a newly chosen path, never silently over the old file.
        self.recovery.write(project)
        self.recovery_last = project.dumps()
        self.replace_project(project, recovered=True)
        if self.recovery_error:
            raise OSError(self.recovery_error)
        self.recovery.discard(path)
        self.update_title()

    def recover_session(self, quiet=False):
        if not self.recovery:
            if not quiet:
                self.error("Recovery storage is unavailable. " + self.recovery_error)
            return
        try:
            entries = self.recovery.available()
        except OSError as exc:
            self.recovery_error = str(exc)
            self.statusBar().showMessage(f"Recovery copies could not be read: {exc}")
            return
        if not entries:
            if not quiet:
                self.statusBar().showMessage("No interrupted sessions found.")
            return
        choices = [f"{i + 1}. {entry['name']} — {entry['updated']}" + (" (damaged)" if entry["error"] else "") for i, entry in enumerate(entries)]
        choice, accepted = QInputDialog.getItem(self, "Recover interrupted session", "Choose a recovery copy. Cancel keeps all copies for later.", choices, 0, False)
        if not accepted:
            return
        entry = entries[choices.index(choice)]
        action = QMessageBox.question(self, "Recovery copy", "Restore this design as an unsaved project? Choose No to discard this recovery copy, or Cancel to keep it.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        try:
            if action == QMessageBox.StandardButton.Yes and self.confirm_discard():
                self.restore_recovery(entry["path"])
            elif action == QMessageBox.StandardButton.No:
                self.recovery.discard(entry["path"])
        except (OSError, ValueError) as exc:
            self.error(str(exc))
