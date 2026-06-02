const API_BASE = "http://127.0.0.1:8000";

let progressInterval;
let feldolgozasKezdete = null;
const POLLING_TIMEOUT_MS = 10 * 60 * 1000;

const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (!file.name.match(/\.(mp3|wav)$/i)) {
            showError("Csak MP3 vagy WAV fájl fogadható el!");
            return;
        }
        const dt = new DataTransfer();
        dt.items.add(file);
        document.getElementById('fileInput').files = dt.files;
        fileSelected();
    }
});

function fileSelected() {
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const submitBtn = document.getElementById('submitBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');
    const statusDiv = document.getElementById('status');
    const progressContainer = document.getElementById('progressContainer');
    const audioPreview = document.getElementById('audioPreview');
    const modelSelector = document.getElementById('modelSelector');
    const processingTime = document.getElementById('processingTime');

    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const meret = (file.size / (1024 * 1024)).toFixed(1);
        fileLabel.innerText = `✅ ${file.name} (${meret} MB)`;

        audioPreview.src = URL.createObjectURL(file);
        audioPreview.style.display = "block";

        modelSelector.style.display = "block";

        document.getElementById('modelSelect').onchange = function() {
            const hint = document.getElementById('modelHint');
            hint.style.display = this.value === 'htdemucs_6s' ? 'block' : 'none';
        };

        submitBtn.style.display = "block";
        downloadBtn.style.display = "none";
        resetBtn.style.display = "none";
        progressContainer.style.display = "none";
        processingTime.style.display = "none";
        statusDiv.innerText = "";
        statusDiv.style.color = "#ffb74d";
    }
}

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('status');
    const submitBtn = document.getElementById('submitBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const modelSelect = document.getElementById('modelSelect');
    const modelSelector = document.getElementById('modelSelector');

    if (fileInput.files.length === 0) return;

    const valasztottModell = modelSelect.value;
    const modellNev = modelSelect.options[modelSelect.selectedIndex].text;

    const formData = new FormData();
    const fajlNeve = fileInput.files[0].name;
    formData.append("file", fileInput.files[0]);
    formData.append("modell", valasztottModell);

    submitBtn.style.display = "none";
    modelSelector.style.display = "none";
    progressContainer.style.display = "block";

    feldolgozasKezdete = Date.now();

    statusDiv.innerText = `🧠 ${modellNev} – A neurális hálózat dolgozik... 🎧`;
    statusDiv.style.color = "#ffb74d";

    let percent = 0;
    progressFill.style.width = "0%";
    progressFill.innerText = "0%";
    progressFill.style.backgroundColor = "#03dac6";

    progressInterval = setInterval(() => {
        if (percent < 95) {
            let increment = Math.random() * 3;
            if (percent > 70) increment = Math.random() * 1;
            percent += increment;
            if (percent > 95) percent = 95;
            progressFill.style.width = percent + "%";
            progressFill.innerText = Math.floor(percent) + "%";
        }
    }, 1000);

    try {
        await fetch(`${API_BASE}/upload/`, { method: "POST", body: formData });
        startPolling(fajlNeve);
    } catch (error) {
        clearInterval(progressInterval);
        showError("Hálózat vagy szerver hiba történt! Elindítottad a backendet?");
    }
}


function startPolling(filename) {
    const statusDiv = document.getElementById('status');
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');
    const progressFill = document.getElementById('progressFill');

    let consecutiveErrors = 0;
    const pollingStart = Date.now();

    const interval = setInterval(async () => {

        if (Date.now() - pollingStart > POLLING_TIMEOUT_MS) {
            clearInterval(interval);
            clearInterval(progressInterval);
            showError("A feldolgozás túl sokáig tartott. Próbáld újra kisebb fájllal!");
            resetBtn.style.display = "inline-block";
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/status/${filename}`);
            const result = await response.json();

            consecutiveErrors = 0;

            if (result.status === "hiba") {
                clearInterval(interval);
                clearInterval(progressInterval);
                showError("Az AI feldolgozás során hiba lépett fel. Próbáld újra!");
                resetBtn.style.display = "inline-block";
                return;
            }

            if (result.status === "kesz") {
                clearInterval(interval);
                clearInterval(progressInterval);

                progressFill.style.width = "100%";
                progressFill.innerText = "100% - Kész!";
                progressFill.style.backgroundColor = "#bb86fc";

                const elteltMasodperc = Math.floor((Date.now() - feldolgozasKezdete) / 1000);
                const percek = Math.floor(elteltMasodperc / 60);
                const masodpercek = elteltMasodperc % 60;
                const idoSzoveg = percek > 0
                    ? `${percek} perc ${masodpercek} másodperc`
                    : `${masodpercek} másodperc`;

                const processingTime = document.getElementById('processingTime');
                processingTime.innerText = `⏱️ Feldolgozási idő: ${idoSzoveg}`;
                processingTime.style.display = "block";

                statusDiv.innerText = "A sávok szétválasztása sikeresen befejeződött! 🎉";
                statusDiv.style.color = "#03dac6";

                downloadBtn.href = `${API_BASE}${result.letoltes_url}`;
                downloadBtn.style.display = "inline-block";
                resetBtn.style.display = "inline-block";
            }
        } catch (error) {
            consecutiveErrors++;
            console.log(`Szerver nem válaszol... (${consecutiveErrors}/3)`);

            if (consecutiveErrors >= 3) {
                clearInterval(interval);
                clearInterval(progressInterval);
                showError("A szerver nem válaszol. Elindítottad a backendet?");
                resetBtn.style.display = "inline-block";
            }
        }
    }, 3000);
}

function showError(uzenet) {
    const statusDiv = document.getElementById('status');
    const progressFill = document.getElementById('progressFill');
    const progressContainer = document.getElementById('progressContainer');

    statusDiv.innerText = "❌ " + uzenet;
    statusDiv.style.color = "#cf6679";

    if (progressContainer.style.display !== "none") {
        progressFill.style.backgroundColor = "#cf6679";
        progressFill.innerText = "Hiba";
    }
}

function resetUI() {
    document.getElementById('fileInput').value = "";
    document.getElementById('fileLabel').innerText = "Húzd ide a fájlt, vagy kattints a tallózáshoz";
    document.getElementById('submitBtn').style.display = "none";
    document.getElementById('downloadBtn').style.display = "none";
    document.getElementById('resetBtn').style.display = "none";
    document.getElementById('progressContainer').style.display = "none";
    document.getElementById('status').innerText = "";
    document.getElementById('status').style.color = "#ffb74d";
    document.getElementById('modelSelector').style.display = "none";
    document.getElementById('processingTime').style.display = "none";

    const audioPreview = document.getElementById('audioPreview');
    audioPreview.style.display = "none";
    audioPreview.pause();
    audioPreview.src = "";

    const progressFill = document.getElementById('progressFill');
    progressFill.style.width = "0%";
    progressFill.innerText = "0%";
    progressFill.style.backgroundColor = "#03dac6";

    feldolgozasKezdete = null;
}