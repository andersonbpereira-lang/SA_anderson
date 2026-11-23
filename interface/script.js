
"use strict";

// ==========================================
// HOSPITALCARE - SISTEMA DE GESTÃO
// ==========================================

// Acesso demonstrativo
const DEMO_USER = "admin";
const DEMO_PASSWORD = "hospital123";

// Persistência centralizada na API Flask/SQLite.
let patients = [];
let appointments = [];
let toastTimer;

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.erro || "Falha na comunicação com o servidor.");
    return body;
}
async function loadData() {
    const data = await api("/api/dados");
    patients = data.patients || [];
    appointments = data.appointments || [];
    renderAll();
}
function handleError(error) {
    console.error(error);
    notify(error.message || "Ocorreu um erro inesperado.");
}

// Elementos principais
const $ = (id) => document.getElementById(id);


// ==========================================
// NOTIFICAÇÕES
// ==========================================

function notify(message) {
    const toast = $("toast");

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

// ==========================================
// LOGIN
// ==========================================

$("togglePassword").addEventListener("click", () => {
    const password = $("password");

    password.type =
        password.type === "password" ? "text" : "password";
});

$("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        await api("/api/login", { method: "POST", body: JSON.stringify({
            username: $("username").value.trim(), password: $("password").value
        }) });
        $("loginError").textContent = "";
        await loadData();
        $("loginScreen").classList.add("hidden");
        $("appScreen").classList.remove("hidden");
        notify("Acesso demonstrativo iniciado.");
    } catch (error) { $("loginError").textContent = error.message; }
});

$("logoutBtn").addEventListener("click", () => {
    $("appScreen").classList.add("hidden");
    $("loginScreen").classList.remove("hidden");

    $("loginForm").reset();
    notify("Sessão encerrada.");
});

// ==========================================
// NAVEGAÇÃO
// ==========================================

const sections = {
    dashboard: "dashboardSection",
    patients: "patientsSection",
    triage: "triageSection",
    queue: "queueSection"
};

const titles = {
    dashboard: "Painel",
    patients: "Pacientes",
    triage: "Triagem",
    queue: "Fila de atendimento"
};

function navigate(section) {
    if (!sections[section]) return;

    Object.values(sections).forEach(id => {
        $(id).classList.add("hidden");
    });

    $(sections[section]).classList.remove("hidden");

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.section === section
        );
    });

    $("pageTitle").textContent = titles[section];

    renderAll();
}

document.querySelectorAll(".nav-item").forEach(button => {
    button.addEventListener("click", () => {
        navigate(button.dataset.section);
    });
});

// ==========================================
// MODAL DE PACIENTES
// ==========================================

function openPatientModal() {
    $("patientModal").classList.remove("hidden");
}

function closePatientModal() {
    $("patientModal").classList.add("hidden");
    $("patientForm").reset();
}

$("newPatientBtn").addEventListener("click", openPatientModal);
$("tableNewPatient").addEventListener("click", openPatientModal);
$("patientsNewBtn").addEventListener("click", openPatientModal);
$("closeModal").addEventListener("click", closePatientModal);
$("cancelModal").addEventListener("click", closePatientModal);

// Fechar modal clicando fora dele
$("patientModal").addEventListener("click", (event) => {
    if (event.target === $("patientModal")) {
        closePatientModal();
    }
});

// ==========================================
// CADASTRAR PACIENTE
// ==========================================

$("patientForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = $("patientName").value.trim();
    const age = Number($("patientAge").value);
    const weight = Number($("patientWeight").value);
    const height = Number($("patientHeight").value);
    if (name.length < 3 || !Number.isInteger(age) || age < 0 || age > 120 ||
        !Number.isFinite(weight) || weight < 0.5 || weight > 400 ||
        !Number.isFinite(height) || height < 0.3 || height > 2.6) {
        notify("Confira nome, idade, peso e altura.");
        return;
    }
    try {
        await api("/api/pacientes", { method: "POST", body: JSON.stringify({
            name, age, weight, height, sex: $("patientSex").value,
            blood: $("patientBlood").value,
            allergies: $("patientAllergies").value.trim() || "nenhuma"
        }) });
        closePatientModal();
        await loadData();
        notify("Paciente cadastrado no SQLite.");
    } catch (error) { handleError(error); }
});

// ==========================================
// CÁLCULO DO IMC
// ==========================================

