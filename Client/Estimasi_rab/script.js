// --- Global Variable Declarations ---
let form;
let submitButton;
let messageDiv;
let grandTotalAmount;
let lingkupPekerjaanSelect;
let sipilTablesWrapper;
let meTablesWrapper;
let currentResetButton;
let categorizedPrices = {};
let pendingStoreCodes = [];
let approvedStoreCodes = [];
let lastRejectedSubmission = null;

// --- Helper Functions ---
const formatRupiah = (number) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(number);
const parseRupiah = (formattedString) => parseFloat(String(formattedString).replace(/Rp\s?|\./g, "").replace(/,/g, ".")) || 0;
const formatNumberWithSeparators = (num) => (num === null || isNaN(num)) ? '0' : new Intl.NumberFormat('id-ID').format(num);
const parseFormattedNumber = (str) => typeof str !== 'string' ? (Number(str) || 0) : (parseFloat(str.replace(/\./g, '')) || 0);

const populateJenisPekerjaanOptionsForNewRow = (rowElement) => {
    const category = rowElement.dataset.category;
    const scope = rowElement.dataset.scope;
    const searchInput = rowElement.querySelector(".jenis-pekerjaan-search-input");
    const hiddenSelect = rowElement.querySelector(".jenis-pekerjaan");
    const suggestionsList = rowElement.querySelector(".jenis-pekerjaan-suggestions");
    if (!searchInput || !hiddenSelect || !suggestionsList) return;
    let dataSource = (scope === "Sipil" && categorizedPrices.categorizedSipilPrices) ? categorizedPrices.categorizedSipilPrices : (scope === "ME" && categorizedPrices.categorizedMePrices) ? categorizedPrices.categorizedMePrices : {};
    const itemsInCategory = dataSource[category] || [];
    hiddenSelect.innerHTML = '<option value="">-- Pilih Jenis Pekerjaan --</option>';
    itemsInCategory.forEach(item => {
        const option = document.createElement("option");
        option.value = item["Jenis Pekerjaan"];
        option.textContent = item["Jenis Pekerjaan"];
        hiddenSelect.appendChild(option);
    });
    const removeListeners = (inputEl) => {
        if (inputEl._inputHandler) inputEl.removeEventListener("input", inputEl._inputHandler);
        if (inputEl._focusHandler) inputEl.removeEventListener("focus", inputEl._focusHandler);
        if (inputEl._blurHandler) inputEl.removeEventListener("blur", inputEl._blurHandler);
    };
    removeListeners(searchInput);
    searchInput._inputHandler = () => {
        const searchTerm = searchInput.value.toLowerCase();
        suggestionsList.innerHTML = "";
        const itemsToDisplay = searchTerm.length > 0 ? itemsInCategory.filter(item => item["Jenis Pekerjaan"].toLowerCase().includes(searchTerm)) : itemsInCategory;
        if (itemsToDisplay.length > 0) {
            itemsToDisplay.forEach(item => {
                const li = document.createElement("li");
                li.textContent = item["Jenis Pekerjaan"];
                li.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    searchInput.value = item["Jenis Pekerjaan"];
                    hiddenSelect.value = item["Jenis Pekerjaan"];
                    suggestionsList.classList.add("hidden");
                    autoFillPrices(hiddenSelect);
                });
                suggestionsList.appendChild(li);
            });
            suggestionsList.classList.remove("hidden");
        } else {
            suggestionsList.classList.add("hidden");
        }
    };
    searchInput.addEventListener("input", searchInput._inputHandler);
    searchInput._focusHandler = () => searchInput.dispatchEvent(new Event("input"));
    searchInput.addEventListener("focus", searchInput._focusHandler);
    searchInput._blurHandler = () => setTimeout(() => { if (!suggestionsList.contains(document.activeElement)) suggestionsList.classList.add("hidden"); }, 150);
    searchInput.addEventListener("blur", searchInput._blurHandler);
};

