import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QTableWidgetItem, QHeaderView

from desktop import Shell, button, label, metric, table, run
from engine import plan, apply, undo, latest_pending


class Window(Shell):
    def __init__(self, folder):
        super().__init__("Düzen", "Dağınıklığa küçük\nbir ara ver.", "Her dosya, kendi yerinde.",
                         "Bir klasör seç. Taşınacak dosyaları gör, seç ve tek adımda düzenle.", "Dosya düzenleyici")
        self.folder = folder
        self.history = folder / "history"
        self.moves = []
        self.last_journal = latest_pending(self.history)
        metrics = QHBoxLayout()
        a, self.count = metric("HAZIR DOSYA", "0")
        b, self.groups = metric("KATEGORİ", "0")
        c, self.skipped = metric("ATLANAN", "0")
        for item in (a, b, c):
            metrics.addWidget(item)
        self.body.addLayout(metrics)
        chooser = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("Düzenlemek istediğin klasörün yolu")
        chooser.addWidget(self.path, 1)
        chooser.addWidget(button("Klasör seç", self.choose))
        self.scan_button = button("Önizle", self.scan, True)
        chooser.addWidget(self.scan_button)
        self.body.addLayout(chooser)
        self.grid = table(["Seç", "Dosya adı", "Yeni konum", "Boyut"])
        self.grid.horizontalHeader().setStretchLastSection(False)
        self.grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.grid.setColumnWidth(0, 50)
        self.body.addWidget(self.grid, 1)
        note = label("Yalnızca bu klasörün içindeki belge, fotoğraf, video, ses ve arşivler işlenir. Alt klasörlere girilmez.", "muted", True)
        self.body.addWidget(note)
        controls = QHBoxLayout()
        controls.addWidget(button("Tümünü seç / kaldır", self.toggle_all))
        self.undo_button = button("Son işlemi geri al", self.revert)
        self.undo_button.setEnabled(self.last_journal is not None)
        controls.addWidget(self.undo_button)
        controls.addStretch()
        self.apply_button = button("Seçilenleri düzenle", self.organize, True)
        self.apply_button.setEnabled(False)
        controls.addWidget(self.apply_button)
        self.body.addLayout(controls)
        self.finish_layout()
        self.status.setText("Dosyalar, onay verdiğinde taşınır. Mevcut dosyaların üzerine yazılmaz.")

    def choose(self):
        folder = QFileDialog.getExistingDirectory(self, "Düzenlenecek klasör")
        if folder:
            self.path.setText(folder)
            self.scan()

    def scan(self):
        folder = self.path.text().strip()
        if not folder:
            self.status.setText("Önce bir klasör seçin.")
            return
        self.work(lambda: plan(folder), self.show_plan)

    def show_plan(self, result):
        self.moves, skipped = result
        self.grid.setRowCount(len(self.moves))
        for row, move in enumerate(self.moves):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.grid.setItem(row, 0, item)
            for col, text in enumerate((Path(move.source).name,
                                         str(Path(move.destination).relative_to(Path(move.source).parent)),
                                         f"{move.identity[2] / 1024:.1f} KB"), 1):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                self.grid.setItem(row, col, cell)
        self.count.setText(str(len(self.moves)))
        self.groups.setText(str(len({m.category for m in self.moves})))
        self.skipped.setText(str(skipped))
        self.apply_button.setEnabled(bool(self.moves))
        self.status.setText(f"{len(self.moves)} dosya hazır. Henüz hiçbir dosya taşınmadı.")

    def selected(self):
        return [m for row, m in enumerate(self.moves)
                if self.grid.item(row, 0).checkState() == Qt.CheckState.Checked]

    def toggle_all(self):
        state = Qt.CheckState.Unchecked if self.selected() else Qt.CheckState.Checked
        for row in range(self.grid.rowCount()):
            self.grid.item(row, 0).setCheckState(state)

    def organize(self):
        moves = self.selected()
        if not moves:
            self.status.setText("En az bir dosya seçin.")
            return
        answer = QMessageBox.question(self, "Dosyalar taşınacak",
            f"{len(moves)} dosya önizlemedeki klasörlere taşınacak. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.work(lambda: apply(moves, self.history), self.applied)

    def applied(self, result):
        self.last_journal, records = result
        count = sum(r["state"] == "moved" for r in records)
        self.moves = []
        self.grid.setRowCount(0)
        self.apply_button.setEnabled(False)
        self.undo_button.setEnabled(count > 0)
        self.count.setText("0")
        self.groups.setText("0")
        errors = [r["error"] for r in records if r["error"]]
        self.status.setText(f"{count} dosya düzenlendi. {len(errors)} dosya atlandı." + (" " + errors[0] if errors else " Geri alabilirsiniz."))

    def revert(self):
        self.last_journal = latest_pending(self.history)
        if not self.last_journal:
            self.status.setText("Geri alınacak işlem yok.")
            self.undo_button.setEnabled(False)
            return
        self.work(lambda: undo(self.last_journal), self.reverted)

    def reverted(self, records):
        undone = sum(r["state"] == "undone" for r in records)
        conflicts = sum(r["state"] == "conflict" for r in records)
        self.status.setText(f"{undone} dosya eski konumuna döndü. {conflicts} çakışma." +
                            (" Değişen dosyalar korunarak atlandı." if conflicts else ""))
        self.last_journal = latest_pending(self.history)
        self.undo_button.setEnabled(self.last_journal is not None)

    def seed_demo(self):
        root = self.folder / "Örnek dosyalar"
        root.mkdir()
        for name in ["Tatil fotoğrafı.jpg", "Toplantı notları.docx", "Sunum.pdf", "Müzik.mp3", "Video.mp4", "Belgeler.zip"]:
            (root / name).write_bytes(b"demo" * 512)
        self.path.setText(str(root))
        self.show_plan(plan(root))
        self.status.setText("Örnek görünüm · Dosyalar yalnızca test klasöründe oluşturuldu.")

    def smoke(self):
        assert self.grid.rowCount() == 6
        self.toggle_all()
        assert not self.selected()
        self.toggle_all()
        journal, records = apply(self.selected(), self.history)
        assert all(r["state"] == "moved" for r in records)
        assert all(r["state"] == "undone" for r in undo(journal))
        return ["preview", "selection", "organize", "persistent undo"]


if __name__ == "__main__":
    sys.exit(run(Window, "Duzen"))
