# Demucs AI 🎧 – Zenei Sávszétválasztó

Professzionális, AI-alapú zenei sávszétválasztó webalkalmazás, amely teljesen lokálisan (offline) fut. A [Meta Demucs](https://github.com/facebookresearch/demucs) neurális hálózat segítségével egy MP3 vagy WAV fájlból különálló sávokat (ének, dob, basszus, egyéb) választ szét, veszteségmentes WAV formátumban.

> 🎓 BBTE Közgazdaságtudományi Kar – Gazdasági Informatika szakdolgozat

---

## Funkciók

- 🎵 Drag & drop vagy kattintásos fájlfeltöltés
- 🧠 Két modell közötti választás (4 sáv vagy 6 sáv)
- 🔒 100%-os adatbiztonság – semmi nem kerül fel a netre
- 📥 Veszteségmentes WAV kimenet ZIP-be csomagolva
- ⏱️ Feldolgozási idő kijelzése
- ❌ Teljes körű hibakezelés

---

## Rendszerkövetelmények

- Windows 10 / 11 (64-bit)
- Python 3.10 vagy újabb
- Minimum 8 GB RAM (ajánlott 16 GB)
- Minimum 5 GB szabad lemezterület
- Internetkapcsolat (csak az első futtatáshoz, a modellek letöltéséhez)

---

## Telepítés

### 1. Python telepítése

Ha még nincs Python telepítve, töltsd le a [python.org](https://www.python.org/downloads/) oldalról.

> ⚠️ Fontos: a telepítő első képernyőjén jelöld be az **"Add Python to PATH"** opciót!

### 2. Csomagok telepítése

Nyiss parancssort abban a mappában ahol a `main.py` található, és futtasd:

```bash
pip install fastapi uvicorn demucs soundfile
```

A telepítés néhány percet vehet igénybe (PyTorch + Demucs mérete miatt).

---

## Indítás

### 1. Backend szerver indítása

```bash
uvicorn main:app --reload
```

Ha ezt látod, a szerver fut:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

> ⚠️ Ne zárd be ezt az ablakot, amíg a szoftvert használod!

### 2. Frontend megnyitása

Nyisd meg duplán az `index.html` fájlt – automatikusan megnyílik a böngészőben.

---

## Használat

1. Húzd rá a zenefájlt a feltöltési zónára (MP3 vagy WAV)
2. Válaszd ki a modellt:
   - **htdemucs** – 4 sáv: ének, dob, basszus, egyéb
   - **htdemucs_6s** – 6 sáv: + gitár, zongora (lassabb)
3. Kattints a **Feldolgozás Indítása** gombra
4. Várj 1–10 percet (hardverfüggő)
5. Töltsd le a ZIP-et – benne a WAV sávok

> Az első futtatáskor a modellek letöltődnek az internetről (~1–2 GB). Ez csak egyszer szükséges.

---

## Fájlstruktúra

```
demucs/
├── main.py          # FastAPI backend
├── index.html       # Frontend
├── script.js        # JavaScript logika
├── style.css        # Stílusok
├── feltoltott_zenek/     # Ideiglenes (auto-cleanup 1h után)
├── szetvalasztott_zenek/ # Ideiglenes (auto-cleanup 1h után)
└── kesz_zipek/           # Ideiglenes (auto-cleanup 1h után)
```

---

## Technológiák

| Réteg | Technológia |
|---|---|
| AI Motor | Meta Demucs (htdemucs / htdemucs_6s) |
| Backend | Python, FastAPI, uvicorn |
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Hangfeldolgozás | soundfile, torchaudio |

---

## Leállítás

A parancssori ablakban nyomj **CTRL+C**-t a szerver leállításához.
