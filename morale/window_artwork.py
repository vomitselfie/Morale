"""Lettering, appliqué, artwork conversion, threads, motifs and reference images."""
from copy import deepcopy
from pathlib import Path
import uuid
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from .model import Project
from .lettering import LetteringDialog
from .reference import import_reference, decode_reference
from .reference_dialog import ReferenceDialog
from .svg_import import import_svg
from .catalog_dialog import CatalogDialog
from .catalogs import nearest_thread
from .motifs import capture_motif, load_motif, save_motif, validate_packet
from .trace_dialog import TraceDialog
from .applique import AppliqueDialog, applique_stages
from .engine import generate


class ArtworkMixin:
    def add_lettering(self):
        dialog = LetteringDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                selected = self.selected_object()
                if selected:
                    dialog.candidate.color = selected.color
                    dialog.candidate.thread = dict(selected.thread)
                self.apply_lettering(dialog.candidate)
            except ValueError as exc:
                self.error(str(exc))

    def add_path_lettering(self):
        selected = self.selected_objects()
        if len(selected) != 1 or selected[0].kind not in {"path", "polygon"}:
            self.statusBar().showMessage("Select one drawn path or polygon for the lettering baseline.")
            return
        guide = selected[0]
        baseline = list(guide.outline())
        if guide.kind == "polygon" and baseline and baseline[-1] != baseline[0]:
            baseline.append(baseline[0])
        dialog = LetteringDialog(parent=self, baseline=baseline)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                dialog.candidate.color = guide.color
                dialog.candidate.thread = dict(guide.thread)
                self.apply_lettering(dialog.candidate, hide_guide_id=None if dialog.keep_baseline.isChecked() else guide.id)
            except ValueError as exc:
                self.error(str(exc))

    def create_applique(self):
        if not self.selected_object():
            self.statusBar().showMessage("Select a closed outline first.")
            return
        dialog = AppliqueDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.apply_applique(dialog.border_width.value(),dialog.cover_mode.currentData())
            except ValueError as exc:
                self.error(str(exc))

    def apply_applique(self, border_width,cover_mode='fill'):
        obj = self.selected_object()
        if not obj:
            raise ValueError("Select a closed outline first.")
        if len(self.project.objects) + 2 > 500:
            raise ValueError("Appliqué stages would exceed the 500-object limit.")
        stages = applique_stages(obj, border_width,cover_mode)
        if len(self.project.objects)-1+len(stages)>500:
            raise ValueError('Appliqué borders would exceed the 500-object limit.')
        combined = deepcopy(self.project)
        index = self.project.objects.index(obj)
        combined.objects[index:index + 1] = stages
        generate(combined)
        self.selected_id = stages[0].id
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def edit_lettering(self):
        obj = self.selected_object()
        if not obj or not obj.lettering:
            self.statusBar().showMessage("Select a lettering object first.")
            return
        dialog = LetteringDialog(obj, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.apply_lettering(dialog.candidate, replace=True)
            except ValueError as exc:
                self.error(str(exc))

    def change_lettering_stitches(self, obj, stitch_type):
        """Switch lettering stitches; choosing satin plans its columns."""
        from .lettering import STITCH_TYPES, finish_lettering
        if stitch_type not in STITCH_TYPES:
            self.sync_properties()
            return
        candidate = deepcopy(obj)
        try:
            self.statusBar().showMessage("Planning satin columns…" if stitch_type == "satin" else "")
            QApplication.processEvents()
            candidate = finish_lettering(candidate, obj, stitch_type)
            self.apply_lettering(candidate, replace=True)
        except ValueError as exc:
            self.error(f"Could not change the lettering stitches.\n{exc}")
            self.sync_properties()

    def apply_lettering(self, candidate, replace=False, hide_guide_id=None):
        combined = deepcopy(self.project)
        if hide_guide_id is not None:
            guide = next((obj for obj in combined.objects if obj.id == hide_guide_id), None)
            if guide is None:
                raise ValueError("The lettering baseline no longer exists.")
            guide.visible = False
        if replace:
            index = next(i for i, obj in enumerate(self.project.objects) if obj.id == candidate.id)
            combined.objects[index] = candidate
        else:
            if len(combined.objects) >= 500:
                raise ValueError("Project exceeds the 500-object limit.")
            combined.objects.append(candidate)
        Project.loads(combined.dumps())
        generate(combined)
        self.selected_id = candidate.id
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def apply_svg_artwork(self, path):
        result = import_svg(path)
        combined = deepcopy(self.project)
        combined.objects.extend(result.objects)
        Project.loads(combined.dumps())
        generate(combined)
        self._selected_id = result.objects[0].id
        self.selected_ids = {obj.id for obj in result.objects}
        self.commit(lambda: setattr(self.project, "objects", combined.objects))
        self.set_mode("select")
        return result

    def import_svg_artwork(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import SVG artwork", "", "SVG artwork (*.svg)")
        if not path:
            return
        try:
            result = self.apply_svg_artwork(path)
            self.statusBar().showMessage(f"Imported {len(result.objects)} editable SVG objects at their physical size, centered in the hoop.")
            if result.notices:
                QMessageBox.information(self, "SVG import notes", "\n\n".join(result.notices))
        except (OSError, ValueError) as exc:
            self.error(str(exc))

    def apply_catalog_threads(self,entries,nearest=False,metric="rgb"):
        objects=self.selected_objects()
        if not objects:
            raise ValueError("Select objects to assign catalog threads.")
        if not entries:
            raise ValueError("Choose at least one catalog thread.")
        selected={obj.id for obj in objects}
        combined=deepcopy(self.project)
        for obj in combined.objects:
            if obj.id in selected:
                entry=nearest_thread(obj.color,entries,metric) if nearest else entries[0]
                obj.color=entry.color
                obj.thread=dict(entry.metadata)
        Project.loads(combined.dumps())
        generate(combined)
        if combined.dumps()!=self.project.dumps():
            self.commit(lambda:setattr(self.project,"objects",combined.objects))

    def thread_catalog_dialog(self):
        objects=self.selected_objects()
        if not objects:
            self.statusBar().showMessage("Select objects to assign or match thread colors.")
            return
        dialog=CatalogDialog(objects[0].color,len(objects),self,getattr(self,"thread_catalog",None),metric=getattr(self,"thread_match_metric","oklab"),colors=[obj.color for obj in objects])
        try:
            accepted=dialog.exec()==dialog.DialogCode.Accepted
            self.thread_catalog=(dialog.catalog_name,dialog.catalog)
            self.thread_match_metric=dialog.metric_choice.currentData()
            if accepted:
                self.apply_catalog_threads(dialog.candidates if dialog.mode=='nearest' else [dialog.entry],dialog.mode=='nearest',dialog.metric_choice.currentData())
        except ValueError as exc:
            self.error(str(exc))
        finally:
            dialog.deleteLater()

    def capture_custom_motif(self):
        obj=self.selected_object()
        if not obj:
            self.statusBar().showMessage("Select one editable outline to capture.")
            return
        try:
            self.captured_motif=capture_motif(obj)
            self.statusBar().showMessage("Captured outline. Select guide objects, then choose Apply captured / loaded motif.")
        except ValueError as exc:
            self.error(str(exc))

    def apply_custom_motif(self):
        packet=getattr(self,'captured_motif',None)
        objects=self.selected_objects()
        if not packet or not objects:
            self.statusBar().showMessage("Capture or load a motif, then select its guide objects.")
            return
        try:
            validate_packet(packet)
            if any(o.kind in {'stitches','satin'} for o in objects):
                raise ValueError("Motif guides must be editable paths or closed shapes.")
            combined=deepcopy(self.project)
            ids={o.id for o in objects}
            for obj in combined.objects:
                if obj.id in ids:
                    obj.custom_motif_paths=deepcopy(packet['paths'])
                    obj.custom_motif_name=packet['name']
                    obj.motif_pattern='custom'
                    if obj.stitch_type!='pattern':
                        obj.stitch_type='motif'
            Project.loads(combined.dumps())
            generate(combined)
            if combined.dumps()!=self.project.dumps():
                self.commit(lambda:setattr(self.project,'objects',combined.objects))
        except ValueError as exc:
            self.error(str(exc))

    def load_custom_motif(self):
        path,_=QFileDialog.getOpenFileName(self,'Load custom motif','','Morale motif (*.mmotif)')
        if path:
            try:
                self.captured_motif=load_motif(path)
                self.statusBar().showMessage("Loaded motif. Select guides and choose Apply captured / loaded motif.")
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def save_custom_motif(self,selected=False):
        packet=None if selected else getattr(self,'captured_motif',None)
        obj=self.selected_object()
        if selected and obj and obj.custom_motif_paths:
            packet={'format':'morale-motif','version':1,'name':obj.custom_motif_name,'paths':obj.custom_motif_paths}
        if packet is None:
            self.statusBar().showMessage("Select a guide containing a custom motif." if selected else "Capture or load a motif first.")
            return
        name,_=QFileDialog.getSaveFileName(self,'Save custom motif','custom.mmotif','Morale motif (*.mmotif)')
        if name:
            path=Path(name)
            if path.suffix.lower()!='.mmotif':
                path=path.with_suffix('.mmotif')
                if not self.confirm_replacement(path):
                    return
            try:
                save_motif(packet,path)
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def apply_raster_trace(self,project):
        combined=deepcopy(self.project)
        objects=deepcopy(project.objects)
        if not objects:
            raise ValueError("The trace contains no objects to add.")
        for obj in objects:
            obj.id=uuid.uuid4().hex
        combined.objects.extend(objects)
        if project.reference:
            decode_reference(project.reference)
            combined.reference=deepcopy(project.reference)
        Project.loads(combined.dumps())
        generate(combined)
        self._selected_id=objects[0].id
        self.selected_ids={obj.id for obj in objects}
        def apply():
            self.project.objects=combined.objects
            self.project.reference=combined.reference
        self.commit(apply)
        self.set_mode('select')

    def digitize_raster(self):
        path,_=QFileDialog.getOpenFileName(self,'Digitize artwork','','Artwork (*.svg *.png *.jpg *.jpeg *.bmp *.webp)')
        if path:
            dialog=TraceDialog(path,self)
            try:
                if dialog.exec()==dialog.DialogCode.Accepted and dialog.project is not None:
                    self.apply_raster_trace(dialog.project)
            except ValueError as exc:
                self.error(str(exc))
            finally:
                dialog.runner.cancel()
                dialog.deleteLater()

    def add_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import reference image", "", "Raster images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            try:
                self.set_reference(import_reference(path, self.project.hoop_width, self.project.hoop_height))
            except (ValueError, OSError) as exc:
                self.error(str(exc))

    def set_reference(self, reference):
        candidate = deepcopy(self.project)
        candidate.reference = reference
        Project.loads(candidate.dumps())
        decode_reference(reference)
        self.commit(lambda: setattr(self.project, "reference", deepcopy(reference)))

    def edit_reference(self):
        if not self.project.reference:
            self.statusBar().showMessage("Import a reference image first.")
            return
        dialog = ReferenceDialog(self.project.reference, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.set_reference(dialog.result_reference())
