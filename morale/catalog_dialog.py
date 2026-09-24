"""Native searchable thread catalog, with a virtual table for large collections."""
import math
from collections import Counter
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel,QTimer,QModelIndex
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QLineEdit,QTableView,QAbstractItemView,QDialogButtonBox,QFileDialog,QMessageBox,QHeaderView,QTabWidget

from .catalogs import builtin_catalog,read_catalog,distance_squared,nearest_thread


class CatalogModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows=[]
        self.metric="rgb"

    def rowCount(self,parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.rows)

    def columnCount(self,parent=None):
        return 0 if parent is not None and parent.isValid() else 6

    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:
            return ['Color','Brand','Catalog number','Description','Chart','Oklab ×100' if self.metric=='oklab' else 'RGB distance'][section]

    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        score,entry=self.rows[index.row()]
        if role==Qt.ItemDataRole.DisplayRole:
            return [entry.color,entry.metadata.get('brand',''),entry.metadata.get('catalog_number',''),entry.metadata.get('description',''),entry.metadata.get('chart',''),f'{math.sqrt(score):.1f}'][index.column()]
        if index.column()==0:
            if role==Qt.ItemDataRole.DecorationRole:
                return QColor(entry.color)

    def set_rows(self,rows):
        self.beginResetModel()
        self.rows=rows
        self.endResetModel()


class MatchModel(QAbstractTableModel):
    def __init__(self,parent=None):super().__init__(parent);self.rows=[];self.metric='oklab'
    def rowCount(self,parent=None):return 0 if parent is not None and parent.isValid() else len(self.rows)
    def columnCount(self,parent=None):return 0 if parent is not None and parent.isValid() else 6
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if orientation==Qt.Orientation.Horizontal and role==Qt.ItemDataRole.DisplayRole:
            return ['Source','Proposed thread','Description','Chart','Oklab ×100' if self.metric=='oklab' else 'RGB distance','Objects'][section]
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        source,count,entry,distance=self.rows[index.row()]
        if role==Qt.ItemDataRole.DisplayRole:return [source,entry.color,entry.metadata.get('description',''),entry.metadata.get('chart',''),f'{distance:.1f}',str(count)][index.column()]
        if role==Qt.ItemDataRole.DecorationRole and index.column() in (0,1):return QColor(source if index.column()==0 else entry.color)
    def clear(self,metric):self.beginResetModel();self.rows=[];self.metric=metric;self.endResetModel()
    def append(self,row):
        index=len(self.rows);self.beginInsertRows(QModelIndex(),index,index);self.rows.append(row);self.endInsertRows()


