from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import shutil
import os
import subprocess
import time
import threading

app = FastAPI(title="Demucs Zene Szétválasztó API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("feltoltott_zenek", exist_ok=True)
os.makedirs("szetvalasztott_zenek", exist_ok=True)
os.makedirs("kesz_zipek", exist_ok=True)

feldolgozas_allapot = {}

TAMOGATOTT_MODELLEK = ["htdemucs", "htdemucs_6s"]


def cleanup_fajlok(fajlnev_kiterjesztes_nelkul: str, eredeti_fajlnev: str, kesleletes_masodperc: int = 3600):
    time.sleep(kesleletes_masodperc)

    zip_utvonal = f"kesz_zipek/{fajlnev_kiterjesztes_nelkul}.zip"
    feltoltott_fajl = f"feltoltott_zenek/{eredeti_fajlnev}"

    if os.path.exists(zip_utvonal):
        os.remove(zip_utvonal)
        print(f"--- 🗑️ ZIP törölve: {zip_utvonal} ---")

    if os.path.exists(feltoltott_fajl):
        os.remove(feltoltott_fajl)
        print(f"--- 🗑️ Feltöltött fájl törölve: {feltoltott_fajl} ---")

    feldolgozas_allapot.pop(eredeti_fajlnev, None)


def run_demucs(file_path: str, eredeti_fajlnev: str, modell: str = "htdemucs"):
    print(f"--- AI INDÍTÁSA: {file_path} | Modell: {modell} ---")

    feldolgozas_allapot[eredeti_fajlnev] = "folyamatban"

    env = os.environ.copy()
    env["TORCHAUDIO_BACKEND"] = "soundfile"

    parancs = ["python", "-m", "demucs", "--name", modell, file_path, "--out", "szetvalasztott_zenek"]

    eredmeny = subprocess.run(parancs, text=True, env=env)

    if eredmeny.returncode != 0:
        print("--- ❌ HIBA AZ AI FUTÁSÁBAN! ---")
        feldolgozas_allapot[eredeti_fajlnev] = "hiba"
        return

    fajlnev_kiterjesztes_nelkul = os.path.splitext(eredeti_fajlnev)[0]

    demucs_kimenet_mappa = f"szetvalasztott_zenek/{modell}/{fajlnev_kiterjesztes_nelkul}"
    zip_cel_utvonal = f"kesz_zipek/{fajlnev_kiterjesztes_nelkul}"

    if os.path.exists(demucs_kimenet_mappa) and len(os.listdir(demucs_kimenet_mappa)) > 0:
        print(f"--- ZIP CSOMAGOLÁS... ---")
        shutil.make_archive(zip_cel_utvonal, 'zip', demucs_kimenet_mappa)
        feldolgozas_allapot[eredeti_fajlnev] = "kesz"
        print(f"--- KÉSZ: {zip_cel_utvonal}.zip ---")

        cleanup_thread = threading.Thread(
            target=cleanup_fajlok,
            args=(fajlnev_kiterjesztes_nelkul, eredeti_fajlnev, 3600),
            daemon=True
        )
        cleanup_thread.start()

    else:
        print(f"--- ❌ HIBA: A kimenet mappa üres: {demucs_kimenet_mappa} ---")
        feldolgozas_allapot[eredeti_fajlnev] = "hiba"


@app.get("/")
def home():
    return {"uzenet": "A backend szerver sikeresen elindult!"}


@app.post("/upload/")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    modell: str = Form(default="htdemucs")
):
    if modell not in TAMOGATOTT_MODELLEK:
        return {"hiba": f"Ismeretlen modell: {modell}. Valassz: {TAMOGATOTT_MODELLEK}"}

    file_location = f"feltoltott_zenek/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    feldolgozas_allapot[file.filename] = "folyamatban"
    background_tasks.add_task(run_demucs, file_location, file.filename, modell)

    return {
        "uzenet": "Sikeres feltoltes! Az AI megkezdte a feldolgozast.",
        "fajl_neve": file.filename,
        "modell": modell
    }


@app.get("/status/{fajlnev}")
def check_status(fajlnev: str):
    fajlnev_kiterjesztes_nelkul = os.path.splitext(fajlnev)[0]
    zip_utvonal = f"kesz_zipek/{fajlnev_kiterjesztes_nelkul}.zip"

    if os.path.exists(zip_utvonal):
        return {
            "status": "kesz",
            "letoltes_url": f"/download/{fajlnev_kiterjesztes_nelkul}"
        }

    allapot = feldolgozas_allapot.get(fajlnev, "folyamatban")
    return {"status": allapot}


@app.get("/download/{fajl_azonosito}")
def download_file(fajl_azonosito: str):
    zip_utvonal = f"kesz_zipek/{fajl_azonosito}.zip"
    if os.path.exists(zip_utvonal):
        def iterfile():
            with open(zip_utvonal, "rb") as f:
                yield from f
        return StreamingResponse(
            iterfile(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={fajl_azonosito}_stems.zip"}
        )
    return {"hiba": "A fajl meg nem keszult el vagy nem talalhato!"}