function calculateBMI(weight, height) {
    if (!height || height <= 0) return "—";

    return (weight / (height * height)).toFixed(1);
}

// ==========================================
// LOCALIZAR PACIENTE
// ==========================================

function getPatient(patientId) {
    return patients.find(patient => String(patient.id) === String(patientId));
}

// ==========================================
// STATUS DO ATENDIMENTO
// ==========================================

function getPatientStatus(patientId) {
    const records = appointments.filter(
        item => String(item.patientId) === String(patientId)
    );

    if (records.some(item => item.status === "active")) {
        return "Em atendimento";
    }

    if (records.some(item => item.status === "waiting")) {
        return "Aguardando";
    }

    if (records.length > 0) {
        return "Finalizado";
    }

    return "Sem atendimento";
}

function statusClass(status) {
    if (status === "Aguardando") return "waiting";
    if (status === "Em atendimento") return "active";
    if (status === "Finalizado") return "finished";

    return "";
}

// ==========================================
// TABELA DE PACIENTES
// ==========================================

function renderPatients() {
    const search = $("searchInput").value.toLowerCase().trim();

    const filtered = patients.filter(patient => {
        return patient.name.toLowerCase().includes(search) ||
            patient.id.toLowerCase().includes(search);
    });

    const html = filtered.map(patient => {
        const status = getPatientStatus(patient.id);

        return `
            <tr>
                <td>${patient.id}</td>
                <td><strong>${escapeHTML(patient.name)}</strong></td>
                <td>${patient.age} anos</td>
                <td>${patient.weight} kg</td>
                <td>${patient.height.toFixed(2)} m</td>
                <td>${calculateBMI(patient.weight, patient.height)}</td>
                <td>${escapeHTML(patient.blood)}</td>
                <td>${escapeHTML(patient.allergies)}</td>
                <td>
                    <span class="status ${statusClass(status)}">
                        ${status}
                    </span>
                </td>
                <td>
                    <button class="table-btn delete"
                        data-delete-patient="${patient.id}">
                        Excluir
                    </button>
                </td>
            </tr>
        `;
    }).join("");

    const empty = `
        <tr>
            <td colspan="10" style="text-align:center;padding:25px">
                Nenhum paciente encontrado.
            </td>
        </tr>
    `;

    $("patientsTable").innerHTML = html || empty;
    $("patientsTable2").innerHTML = html || empty;
}

$("searchInput").addEventListener("input", renderPatients);

// ==========================================
// SEGURANÇA DE TEXTO HTML
// ==========================================

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return entities[character];
    });
}

// ==========================================
// EXCLUIR PACIENTE
// ==========================================

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-patient]");

    if (!button) return;

    const id = button.dataset.deletePatient;

    const hasActive = appointments.some(item =>
        String(item.patientId) === String(id) &&
        (item.status === "waiting" || item.status === "active")
    );

    if (hasActive) {
        notify("Finalize ou cancele o atendimento antes de excluir.");
        return;
    }

    if (!confirm("Deseja realmente excluir este paciente?")) {
        return;
    }

    try {
        await api("/api/pacientes/" + encodeURIComponent(id), { method: "DELETE" });
        await loadData();
        notify("Paciente excluído.");
    } catch (error) { handleError(error); }
});

// ==========================================
// SELEÇÃO DE PACIENTE NA TRIAGEM
// ==========================================

function renderPatientOptions() {
    const select = $("patientSelect");
    const selected = select.value;

    select.innerHTML = `
        <option value="">Selecione um paciente</option>
        ${patients.map(patient => `
            <option value="${patient.id}">
                ${escapeHTML(patient.name)} - ${patient.id}
            </option>
        `).join("")}
    `;

    if (patients.some(patient => patient.id === selected)) {
        select.value = selected;
    }
}

// ==========================================
// CONTROLE DA DOR
// ==========================================

$("pain").addEventListener("input", () => {
    $("painValue").textContent = $("pain").value;
});

// ==========================================
// REGISTRAR ATENDIMENTO
// ==========================================