class CatalogDialog(QDialog):
    def __init__(self,color,count,parent=None,cached=None,metric="oklab",colors=None):
        super().__init__(parent)
        self.setWindowTitle('Thread catalog')
        self.source_colors=list(Counter(c.lower() for c in (colors or [color])).items())
        self._closed=False
        self.color=color
        self.mode='thread'
        self.entry=None
        self.candidates=[]
        layout=QVBoxLayout(self)
        text=QLabel(f'Assign a thread to {count} selected object(s), or match their colors separately to the shown threads. Rows are ranked from {color} using the selected color metric. These are screen-color estimates; compare actual thread samples.')
        text.setWordWrap(True)
        layout.addWidget(text)
        row=QHBoxLayout()
        self.catalog_choice=QComboBox()
        self.catalog_choice.addItems(['PEC fixed palette','JEF fixed palette'])
        self.catalog_choice.setAccessibleName('Thread catalog')
        row.addWidget(self.catalog_choice,1)
        load=QPushButton('Import palette…')
        load.clicked.connect(self.load_csv)
        row.addWidget(load)
        self.export_button=QPushButton('Export shown palette…');self.export_button.clicked.connect(self.export_palette)
        self.export_button.setToolTip('Save the filtered catalog in its displayed order. INF retains descriptions/chart names; EDR stores RGB only. These files contain no stitches.')
        row.addWidget(self.export_button)
        self.metric_choice=QComboBox();self.metric_choice.addItem('Perceptual (Oklab)','oklab');self.metric_choice.addItem('RGB comparison','rgb')
        self.metric_choice.setAccessibleName('Thread matching color metric')
        self.metric_choice.setCurrentIndex(max(0,self.metric_choice.findData(metric)))
        row.addWidget(self.metric_choice)
        layout.addLayout(row)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Search brand, number, description, chart or RGB')
        self.search.setAccessibleName('Search thread catalog')
        self.search.textChanged.connect(self.filter_rows)
        layout.addWidget(self.search)
        self.table=QTableView()
        self.model=CatalogModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAccessibleName('Available catalog threads')
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.match_table=QTableView();self.match_model=MatchModel(self);self.match_table.setModel(self.match_model)
        self.match_table.setAccessibleName('Proposed thread matches for selected objects')
        self.match_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs=QTabWidget();self.tabs.addTab(self.table,'Catalog threads');self.tabs.addTab(self.match_table,'Match preview')
        layout.addWidget(self.tabs,1)
        self.match_status=QLabel();layout.addWidget(self.match_status)
        self.match_timer=QTimer(self);self.match_timer.setInterval(0);self.match_timer.timeout.connect(self.advance_matches)
        self.tabs.currentChanged.connect(self.refresh_matches)
        note=QLabel('Built-ins are fixed machine-format palettes, not verified current spool inventories. CSV requires color (#RRGGBB); optional columns: brand, catalog_number, description, weight, chart, details. Morale thread-chart CSVs also work; other columns are ignored. INF preserves RGB colors, descriptions and chart names; EDR provides RGB colors only.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.assign_button=controls.button(QDialogButtonBox.StandardButton.Ok)
        self.assign_button.setText('Assign highlighted thread')
        controls.accepted.connect(self.assign)
        controls.rejected.connect(self.reject)
        match=controls.addButton('Match colors to shown threads',QDialogButtonBox.ButtonRole.ActionRole)
        match.clicked.connect(self.match_colors)
        layout.addWidget(controls)
        self.catalog_choice.currentTextChanged.connect(self.choose_catalog)
        self.catalog_name='PEC fixed palette'
        self.catalog=builtin_catalog(self.catalog_name)
        if cached:
            self.catalog_name,self.catalog=cached
            if self.catalog_choice.findText(self.catalog_name)<0:
                self.custom=cached
                self.catalog_choice.addItem(self.catalog_name)
            self.catalog_choice.blockSignals(True)
            self.catalog_choice.setCurrentText(self.catalog_name)
            self.catalog_choice.blockSignals(False)
        self.metric_choice.currentIndexChanged.connect(self.rank)
        self.rank()
        self.resize(900,600)

    def rank(self):
        self.model.metric=self.metric_choice.currentData()
        if self.model.metric=='oklab':
            from .perceptual_color import distance_squared as score
        else:score=distance_squared
        self.ranked=sorted([(score(self.color,entry.color),entry) for entry in self.catalog],key=lambda pair:pair[0])
        self.filter_rows()

    def filter_rows(self):
        query=self.search.text().casefold()
        self.model.set_rows([(score,entry) for score,entry in self.ranked if query in ' '.join([entry.color,*entry.metadata.values()]).casefold()])
        if self.model.rows:
            self.table.selectRow(0)
        self.refresh_matches()

    def refresh_matches(self,*unused):
        self.match_timer.stop();self.match_model.clear(self.metric_choice.currentData())
        self.match_entries=[entry for score,entry in self.model.rows]
        self.match_status.clear()
        self.assign_button.setEnabled(self.tabs.currentIndex()==0 and bool(self.model.rows))
        self.export_button.setEnabled(self.tabs.currentIndex()==0 and bool(self.model.rows))
        if self._closed or self.tabs.currentIndex()!=1:return
        if not self.match_entries:self.match_status.setText('No threads match the current filter.');return
        self.match_status.setText('Preparing proposed matches…');self.match_timer.start()

    def advance_matches(self):
        if self._closed or self.tabs.currentIndex()!=1 or not self.match_entries:self.match_timer.stop();return
        index=len(self.match_model.rows)
        # Yield to native events after each source color, even for large catalogs.
        if index<len(self.source_colors):
            color,count=self.source_colors[index];metric=self.match_model.metric
            entry=nearest_thread(color,self.match_entries,metric)
            if metric=='oklab':
                from .perceptual_color import distance_squared as score
            else:score=distance_squared
            self.match_model.append((color,count,entry,math.sqrt(score(color,entry.color))))
        complete=len(self.match_model.rows)==len(self.source_colors)
        self.match_status.setText(f'{len(self.match_model.rows)} of {len(self.source_colors)} source colors matched. Matching uses only the currently shown catalog threads.')
        if complete:self.match_timer.stop()

    def done(self,result):
        self._closed=True;self.match_timer.stop();super().done(result)

    def choose_catalog(self,name):
        if name in {'PEC fixed palette','JEF fixed palette'}:
            self.catalog_name,self.catalog=name,builtin_catalog(name)
        else:
            self.catalog_name,self.catalog=self.custom
        self.rank()

    def load_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'Import thread catalog','','Thread catalogs and palettes (*.csv *.inf *.edr);;CSV (*.csv);;INF palette (*.inf);;EDR palette (*.edr)')
        if path:
            try:
                entries=read_catalog(path)
                self.custom=(Path(path).name,entries)
                self.catalog_choice.blockSignals(True)
                while self.catalog_choice.count()>2:
                    self.catalog_choice.removeItem(2)
                self.catalog_choice.addItem(self.custom[0])
                self.catalog_choice.setCurrentIndex(2)
                self.catalog_choice.blockSignals(False)
                self.choose_catalog(self.custom[0])
            except (OSError,ValueError) as exc:
                QMessageBox.warning(self,'Catalog import',str(exc))

    def export_palette(self):
        entries=[entry for score,entry in self.model.rows]
        if not entries:
            QMessageBox.information(self,'Export palette','No threads match the current filter.');return
        path,selected=QFileDialog.getSaveFileName(self,'Export shown thread palette','threads.inf',
            'INF — RGB, descriptions and chart names (*.inf);;EDR — RGB only (*.edr)')
        if not path:return
        if not Path(path).suffix:path+='.edr' if '*.edr' in selected else '.inf'
        from .thread_palette_files import write_palette
        try:
            result=write_palette(path,entries)
            detail='Descriptions and chart names retained; other metadata omitted.' if result['metadata_fields'] else 'RGB colors only; metadata omitted.'
            QMessageBox.information(self,'Palette saved',f"{result['colors']} colors saved in displayed order. {detail}")
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Export palette',str(exc))

    def assign(self):
        index=self.table.currentIndex()
        if index.isValid():
            self.mode='thread'
            self.entry=self.model.rows[index.row()][1]
            self.accept()

    def match_colors(self):
        if self.model.rows:
            self.mode='nearest'
            self.candidates=[entry for score,entry in self.model.rows]
            self.accept()