const autoFillPrices = (selectElement) => {
    const row = selectElement.closest("tr");
    const selectedJenisPekerjaan = selectElement.value;
    const currentLingkupPekerjaan = lingkupPekerjaanSelect.value;
    const currentCategory = row.closest(".boq-table-body").dataset.category;
    let dataSource = (currentLingkupPekerjaan === "Sipil") ? categorizedPrices.categorizedSipilPrices : categorizedPrices.categorizedMePrices;
    let selectedItem = dataSource?.[currentCategory]?.find(item => item["Jenis Pekerjaan"] === selectedJenisPekerjaan);
    if (selectedItem) {
        row.querySelector(".harga-material").value = formatNumberWithSeparators(selectedItem["Harga Material"]);
        row.querySelector(".harga-upah").value = formatNumberWithSeparators(selectedItem["Harga Upah"]);
        row.querySelector(".satuan").value = selectedItem["Satuan"];
    } else {
        row.querySelector(".harga-material").value = "0";
        row.querySelector(".harga-upah").value = "0";
        row.querySelector(".satuan").value = "Ls";
    }
    calculateTotalPrice(row.querySelector(".volume"));
};

const createBoQRow = (category, scope) => {
    const row = document.createElement("tr");
    row.classList.add("boq-item-row");
    row.dataset.category = category;
    row.dataset.scope = scope;
    row.innerHTML = `<td><span class="row-number"></span></td><td><div class="jenis-pekerjaan-wrapper"><input type="text" class="jenis-pekerjaan-search-input" placeholder="Cari Jenis Pekerjaan"><select class="jenis-pekerjaan hidden" name="Jenis_Pekerjaan_Item" required><option value="">-- Pilih --</option></select><ul class="jenis-pekerjaan-suggestions hidden"></ul></div></td><td><input type="text" class="satuan" name="Satuan_Item" required readonly /></td><td><input type="number" class="volume" name="Volume_Item" value="0.00" min="0" step="0.01" /></td><td><input type="text" class="harga-material" name="Harga_Material_Item" inputmode="numeric" required readonly /></td><td><input type="text" class="harga-upah" name="Harga_Upah_Item" inputmode="numeric" required readonly /></td><td><input type="text" class="total-material" disabled /></td><td><input type="text" class="total-upah" disabled /></td><td><input type="text" class="total-harga" disabled /></td><td><button type="button" class="delete-row-btn">Hapus</button></td>`;
    [row.querySelector(".volume"), row.querySelector(".harga-material"), row.querySelector(".harga-upah")].forEach(input => input.addEventListener("input", () => calculateTotalPrice(input)));
    row.querySelector(".delete-row-btn").addEventListener("click", () => { row.remove(); updateAllRowNumbersAndTotals(); });
    row.querySelector('.jenis-pekerjaan').addEventListener('change', (e) => autoFillPrices(e.target));
    return row;
};

const updateAllRowNumbersAndTotals = () => {
    document.querySelectorAll(".boq-table-body:not(.hidden)").forEach(tbody => {
        tbody.querySelectorAll(".boq-item-row").forEach((row, index) => {
            row.querySelector(".row-number").textContent = index + 1;
            calculateTotalPrice(row.querySelector(".volume"));
        });
        calculateSubTotal(tbody);
    });
    calculateGrandTotal();
};

const calculateSubTotal = (tbodyElement) => {
    let subTotal = 0;
    tbodyElement.querySelectorAll(".boq-item-row .total-harga").forEach(input => subTotal += parseRupiah(input.value));
    const subTotalAmountElement = tbodyElement.closest("table").querySelector(".sub-total-amount");
    if (subTotalAmountElement) subTotalAmountElement.textContent = formatRupiah(subTotal);
};

function calculateTotalPrice(inputElement) {
    const row = inputElement.closest("tr");
    if (!row) return;
    const volume = parseFloat(row.querySelector("input.volume").value) || 0;
    const material = parseFormattedNumber(row.querySelector("input.harga-material").value);
    const upah = parseFormattedNumber(row.querySelector("input.harga-upah").value);
    const totalMaterial = volume * material;
    const totalUpah = volume * upah;
    row.querySelector("input.total-material").value = formatRupiah(totalMaterial);
    row.querySelector("input.total-upah").value = formatRupiah(totalUpah);
    row.querySelector("input.total-harga").value = formatRupiah(totalMaterial + totalUpah);
    calculateSubTotal(row.closest(".boq-table-body"));
    calculateGrandTotal();
}

