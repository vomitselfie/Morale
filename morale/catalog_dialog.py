"""Native searchable thread catalog, with a virtual table for large collections."""
import math
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QLineEdit,QTableView,QAbstractItemView,QDialogButtonBox,QFileDialog,QMessageBox,QHeaderView

from .catalogs import builtin_catalog,read_catalog,distance_squared


class CatalogModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows=[]

    def rowCount(self,parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.rows)

    def columnCount(self,parent=None):
        return 0 if parent is not None and parent.isValid() else 5

    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:
            return ['Color','Brand','Catalog number','Description','RGB distance'][section]

    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        score,entry=self.rows[index.row()]
        if role==Qt.ItemDataRole.DisplayRole:
            return [entry.color,entry.metadata.get('brand',''),entry.metadata.get('catalog_number',''),entry.metadata.get('description',''),f'{math.sqrt(score):.1f}'][index.column()]
        if index.column()==0:
            if role==Qt.ItemDataRole.DecorationRole:
                return QColor(entry.color)

    def set_rows(self,rows):
        self.beginResetModel()
        self.rows=rows
        self.endResetModel()


class CatalogDialog(QDialog):
    def __init__(self,color,count,parent=None,cached=None):
        super().__init__(parent)
        self.setWindowTitle('Thread catalog')
        self.color=color
        self.mode='thread'
        self.entry=None
        self.candidates=[]
        layout=QVBoxLayout(self)
        text=QLabel(f'Assign a thread to {count} selected object(s), or match their colors separately to the shown threads. Rows are ranked by RGB distance from {color}. RGB distance is approximate; compare actual thread samples.')
        text.setWordWrap(True)
        layout.addWidget(text)
        row=QHBoxLayout()
        self.catalog_choice=QComboBox()
        self.catalog_choice.addItems(['PEC fixed palette','JEF fixed palette'])
        self.catalog_choice.setAccessibleName('Thread catalog')
        row.addWidget(self.catalog_choice,1)
        load=QPushButton('Import CSV…')
        load.clicked.connect(self.load_csv)
        row.addWidget(load)
        layout.addLayout(row)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Search brand, number, description or RGB')
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
        layout.addWidget(self.table,1)
        note=QLabel('Built-ins are fixed machine-format palettes, not verified current spool inventories. CSV requires color (#RRGGBB); optional columns: brand, catalog_number, description, weight, chart, details. Morale thread-chart CSVs also work; other columns are ignored.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        controls.button(QDialogButtonBox.StandardButton.Ok).setText('Assign highlighted thread')
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
        self.rank()
        self.resize(900,600)

    def rank(self):
        self.ranked=sorted([(distance_squared(self.color,entry.color),entry) for entry in self.catalog],key=lambda pair:pair[0])
        self.filter_rows()

    def filter_rows(self):
        query=self.search.text().casefold()
        self.model.set_rows([(score,entry) for score,entry in self.ranked if query in ' '.join([entry.color,*entry.metadata.values()]).casefold()])
        if self.model.rows:
            self.table.selectRow(0)

    def choose_catalog(self,name):
        if name in {'PEC fixed palette','JEF fixed palette'}:
            self.catalog_name,self.catalog=name,builtin_catalog(name)
        else:
            self.catalog_name,self.catalog=self.custom
        self.rank()

    def load_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'Import thread catalog','','CSV thread catalog (*.csv)')
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
