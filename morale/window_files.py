"""Opening, saving, exporting and recovering designs."""
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import (QFileDialog, QMessageBox, QInputDialog, QProgressDialog, QDialog, QVBoxLayout, QLabel,
    QListWidget, QDialogButtonBox)
from .model import Project, demo_project, satin_sample
from .hoop_dialog import HoopDialog as MultiHoopDialog
from .threads import save_chart
from .reference import decode_reference
from .templates import TemplateDialog, export_template
from .comparison import ComparisonDialog
from .library import LibraryDialog
from .batch_dialog import BatchDialog
from .engine import generate, preflight
from .formats import (export_machine, file_filters, export_notes, export_summary, IMPORT_FORMATS,
    EXPORT_FORMATS)


class DesignCheckDialog(QDialog):
    """Design check results; choosing an issue selects and shows its object."""

    SYMBOLS = {"error": "✕", "warning": "⚠", "info": "✓"}

    def __init__(self, issues, window):
        super().__init__(window)
        self.setWindowTitle("Check design")
        self.window, self.issues = window, issues
        layout = QVBoxLayout(self)
        errors = sum(i.severity == "error" for i in issues)
        warnings = sum(i.severity == "warning" for i in issues)
        summary = QLabel(f"{errors} problem{'s' if errors != 1 else ''} to fix before export · "
                         f"{warnings} thing{'s' if warnings != 1 else ''} to review. Limits marked provisional "
                         "are starting points until sew-out results confirm them. Nothing here changes your design.")
        summary.setWordWrap(True)
        layout.addWidget(summary)
        self.list = QListWidget()
        self.list.setAccessibleName("Design check results")
        self.list.setWordWrap(True)
        for issue in issues:
            self.list.addItem(f"{self.SYMBOLS[issue.severity]}  {issue.message}")
        self.list.currentRowChanged.connect(self.show_issue)
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, 420)

    def show_issue(self, row):
        if not 0 <= row < len(self.issues):
            return
        issue = self.issues[row]
        if issue.object_id and any(o.id == issue.object_id for o in self.window.project.objects):
            self.window.select(issue.object_id)
        if issue.position is not None:
            # Centre the canvas on the issue: screen = centre + pan + world * scale.
            canvas = self.window.canvas
            canvas.pan = QPointF(-issue.position[0] * canvas.scale, -issue.position[1] * canvas.scale)
            canvas.update()