const calculateGrandTotal = () => {
    let total = 0;
    document.querySelectorAll(".boq-table-body:not(.hidden) .total-harga").forEach(input => total += parseRupiah(input.value));
    if (grandTotalAmount) grandTotalAmount.textContent = formatRupiah(total);
};

const populateFormWithHistory = (data) => {
    console.log("Populating form with rejected data:", data);
    form.reset();
    document.querySelectorAll(".boq-table-body").forEach(tbody => tbody.innerHTML = "");
    for (const key in data) {
        if (data.hasOwnProperty(key)) {
            const elementName = key.replace(/_/g, " ");
            const element = document.getElementsByName(elementName)[0];
            if (element) {
                element.value = (element.type === 'date' && data[key]) ? new Date(data[key]).toISOString().split('T')[0] : data[key];
                if (key === 'Lingkup Pekerjaan') {
                    lingkupPekerjaanSelect.value = data[key];
                    lingkupPekerjaanSelect.dispatchEvent(new Event('change'));
                }
            }
        }
    }
    setTimeout(() => {
        for (let i = 1; i <= 50; i++) {
            if (data[`Jenis_Pekerjaan_${i}`]) {
                const category = data[`Kategori_Pekerjaan_${i}`];
                const scope = data.Lingkup_Pekerjaan;
                const targetTbody = document.querySelector(`.boq-table-body[data-category="${category}"][data-scope="${scope}"]`);
                if (targetTbody) {
                    const newRow = createBoQRow(category, scope);
                    targetTbody.appendChild(newRow);
                    newRow.querySelector('.jenis-pekerjaan-search-input').value = data[`Jenis_Pekerjaan_${i}`];
                    newRow.querySelector('.jenis-pekerjaan').value = data[`Jenis_Pekerjaan_${i}`];
                    newRow.querySelector('.satuan').value = data[`Satuan_Item_${i}`];
                    newRow.querySelector('.volume').value = data[`Volume_Item_${i}`] || 0.00;
                    populateJenisPekerjaanOptionsForNewRow(newRow);
                    newRow.querySelector('.harga-material').value = formatNumberWithSeparators(data[`Harga_Material_Item_${i}`]);
                    newRow.querySelector('.harga-upah').value = formatNumberWithSeparators(data[`Harga_Upah_Item_${i}`]);
                }
            }
        }
        updateAllRowNumbersAndTotals();
        messageDiv.innerHTML = "Data revisi telah dimuat. Silakan lakukan perubahan dan klik 'Kirim' jika sudah selesai.";
        messageDiv.style.display = 'block';
        messageDiv.style.backgroundColor = '#007bff';
        messageDiv.style.color = 'white';
    }, 500);
};