$("triageForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const patientId = $("patientSelect").value;
    if (!getPatient(patientId)) {
        notify("Selecione um paciente cadastrado.");
        return;
    }
    const oxygen = Number($("oxygen").value);
    const heartRate = Number($("heartRate").value);
    const temperature = Number($("temperature").value);
    const systolic = Number($("systolic").value);
    const diastolic = Number($("diastolic").value);
    const pain = Number($("pain").value);
    const complaint = $("complaint").value.trim();
    if (complaint.length < 3 || oxygen < 0 || oxygen > 100 ||
        heartRate < 20 || heartRate > 300 || temperature < 30 || temperature > 45 ||
        systolic < 30 || systolic > 300 || diastolic < 20 || diastolic > 200) {
        notify("Confira a queixa e os valores informados.");
        return;
    }
    try {
        await api("/api/atendimentos", { method: "POST", body: JSON.stringify({
            patientId: Number(patientId), complaint, injury: $("injury").value,
            pain, oxygen, heartRate, temperature, systolic, diastolic,
            conscious: $("conscious").checked
        }) });
        $("triageForm").reset();
        $("painValue").textContent = "0";
        $("oxygen").value = 98;
        $("heartRate").value = 80;
        $("temperature").value = 36.5;
        $("systolic").value = 120;
        $("diastolic").value = 80;
        $("conscious").checked = true;
        await loadData();
        navigate("queue");
        notify("Atendimento simulado registrado.");
    } catch (error) { handleError(error); }
});

$("cancelTriage").addEventListener("click", () => {
    $("triageForm").reset();
    $("painValue").textContent = "0";
    navigate("dashboard");
});

// ==========================================
// PRIORIDADES VISUAIS
// ==========================================

const priorityInfo = {
    blue: {
        label: "Azul — Não urgente",
        color: "#4385c5",
        order: 5
    },
    red: {
        label: "Vermelha — Imediata",
        color: "#e5484d",
        order: 1
    },
    orange: {
        label: "Laranja — Alta",
        color: "#ed8b32",
        order: 2
    },
    yellow: {
        label: "Amarela — Moderada",
        color: "#e7bb39",
        order: 3
    },
    green: {
        label: "Verde — Baixa",
        color: "#35a66f",
        order: 4
    }
};

function getWaitingAppointments() {
    return appointments
        .filter(item => item.status === "waiting")
        .sort((a, b) => {
            const priorityA = priorityInfo[a.priority]?.order || 5;
            const priorityB = priorityInfo[b.priority]?.order || 5;

            if (priorityA !== priorityB) {
                return priorityA - priorityB;
            }

            return new Date(a.createdAt) - new Date(b.createdAt);
        });
}

// ==========================================
// FILA POR GRAVIDADE
// ==========================================

function renderSeverity() {
    const waiting = getWaitingAppointments();

    const priorities = ["red", "orange", "yellow", "green", "blue"];

    $("severityList").innerHTML = priorities.map(priority => {
        const info = priorityInfo[priority];

        const count = waiting.filter(
            item => item.priority === priority
        ).length;

        return `
            <div class="severity-row">
                <div class="severity-label">
                    <span class="severity-dot"
                        style="background:${info.color}"></span>
                    ${info.label}
                </div>
                <strong>${count}</strong>
            </div>
        `;
    }).join("");
}

// ==========================================
// PRÓXIMO PACIENTE
// ==========================================

function renderNextPatient() {
    const next = getWaitingAppointments()[0];

    if (!next) {
        $("nextPatient").innerHTML = `
            <span class="empty-icon">♙</span>
            <p>Nenhum paciente aguardando.</p>
        `;
        return;
    }

    const patient = getPatient(next.patientId);
    const priority = priorityInfo[next.priority];

    $("nextPatient").innerHTML = `
        <div class="avatar">${patient ? escapeHTML(patient.name.substring(0, 2).toUpperCase()) : "HC"}</div>
        <strong>${patient ? escapeHTML(patient.name) : "Paciente"}</strong>
        <p>${next.id}</p>
        <span class="priority-tag" style="color:${priority.color}">
            ${priority.label}
        </span>
    `;
}

// ==========================================
// FILA COMPLETA
// ==========================================

