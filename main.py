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


def cleanup_fajlok(egyedi_id: str, eredeti_fajlnev: str, kesleletes_masodperc: int = 3600):
    time.sleep(kesleletes_masodperc)

    zip_utvonal = f"kesz_zipek/{egyedi_id}.zip"
    feltoltott_fajl = f"feltoltott_zenek/{eredeti_fajlnev}"

    if os.path.exists(zip_utvonal):
        os.remove(zip_utvonal)
        print(f"--- ZIP törölve: {zip_utvonal} ---")

    if os.path.exists(feltoltott_fajl):
        os.remove(feltoltott_fajl)
        print(f"--- Feltöltött fájl törölve: {feltoltott_fajl} ---")

    feldolgozas_allapot.pop(egyedi_id, None)


def run_demucs(file_path: str, egyedi_id: str, modell: str = "htdemucs"):
    print(f"--- AI INDÍTÁSA: {file_path} | Modell: {modell} | ID: {egyedi_id} ---")

    feldolgozas_allapot[egyedi_id] = "folyamatban"

    env = os.environ.copy()
    env["TORCHAUDIO_BACKEND"] = "soundfile"

    parancs = ["python", "-m", "demucs", "--name", modell, file_path, "--out", "szetvalasztott_zenek"]
    eredmeny = subprocess.run(parancs, text=True, env=env)

    if eredmeny.returncode != 0:
        print("--- HIBA AZ AI FUTÁSÁBAN! ---")
        feldolgozas_allapot[egyedi_id] = "hiba"
        return

    # A Demucs a FÁJLNÉV alapján hozza létre a mappát, nem az egyedi ID alapján
    # Ezért az eredeti fájlnévből (timestamp nélkül) kell keresni
    fajlnev_kiterjesztes_nelkul = os.path.splitext(os.path.basename(file_path))[0]

    # Megkeressük melyik modell mappa jött létre
    demucs_kimenet_mappa = None
    for modell_mappa in os.listdir("szetvalasztott_zenek"):
        lehetseges = f"szetvalasztott_zenek/{modell_mappa}/{fajlnev_kiterjesztes_nelkul}"
        if os.path.exists(lehetseges) and len(os.listdir(lehetseges)) > 0:
            demucs_kimenet_mappa = lehetseges
            print(f"--- Kimenet mappa megtalálva: {demucs_kimenet_mappa} ---")
            break

    if demucs_kimenet_mappa is None:
        print(f"--- HIBA: Nem találom a kimenet mappát ---")
        feldolgozas_allapot[egyedi_id] = "hiba"
        return

    # A ZIP neve az egyedi ID — így nem keveredik össze régi feldolgozásokkal
    zip_cel_utvonal = f"kesz_zipek/{egyedi_id}"
    shutil.make_archive(zip_cel_utvonal, 'zip', demucs_kimenet_mappa)
    feldolgozas_allapot[egyedi_id] = "kesz"
    print(f"--- KÉSZ: {zip_cel_utvonal}.zip ---")

    cleanup_thread = threading.Thread(
        target=cleanup_fajlok,
        args=(egyedi_id, os.path.basename(file_path), 3600),
        daemon=True
    )
    cleanup_thread.start()



@app.on_event("startup")
async def startup_cleanup():
    """Indításkor törli az 1 óránál régebbi ideiglenes fájlokat."""
    now = time.time()
    torolve = 0

    for mappa in ["kesz_zipek", "feltoltott_zenek"]:
        if os.path.exists(mappa):
            for f in os.listdir(mappa):
                fpath = f"{mappa}/{f}"
                if os.path.getmtime(fpath) < now - 3600:
                    os.remove(fpath)
                    print(f"--- Startup cleanup: {fpath} törölve ---")
                    torolve += 1

    if torolve > 0:
        print(f"--- Startup cleanup: {torolve} régi fájl törölve ---")
    else:
        print("--- Startup cleanup: nincs törölnivaló ---")

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

    # Egyedi ID = fájlnév + timestamp — minden feltöltés egyedi lesz
    nev_resz, kiterjesztes = os.path.splitext(file.filename)
    timestamp = int(time.time())
    egyedi_fajlnev = f"{nev_resz}_{timestamp}{kiterjesztes}"
    egyedi_id = f"{nev_resz}_{timestamp}"

    file_location = f"feltoltott_zenek/{egyedi_fajlnev}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    feldolgozas_allapot[egyedi_id] = "folyamatban"
    background_tasks.add_task(run_demucs, file_location, egyedi_id, modell)

    # Visszaküldjük az egyedi ID-t — a frontend ezt figyeli
    return {
        "uzenet": "Sikeres feltoltes!",
        "fajl_neve": egyedi_id,
        "modell": modell
    }


@app.get("/status/{egyedi_id}")
def check_status(egyedi_id: str):
    # Egyedi ID alapján keresünk ZIP-et — nem lesz félreértés régi fájlokkal
    zip_utvonal = f"kesz_zipek/{egyedi_id}.zip"
    if os.path.exists(zip_utvonal):
        return {
            "status": "kesz",
            "letoltes_url": f"/download/{egyedi_id}"
        }

    allapot = feldolgozas_allapot.get(egyedi_id, "folyamatban")
    return {"status": allapot}


@app.get("/download/{egyedi_id}")
def download_file(egyedi_id: str):
    zip_utvonal = f"kesz_zipek/{egyedi_id}.zip"
    if os.path.exists(zip_utvonal):
        def iterfile():
            with open(zip_utvonal, "rb") as f:
                yield from f
        return StreamingResponse(
            iterfile(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={egyedi_id}_stems.zip"}
        )
    return {"hiba": "A fajl meg nem keszult el vagy nem talalhato!"}