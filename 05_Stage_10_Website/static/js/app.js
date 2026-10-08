"use strict";
/* Price estimator: loads the options, validates input, calls /api/predict and shows the result. */

const form = document.getElementById("vehicle-form");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");

const FORM_SELECTS = ["manufacturer", "category", "color", "fuel_type", "gearbox", "drive_wheels", "wheel", "doors", "leather"];
const DOOR_LABELS = { "2-3": "2-3 doors", "4-5": "4-5 doors", ">5": "More than 5 doors" };
const money = (value) => "$" + Math.round(value).toLocaleString("en-US");
const plain = (value) => (Number(value) >= 10000 ? Number(value).toLocaleString("en-US") : String(Number(value)));
let modelStats = {};

function fillSelect(select, values, placeholder, labels = {}) {
    select.replaceChildren();
    if (placeholder) {
        const first = document.createElement("option");
        first.value = "";
        first.textContent = placeholder;
        select.appendChild(first);
    }
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = labels[value] || value;
        select.appendChild(option);
    });
}

async function loadForm() {
    try {
        const [optRes, modelRes] = await Promise.all([fetch("/api/options"), fetch("/api/models")]);
        if (!optRes.ok || !modelRes.ok) throw new Error("bad response");
        const options = await optRes.json();
        const summary = await modelRes.json();

        FORM_SELECTS.forEach((id) => fillSelect(document.getElementById(id), options[id], "Select...", id === "doors" ? DOOR_LABELS : {}));
        summary.models.forEach((m) => (modelStats[m.key] = m));

        const [minYear, maxYear] = options.year_range;
        const year = document.getElementById("prod_year");
        year.min = minYear;
        year.max = maxYear;
        document.getElementById("year-help").textContent = `Between ${minYear} and ${maxYear}`;
        document.getElementById("year-from").textContent = minYear;
        document.getElementById("year-to").textContent = maxYear;

        const modelSelect = document.getElementById("model");
        fillSelect(modelSelect, summary.models.map((m) => m.key), null,
            Object.fromEntries(summary.models.map((m) => [m.key, m.name + (m.final ? " (final model)" : "")])));
        modelSelect.value = summary.final_model;
    } catch (err) {
        showFormError("The page could not load its options from the server. Please refresh the page.");
        submitBtn.disabled = true;
    }
}

// ------------------------------------------------------------------ validation
const NUMBER_RULES = {
    prod_year: { label: "Production year", integer: true, required: true },
    engine_volume: { label: "Engine volume", required: true },
    cylinders: { label: "Cylinders", integer: true, required: true },
    mileage: { label: "Mileage", required: true },
    airbags: { label: "Airbags", integer: true, required: true },
    levy: { label: "Customs levy", required: false },
    asking_price: { label: "Asking price", required: false },
};

function clearErrors() {
    formError.hidden = true;
    form.querySelectorAll(".error").forEach((el) => (el.textContent = ""));
    form.querySelectorAll(".invalid").forEach((el) => el.classList.remove("invalid"));
}

function setError(field, message) {
    const slot = form.querySelector(`[data-error-for="${field}"]`);
    const input = document.getElementById(field);
    if (slot) slot.textContent = message;
    if (input) input.classList.add("invalid");
}

function showFormError(message) {
    formError.textContent = message;
    formError.hidden = false;
}

function validateClient() {
    const errors = {};
    Object.entries(NUMBER_RULES).forEach(([id, rule]) => {
        const input = document.getElementById(id);
        const raw = input.value.trim();
        if (raw === "") {
            if (rule.required) errors[id] = `${rule.label} is required.`;
            return;
        }
        const value = Number(raw);
        if (!Number.isFinite(value)) errors[id] = `${rule.label} must be a number.`;
        else if (rule.integer && !Number.isInteger(value)) errors[id] = `${rule.label} must be a whole number.`;
        else if (value < Number(input.min) || value > Number(input.max)) {
            errors[id] = `${rule.label} must be between ${plain(input.min)} and ${plain(input.max)}.`;
        }
    });
    FORM_SELECTS.forEach((id) => {
        if (document.getElementById(id).value === "") errors[id] = "Please select an option.";
    });
    return errors;
}

function applyErrors(errors) {
    clearErrors();
    const fields = [];
    Object.entries(errors).forEach(([field, message]) => {
        if (field === "_form") showFormError(message);
        else setError(field, message);
        if (document.getElementById(field)) fields.push(document.getElementById(field));
    });
    // focus the first wrong field in the order it appears on the page
    fields.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
    if (fields.length) fields[0].focus();
}

// ------------------------------------------------------------------ submit
function collectPayload() {
    const data = {};
    new FormData(form).forEach((value, key) => (data[key] = value));
    data.turbo = document.getElementById("turbo").checked;
    return data;
}