function renderQueue() {
    const sorted = [...appointments].sort((a, b) => {
        const order = {
            red: 1,
            orange: 2,
            yellow: 3,
            green: 4,
            blue: 5
        };

        if (a.status === "waiting" && b.status === "waiting") {
            return (order[a.priority] || 5) -
                (order[b.priority] || 5) ||
                new Date(a.createdAt) - new Date(b.createdAt);
        }

        const statusOrder = {
            active: 1,
            waiting: 2,
            finished: 3
        };

        return statusOrder[a.status] - statusOrder[b.status];
    });

    if (!sorted.length) {
        $("queueList").innerHTML = `
            <div class="next-patient">
                <span class="empty-icon">☷</span>
                <p>Nenhum atendimento registrado.</p>
            </div>
        `;
        return;
    }

    $("queueList").innerHTML = sorted.map(item => {
        const patient = getPatient(item.patientId);
        const priority = priorityInfo[item.priority];

        const statusLabels = {
            waiting: "Aguardando",
            active: "Em atendimento",
            finished: "Finalizado"
        };

        let actions = "";

        if (item.status === "waiting") {
            actions = `
                <button class="table-btn"
                    data-start="${item.id}">
                    Iniciar
                </button>
            `;
        } else if (item.status === "active") {
            actions = `
                <button class="table-btn"
                    data-finish="${item.id}">
                    Finalizar
                </button>
            `;
        }

        return `
            <div class="queue-card"
                style="--priority:${priority.color}">

                <div>
                    <h4>
                        ${patient ? escapeHTML(patient.name) : "Paciente não encontrado"}
                    </h4>
                    <p>ID: ${item.id}</p>
                    <p>Queixa: ${escapeHTML(item.complaint)}</p>
                    <p>Registro: ${new Date(item.createdAt).toLocaleString("pt-BR")}</p>
                    <p style="color:${priority.color};font-weight:700;margin-top:7px">
                        ${priority.label}
                    </p>
                </div>

                <div class="queue-actions">
                    <span class="status ${statusClass(
                        statusLabels[item.status]
                    )}">
                        ${statusLabels[item.status]}
                    </span>
                    ${actions}
                </div>
            </div>
        `;
    }).join("");
}

// ==========================================
// INICIAR E FINALIZAR ATENDIMENTO
// ==========================================

document.addEventListener("click", async (event) => {
    const startButton = event.target.closest("[data-start]");
    const finishButton = event.target.closest("[data-finish]");

    if (startButton) {
        const item = appointments.find(
            appointment => appointment.id === startButton.dataset.start
        );

        if (!item || item.status !== "waiting") return;

        const anotherActive = appointments.some(
            appointment => appointment.status === "active"
        );

        if (anotherActive) {
            notify("Já existe um atendimento ativo.");
            return;
        }

        try {
            await api("/api/atendimentos/" + item.id, {
                method: "PATCH", body: JSON.stringify({ status: "active" })
            });
            await loadData();
            notify("Atendimento iniciado.");
        } catch (error) { handleError(error); }
    }

    if (finishButton) {
        const item = appointments.find(
            appointment => appointment.id === finishButton.dataset.finish
        );

        if (!item || item.status !== "active") return;

        try {
            await api("/api/atendimentos/" + item.id, {
                method: "PATCH", body: JSON.stringify({ status: "finished" })
            });
            await loadData();
            notify("Atendimento finalizado.");
        } catch (error) { handleError(error); }
    }
});

// ==========================================
// INDICADORES DO PAINEL
// ==========================================

function renderStats() {
    $("totalPatients").textContent = patients.length;

    $("waitingPatients").textContent =
        appointments.filter(item => item.status === "waiting").length;

    $("activePatients").textContent =
        appointments.filter(item => item.status === "active").length;

    $("finishedPatients").textContent =
        appointments.filter(item => item.status === "finished").length;

    $("queueCount").textContent =
        appointments.filter(item => item.status === "waiting").length;
}

// ==========================================
// ATUALIZAR SISTEMA
// ==========================================

function renderAll() {
    renderPatients();
    renderPatientOptions();
    renderStats();
    renderSeverity();
    renderNextPatient();
    renderQueue();
}

// ==========================================
// BOTÕES DE NAVEGAÇÃO RÁPIDA
// ==========================================

function openTriage() {
    if (patients.length === 0) {
        notify("Cadastre um paciente antes de registrar a triagem.");
        openPatientModal();
        return;
    }

    navigate("triage");
}

$("newPatientBtn").addEventListener("contextmenu", event => {
    event.preventDefault();
    openPatientModal();
});

// Inicialização: a interface deve ser aberta pelo servidor Flask.
loadData().catch(handleError);
const clearDemoButton = $("clearDemoBtn");
if (clearDemoButton) {
    clearDemoButton.addEventListener("click", async () => {
        if (!confirm("Isso apagará todos os registros fictícios. Continuar?")) return;
        try {
            await api("/api/dados-demo", { method: "DELETE" });
            await loadData();
            notify("Dados de demonstração removidos.");
        } catch (error) { handleError(error); }
    });
}