async function handleFormSubmit() {
    // ▼▼▼ PERUBAHAN UTAMA: URL SERVER RENDER ANDA ▼▼▼
    const PYTHON_API_BASE_URL = "https://bnm-application.onrender.com";
    
    const cabangValue = form.elements['Cabang']?.value;
    const lokasiValue = form.elements['Lokasi']?.value;
    if (!cabangValue || !lokasiValue) {
        messageDiv.textContent = `Error: 'Cabang' dan 'Lokasi' wajib diisi.`;
        messageDiv.style.display = "block";
        messageDiv.style.backgroundColor = "#dc3545";
        return;
    }
    const currentStoreCode = String(lokasiValue).toUpperCase();
    if (approvedStoreCodes.map(code => String(code).toUpperCase()).includes(currentStoreCode)) {
        messageDiv.textContent = `Error: Kode toko ${currentStoreCode} sudah pernah diajukan dan disetujui.`;
        messageDiv.style.display = "block";
        messageDiv.style.backgroundColor = "#dc3545";
        return;
    }
    if (pendingStoreCodes.map(code => String(code).toUpperCase()).includes(currentStoreCode) && (!lastRejectedSubmission || currentStoreCode !== String(lastRejectedSubmission.Lokasi).toUpperCase())) {
        messageDiv.textContent = `Error: Kode toko ${currentStoreCode} sudah memiliki pengajuan yang sedang direview.`;
        messageDiv.style.display = "block";
        messageDiv.style.backgroundColor = "#ffc107";
        messageDiv.style.color = "black";
        return;
    }
    messageDiv.textContent = "Mengirim data...";
    messageDiv.style.display = "block";
    messageDiv.style.backgroundColor = '#007bff';
    submitButton.disabled = true;
    try {
        const formData = new FormData(form);
        const formDataToSend = {};
        formData.forEach((value, key) => {
            if (!key.includes('_Item')) {
                formDataToSend[key.replace(/ /g, '_')] = value;
            }
        });
        formDataToSend["Email_Pembuat"] = sessionStorage.getItem('loggedInUserEmail') || '';
        formDataToSend["Lokasi"] = currentStoreCode;
        let itemCounter = 0;
        document.querySelectorAll(".boq-table-body:not(.hidden) .boq-item-row").forEach(row => {
            const jenisPekerjaanInput = row.querySelector(".jenis-pekerjaan");
            if (jenisPekerjaanInput && jenisPekerjaanInput.value) {
                itemCounter++;
                formDataToSend[`Kategori_Pekerjaan_${itemCounter}`] = row.dataset.category;
                formDataToSend[`Jenis_Pekerjaan_${itemCounter}`] = jenisPekerjaanInput.value;
                formDataToSend[`Satuan_Item_${itemCounter}`] = row.querySelector(".satuan").value;
                formDataToSend[`Volume_Item_${itemCounter}`] = parseFloat(row.querySelector(".volume").value) || 0;
                formDataToSend[`Harga_Material_Item_${itemCounter}`] = parseFormattedNumber(row.querySelector(".harga-material").value);
                formDataToSend[`Harga_Upah_Item_${itemCounter}`] = parseFormattedNumber(row.querySelector(".harga-upah").value);
                formDataToSend[`Total_Material_Item_${itemCounter}`] = parseRupiah(row.querySelector(".total-material").value);
                formDataToSend[`Total_Upah_Item_${itemCounter}`] = parseRupiah(row.querySelector(".total-upah").value);
                formDataToSend[`Total_Harga_Item_${itemCounter}`] = parseRupiah(row.querySelector(".total-harga").value);
            }
        });
        if (itemCounter === 0) {
            throw new Error("Tidak ada item pekerjaan yang ditambahkan. Formulir tidak bisa dikirim.");
        }
        formDataToSend["Grand_Total"] = parseRupiah(grandTotalAmount.textContent);
        const response = await fetch(`${PYTHON_API_BASE_URL}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formDataToSend),
        });
        const data = await response.json();
        console.log("Response from Python backend:", data);
        if (!response.ok) throw new Error(data.message || 'Submission failed.');
        messageDiv.textContent = data.message || "Data berhasil terkirim! Anda akan diarahkan ke Beranda.";
        messageDiv.style.backgroundColor = "#28a745";
        setTimeout(() => { window.location.href = '../Homepage/index.html'; }, 2500);
    } catch (error) {
        console.error("Error submitting form:", error);
        messageDiv.textContent = "Error: " + error.message;
        messageDiv.style.backgroundColor = "#dc3545";
    } finally {
        submitButton.disabled = false;
    }
}

async function initializePage() {
    form = document.getElementById("form");
    submitButton = document.getElementById("submit-button");
    messageDiv = document.getElementById("message");
    grandTotalAmount = document.getElementById("grand-total-amount");
    lingkupPekerjaanSelect = document.getElementById("lingkup_pekerjaan");
    sipilTablesWrapper = document.getElementById("sipil-tables-wrapper");
    meTablesWrapper = document.getElementById("me-tables-wrapper");
    currentResetButton = form.querySelector("button[type='reset']");

    lingkupPekerjaanSelect.disabled = true;
    messageDiv.textContent = 'Memuat data, mohon tunggu...';
    messageDiv.style.display = 'block';
    messageDiv.style.backgroundColor = '#007bff';
    messageDiv.style.color = 'white';

    // ▼▼▼ PERUBAHAN UTAMA: URL SERVER RENDER ANDA ▼▼▼
    const PYTHON_API_BASE_URL = "https://bnm-application.onrender.com";
    const userEmail = sessionStorage.getItem('loggedInUserEmail');

    if (userEmail) {
        try {
            const checkUrl = `${PYTHON_API_BASE_URL}/check_status?email=${encodeURIComponent(userEmail)}`;
            const response = await fetch(checkUrl);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to check status');
            console.log("User submissions response:", result);
            if (result.last_rejected_data) {
                lastRejectedSubmission = result.last_rejected_data;
                messageDiv.innerHTML = `Ditemukan data pengajuan yang ditolak untuk kode toko <strong>${lastRejectedSubmission.Lokasi}</strong>. Masukkan kode toko yang sama untuk memuat ulang data.`;
            } else {
                 messageDiv.style.display = 'none';
            }
            if (result.active_codes) {
                pendingStoreCodes = result.active_codes.pending || [];
                approvedStoreCodes = result.active_codes.approved || [];
            }
        } catch (error) {
            console.error("Gagal memeriksa status pengajuan:", error);
            messageDiv.textContent = "Gagal memuat status pengajuan terakhir. Error: " + error.message;
            messageDiv.style.backgroundColor = '#dc3545';
        }
    }
    
    document.getElementById('lokasi')?.addEventListener('input', function() {
        const currentStoreCode = this.value.toUpperCase();
        if (lastRejectedSubmission && currentStoreCode === String(lastRejectedSubmission.Lokasi).toUpperCase()) {
            if (confirm("Data pengajuan yang ditolak untuk kode toko ini ditemukan. Apakah Anda ingin memuat ulang data tersebut untuk direvisi?")) {
                populateFormWithHistory(lastRejectedSubmission);
            }
        }
    });

    const APPS_SCRIPT_DATA_URL = "https://script.google.com/macros/s/AKfycbx2rtKmaZBb_iRBRL-DOemjVhAp3GaCwsthtwtfdtvdtuO2bRVlmONboB8wE-CZU7Hc/exec";
    try {
        const response = await fetch(APPS_SCRIPT_DATA_URL);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        categorizedPrices = await response.json();
        console.log("Data harga berhasil dimuat.");
        lingkupPekerjaanSelect.disabled = false;
        if (!lastRejectedSubmission) {
             messageDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading price data:', error);
        messageDiv.textContent = 'Gagal memuat data harga. Mohon muat ulang halaman.';
        messageDiv.style.display = 'block';
    }

    document.querySelectorAll(".add-row-btn").forEach(button => {
        button.addEventListener("click", () => {
            const category = button.dataset.category;
            const scope = button.dataset.scope;
            const targetTbody = document.querySelector(`.boq-table-body[data-category="${category}"][data-scope="${scope}"]`);
            if (targetTbody) {
                const newRow = createBoQRow(category, scope);
                targetTbody.appendChild(newRow);
                populateJenisPekerjaanOptionsForNewRow(newRow);
                updateAllRowNumbersAndTotals();
            }
        });
    });

    lingkupPekerjaanSelect.addEventListener("change", (event) => {
        const selectedScope = event.target.value;
        sipilTablesWrapper.classList.toggle("hidden", selectedScope !== 'Sipil');
        meTablesWrapper.classList.toggle("hidden", selectedScope !== 'ME');
        document.querySelectorAll(".boq-table-body").forEach(tbody => {
            if (tbody.dataset.scope !== selectedScope) tbody.innerHTML = "";
        });
        if (selectedScope) {
            document.querySelectorAll(`.boq-table-body[data-scope="${selectedScope}"]`).forEach((tbody) => {
                if (tbody.children.length === 0) {
                    const newRow = createBoQRow(tbody.dataset.category, selectedScope);
                    tbody.appendChild(newRow);
                    populateJenisPekerjaanOptionsForNewRow(newRow);
                }
            });
        }
        updateAllRowNumbersAndTotals();
    });

    currentResetButton.addEventListener("click", () => {
        if (confirm("Apakah Anda yakin ingin mengulang dan mengosongkan semua isian form?")) {
            window.location.reload();
        }
    });

    submitButton.addEventListener("click", function(e) {
        e.preventDefault();
        handleFormSubmit();
    });
}

window.addEventListener("pageshow", () => {
    initializePage();
});