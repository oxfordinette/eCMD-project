"""Construit le paquet des Lambdas de soumission (ecmd-creer-dossier, ecmd-accuse-reception).

Contenu du zip :
  - traiter_soumission.py                (point d'entrée des Lambdas)
  - app/ : config, db, models, portail_logic, soumission — copie du backend cellmed (même règle de création)
  - dépendances : SQLAlchemy, psycopg (binaire), pydantic-settings, databricks-sdk (jeton Lakebase)

Exécuté par le service docker compose « lambda-build » (image python:3.12-slim) ; résultat : /build/soumission.zip.
Les roues sont choisies pour Lambda Python 3.12 x86_64, quelle que soit la machine de construction.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SRC_APP = Path("/src/app")
SRC_LAMBDAS = Path("/src/lambdas")
BUILD = Path("/build")
PKG = BUILD / "pkg"
ZIP = BUILD / "soumission.zip"
MODULES_APP = ["__init__.py", "config.py", "db.py", "models.py", "portail_logic.py", "soumission.py"]
DEPENDANCES = ["sqlalchemy>=2.0", "psycopg[binary]>=3.1", "pydantic>=2", "pydantic-settings>=2", "databricks-sdk>=0.146"]

shutil.rmtree(PKG, ignore_errors=True)
PKG.mkdir(parents=True)
print("▶ Installation des dépendances des Lambdas…", flush=True)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir", "--target", str(PKG),
     "--platform", "manylinux2014_x86_64", "--implementation", "cp", "--python-version", "3.12",
     "--only-binary=:all:", *DEPENDANCES],
    check=True,
)
(PKG / "app").mkdir()
for m in MODULES_APP:
    shutil.copy(SRC_APP / m, PKG / "app" / m)
shutil.copy(SRC_LAMBDAS / "traiter_soumission.py", PKG / "traiter_soumission.py")

ZIP.unlink(missing_ok=True)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(PKG.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            z.write(f, f.relative_to(PKG).as_posix())
print(f"✔ {ZIP} ({ZIP.stat().st_size // 1024 // 1024} Mo)")