class FileWorkflowsMixin:
    def check_design(self):
        if not self.preview_available():
            return
        from .design_check import check_design
        dialog = DesignCheckDialog(check_design(self.project, self.blocks), self)
        dialog.exec()


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

    def export_sewout_worksheet(self):
        if not self.preview_available():return
        path,_=QFileDialog.getSaveFileName(self,'Export sewout worksheet','sewout-worksheet.pdf','PDF document (*.pdf)')
        if not path:return
        if not Path(path).suffix:path+='.pdf'
        try:
            from .coupons import project_evaluation_pdf
            project_evaluation_pdf(self.project,path)
            self.statusBar().showMessage('Exported blank sewout worksheet with the current design settings.')
        except (OSError,ValueError) as exc:self.error(str(exc))

    def new(self):
        if self.confirm_discard():
            self.replace_project(Project())

    def load_demo(self):
        if self.confirm_discard():
            self.replace_project(demo_project())

    def load_satin_sample(self):
        if self.confirm_discard():
            self.replace_project(satin_sample())

    def load_fabric_sample(self):
        self.load_sewout_coupon('fabric-profiles')

    def choose_sewout_coupon(self):
        from .coupons import COUPONS
        choices={key.replace('-',' ').capitalize():key for key in COUPONS}
        label,accepted=QInputDialog.getItem(self,'Load sewout coupon','Calibration design (100 × 100 mm field)',list(choices),0,False)
        if accepted and label in choices:self.load_sewout_coupon(choices[label])

    def export_sewout_coupon_pack(self):
        from .coupons import COUPONS
        from .coupon_worker import export_coupon
        choices={key.replace('-',' ').capitalize():key for key in COUPONS}
        label,accepted=QInputDialog.getItem(self,'Export sewout test pack',
            'Standard coupon (machine files, placement and evaluation forms)',list(choices),0,False)
        if not accepted or label not in choices:return
        parent=QFileDialog.getExistingDirectory(self,'Choose a folder for the new sewout pack')
        if not parent:return
        destination=Path(parent)/choices[label]
        try:
            report=export_coupon(choices[label],destination,self)
            if report is None:
                self.statusBar().showMessage(f'Sewout export cancelled. Any unfinished files are in {destination}.')
                return
        except FileExistsError:
            self.error(f'A pack already exists at {destination}. Choose another folder to keep the existing results.')
            return
        except (OSError,ValueError) as exc:
            self.error(f'Could not finish the sewout pack: {exc}\nAny files at {destination} are incomplete. Create a new pack before sewing.')
            return
        from .export_verify import verification_text
        details='\n\n'.join(verification_text(result,name) for name,result in report['export_verification'].items())
        self.statusBar().showMessage(f'Exported {label} sewout pack to {destination}')
        message=QMessageBox(self)
        message.setWindowTitle('Sewout test pack exported')
        message.setText(f'Saved {label} to {destination}')
        review=[name for name,result in report['export_verification'].items() if not result.get('verified')]
        summary=('Export checks need review: '+', '.join(review)+'. ') if review else 'All exported files passed software checks. '
        message.setIcon(QMessageBox.Icon.Warning if review else QMessageBox.Icon.Information)
        message.setInformativeText(summary+'Includes PES, EXP and DST files, an editable project, placement and evaluation PDFs, and blank machine/material records. Record your machine, hoop and materials before sewing.')
        message.setDetailedText(details)
        message.exec()

    def test_swatches(self):
        from .swatch_dialog import SwatchDialog
        from .swatches import build_swatches
        selected=self.selected_objects()
        if not selected:
            self.statusBar().showMessage('Select the parts to test first.');return
        dialog=SwatchDialog(selected,self)
        try:
            if dialog.exec()!=dialog.DialogCode.Accepted:return
            request=dialog.request()
        finally:dialog.deleteLater()
        try:project=build_swatches(self.project,{obj.id for obj in selected},**request)
        except ValueError as exc:
            self.error(str(exc));return
        # Built before asking, so a refused layout never discards the design.
        if not self.confirm_discard():return
        self.replace_project(project)
        self.statusBar().showMessage('Test swatches ready. Sew them on your real fabric and compare; the values are listed in Design → Design notes….')

    def load_sewout_coupon(self,name):
        if not self.confirm_discard():return
        from .coupons import build_project,COUPONS
        try:
            if name not in COUPONS:raise ValueError('Unknown sewout coupon.')
            project,_,_,guidance=build_project(name)
            self.replace_project(project)
            self.statusBar().showMessage(guidance)
        except ValueError as exc:self.error(str(exc))

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
            self.saved = self.serialized()
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
            # Reopen the file with the real reader so format problems are visible now.
            from .export_verify import verify_export, verification_text
            try:
                check = verify_export(self.blocks, path)
                notes.insert(0, verification_text(check, path.name))
            except Exception as exc:
                check = {"verified": False}
                notes.insert(0, f"Export check could not reopen {path.name}: {exc}")
            show = QMessageBox.information if check["verified"] else QMessageBox.warning
            show(self, "Stitches exported" if check["verified"] else "Check the exported file",
                 f"Saved {path.name}.\n\n" + "\n\n".join(notes) + "\n\nTest on scrap fabric. Keep your editable .morale project.")
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
        path, selected = QFileDialog.getSaveFileName(self, "Export thread sequence", "threads.csv", "Thread chart (*.csv);;INF palette (*.inf);;EDR palette (*.edr)")
        if path:
            try:
                extension='.inf' if '*.inf' in selected else '.edr' if '*.edr' in selected else '.csv'
                target=Path(path)
                if target.suffix.lower()!=extension:
                    target=target.with_suffix(extension)
                    if not self.confirm_replacement(target):return
                if extension=='.csv':
                    save_chart(self.project,self.blocks,target)
                else:
                    from .thread_palette_files import design_palette,write_palette
                    result=write_palette(target,design_palette(self.blocks))
                    detail='Descriptions and chart names retained.' if extension=='.inf' else 'RGB colors only; metadata omitted.'
                    QMessageBox.information(self,'Design palette saved',f"{result['colors']} native thread runs saved in sewing order. {detail}\nPauses do not add entries. Machine formats may encode pauses as extra thread changes; this palette is not automatically paired with a machine file.")
                self.statusBar().showMessage(f"Thread sequence saved · {target}")
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def checkpoint(self):
        if not self.recovery:
            return
        try:
            current = self.serialized()
            if not self.dirty:
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
