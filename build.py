"""Build an inspectable Windows portable folder and ZIP. Run from this repository."""
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent
    meta=json.loads((root/"app.json").read_text(encoding="utf-8"))
    name,version=meta["name"],meta["version"]
    subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed","--onedir",
                    "--name",name,"--icon",str(root/"app.ico"),"--distpath",str(root/"dist"),
                    "--workpath",str(root/"build"),"--specpath",str(root),str(root/"main.py")],cwd=root,check=True)
    target=root/"dist"/name
    for filename in ("LICENSE","README.md","THIRD_PARTY_NOTICES.txt"):
        shutil.copy2(root/filename,target/filename)
    licenses=target/"licenses"
    licenses.mkdir(exist_ok=True)
    for package in ("PySide6-Essentials","shiboken6","Pillow"):
        try: dist=distribution(package)
        except Exception: continue
        for file in dist.files or []:
            path=str(file).replace("\\","/")
            if any(word in path.lower() for word in ("license","copying")) and Path(dist.locate_file(file)).is_file():
                output=licenses/package/path
                output.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(dist.locate_file(file),output)
    release=root/"release"
    release.mkdir(exist_ok=True)
    archive=shutil.make_archive(str(release/f"{name}-{version}-Windows-x64"),"zip",root/"dist",name)
    digest=hashlib.file_digest(open(archive,"rb"),"sha256").hexdigest()
    (release/"SHA256SUMS.txt").write_text(f"{digest}  {Path(archive).name}\n",encoding="utf-8")
    print(archive)


if __name__=="__main__": main()
