from pathlib import Path
import json
import tempfile
import unittest
from engine import plan, apply, undo, latest_pending, Move


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"files"
        self.root.mkdir()
        self.history=Path(self.temp.name)/"history"
        (self.root/"örnek.pdf").write_bytes(b"important")

    def test_preview_has_no_side_effect(self):
        moves,skipped=plan(self.root)
        self.assertEqual(len(moves),1)
        self.assertEqual(skipped,0)
        self.assertFalse((self.root/"Belgeler").exists())
        self.assertTrue((self.root/"örnek.pdf").exists())

    def test_roundtrip_and_persistent_history(self):
        journal,records=apply(plan(self.root)[0],self.history)
        self.assertEqual(records[0]["state"],"moved")
        self.assertEqual(latest_pending(self.history),journal)
        self.assertEqual(undo(journal)[0]["state"],"undone")
        self.assertEqual((self.root/"örnek.pdf").read_bytes(),b"important")
        self.assertIsNone(latest_pending(self.history))

    def test_name_conflicts_get_suffix(self):
        (self.root/"Belgeler").mkdir()
        (self.root/"Belgeler"/"örnek.pdf").write_bytes(b"existing")
        moves,_=plan(self.root)
        self.assertTrue(moves[0].destination.endswith("örnek (1).pdf"))
        apply(moves,self.history)
        self.assertEqual((self.root/"Belgeler"/"örnek.pdf").read_bytes(),b"existing")

    def test_preview_race_does_not_overwrite(self):
        moves,_=plan(self.root)
        destination=Path(moves[0].destination)
        destination.parent.mkdir()
        destination.write_bytes(b"new")
        _,records=apply(moves,self.history)
        self.assertEqual(records[0]["state"],"failed")
        self.assertEqual(destination.read_bytes(),b"new")
        self.assertTrue(Path(moves[0].source).exists())

    def test_changed_source_is_skipped(self):
        moves,_=plan(self.root)
        (self.root/"örnek.pdf").write_bytes(b"changed content")
        _,records=apply(moves,self.history)
        self.assertEqual(records[0]["state"],"failed")

    def test_changed_destination_blocks_undo(self):
        journal,records=apply(plan(self.root)[0],self.history)
        Path(records[0]["destination"]).write_bytes(b"edited afterwards")
        self.assertEqual(undo(journal)[0]["state"],"conflict")
        self.assertFalse((self.root/"örnek.pdf").exists())

    def test_original_name_reused_blocks_undo(self):
        journal,_=apply(plan(self.root)[0],self.history)
        (self.root/"örnek.pdf").write_bytes(b"different")
        self.assertEqual(undo(journal)[0]["state"],"conflict")
        self.assertEqual((self.root/"örnek.pdf").read_bytes(),b"different")

    def test_recover_crash_after_move(self):
        journal,_=apply(plan(self.root)[0],self.history)
        data=json.loads(journal.read_text(encoding="utf-8"))
        data["records"][0]["state"]="moving"
        journal.write_text(json.dumps(data),encoding="utf-8")
        self.assertEqual(undo(journal)[0]["state"],"undone")

    def test_excludes_unknown_hidden_and_subfolders(self):
        (self.root/"app.exe").write_bytes(b"exe")
        (self.root/".private.txt").write_text("secret")
        (self.root/"nested").mkdir()
        (self.root/"nested"/"child.pdf").write_bytes(b"child")
        moves,skipped=plan(self.root)
        self.assertEqual(len(moves),1)
        self.assertEqual(skipped,3)

    def test_invalid_destination_is_rejected(self):
        move=plan(self.root)[0][0]
        invalid=Move(move.source,str(Path(self.temp.name)/"outside.pdf"),move.identity,move.category)
        _,records=apply([invalid],self.history)
        self.assertEqual(records[0]["state"],"failed")


if __name__=="__main__": unittest.main()