async function submitForm(event) {
    event.preventDefault();
    const clientErrors = validateClient();
    if (Object.keys(clientErrors).length) {
        applyErrors(clientErrors);
        return;
    }
    clearErrors();
    submitBtn.disabled = true;
    submitBtn.textContent = "Estimating...";
    try {
        const response = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(collectPayload()),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            applyErrors(data.errors || { _form: "The estimate could not be produced." });
            return;
        }
        showResult(data);
    } catch (err) {
        showFormError("Could not reach the server. Check that the application is running and try again.");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Estimate price";
    }
}

// ------------------------------------------------------------------ result
function countUp(el, target) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = money(target); return; }
    const t0 = performance.now();
    const tick = (t) => {
        const p = Math.min(1, (t - t0) / 800);
        el.textContent = money(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}

function placeRange(p, asking) {
    const values = [p.range_low, p.range_high, p.price_usd].concat(asking ? [asking] : []);
    const lo = Math.min(...values) * 0.85, hi = Math.max(...values) * 1.08, span = hi - lo;
    const at = (v) => ((v - lo) / span) * 100 + "%";
    const fill = document.getElementById("range-fill");
    fill.style.left = at(p.range_low);
    fill.style.width = ((p.range_high - p.range_low) / span) * 100 + "%";
    const est = document.getElementById("marker-est");
    est.style.left = at(p.price_usd);
    document.getElementById("marker-est-label").textContent = "Estimate " + money(p.price_usd);
    const ask = document.getElementById("marker-ask");
    ask.hidden = !asking;
    if (asking) {
        ask.style.left = at(asking);
        document.getElementById("marker-ask-label").textContent = "Asking " + money(asking);
    }
    document.getElementById("range-low").textContent = money(p.range_low);
    document.getElementById("range-high").textContent = money(p.range_high);
}

function showResult(data) {
    const p = data.prediction;
    document.getElementById("res-vehicle").textContent = data.vehicle;
    countUp(document.getElementById("res-price"), p.price_usd);
    document.getElementById("res-range").textContent = `Likely range: ${money(p.range_low)} to ${money(p.range_high)}`;
    document.getElementById("res-model").textContent =
        `Estimated with ${p.model_name}. The range is where the real price fell for ${Math.round(p.range_coverage * 100)}% of the test cars.`;
    const check = data.asking_price_check;
    document.getElementById("result-empty").hidden = true;
    document.getElementById("result").hidden = false;
    placeRange(p, check ? check.asking_price : null);

    const notices = document.getElementById("res-notices");
    notices.replaceChildren();
    data.notices.forEach((text) => {
        const line = document.createElement("div");
        line.textContent = text;
        notices.appendChild(line);
    });
    notices.hidden = data.notices.length === 0;

    const asking = document.getElementById("res-asking");
    asking.hidden = !check;
    if (check) {
        const diff = Math.abs(check.difference_pct).toFixed(1);
        const direction = check.difference_pct >= 0 ? "above" : "below";
        const verdict = {
            below: "This is lower than the likely range, so the listing may be a good price or may hide a problem with the car.",
            within: "This is inside the likely range, so the asking price looks reasonable.",
            above: "This is higher than the likely range, so the asking price may be too high.",
        }[check.position];
        document.getElementById("res-asking-text").textContent =
            `The asking price of ${money(check.asking_price)} is ${diff}% ${direction} the estimate. ${verdict}`;
    }

    const maxPrice = Math.max(...data.model_comparison.map((r) => r.price));
    const bars = document.getElementById("model-bars");
    bars.replaceChildren();
    data.model_comparison.forEach((row) => {
        const info = modelStats[row.key];
        const wrap = document.createElement("div");
        wrap.className = "mbar" + (row.final ? " final" : "");
        const label = document.createElement("div");
        const name = document.createElement("b");
        name.textContent = row.name;
        const small = document.createElement("small");
        small.textContent = `R² ${info.test_r2.toFixed(3)} · error ${money(info.test_mae)}`;
        label.append(name, small);
        const track = document.createElement("div");
        track.className = "track";
        const fill = document.createElement("i");
        fill.style.width = "0%";
        track.appendChild(fill);
        const val = document.createElement("div");
        val.className = "val";
        val.textContent = money(row.price);
        wrap.append(label, track, val);
        bars.appendChild(wrap);
        requestAnimationFrame(() => requestAnimationFrame(() => (fill.style.width = (row.price / maxPrice) * 100 + "%")));
    });
}

// ------------------------------------------------------------------ wiring
function fillExample() {
    Object.entries(window.EXAMPLE).forEach(([key, value]) => {
        const el = document.getElementById(key);
        if (!el) return;
        if (el.type === "checkbox") el.checked = Boolean(value);
        else el.value = value;
    });
    clearErrors();
}

form.addEventListener("submit", submitForm);
document.getElementById("example-btn").addEventListener("click", fillExample);
document.getElementById("reset-btn").addEventListener("click", () => {
    form.reset();
    clearErrors();
    document.getElementById("model").value = Object.keys(modelStats).find((k) => modelStats[k].final) || "";
    document.getElementById("result").hidden = true;
    document.getElementById("result-empty").hidden = false;
});

loadForm();
