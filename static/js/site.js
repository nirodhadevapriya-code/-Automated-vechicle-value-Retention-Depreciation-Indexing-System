"use strict";
/* Site behaviour: header, animated hero, charts built from /api/insights, anatomy pins,
 * car cards, model section, presentation deck and contact form. */

const FMT = {
    int: (v) => Math.round(v).toLocaleString("en-US"),
    usd: (v) => "$" + Math.round(v).toLocaleString("en-US"),
    pct0: (v) => Math.round(v * 100) + "%",
    pct1: (v) => (v * 100).toFixed(1) + "%",
    r2: (v) => Number(v).toFixed(3),
};
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const get = (obj, path) => path.split(".").reduce((a, k) => (a == null ? a : a[k]), obj);
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const PALETTE = ["#2f6bff", "#12b5a6", "#ffb020", "#ff6b57", "#7c5cff", "#5ac8fa", "#4e8f6a", "#c0392b"];

// A real car used for the live example in the hero and the presentation.
window.EXAMPLE = {
    manufacturer: "TOYOTA", prod_year: 2014, category: "Sedan", color: "White", engine_volume: 2.5, cylinders: 4, turbo: false,
    fuel_type: "Petrol", gearbox: "Automatic", drive_wheels: "Front", wheel: "Left wheel", mileage: 98000, airbags: 8,
    doors: "4-5", leather: "Yes",
};

let INS = null;

// ------------------------------------------------------------------ header and menu
const header = $("#site-header");
const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 40);
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();
const menuBtn = $("#menu-toggle"), nav = $("#main-nav");
menuBtn.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", String(open));
    header.classList.toggle("scrolled", open || window.scrollY > 40);
});
$$("#main-nav a").forEach((a) => a.addEventListener("click", () => { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); onScroll(); }));

// ------------------------------------------------------------------ hero scene
function seeded(seed) { let s = seed; return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646; }

function ridge(rand, base, amp, step) {
    const pts = [[0, base]];
    for (let x = step; x < 1600; x += step) pts.push([x, base - rand() * amp]);
    pts.push([1600, base]);
    return "M" + pts.map((p) => p.join(",")).join(" L") + " L1600,700 L0,700 Z";
}
function pines(rand, base) {
    let d = "";
    for (let x = 10; x < 1600; x += 34 + rand() * 40) {
        const h = 40 + rand() * 70, w = 14 + rand() * 12;
        d += `M${x - w},${base} L${x},${base - h} L${x + w},${base} Z `;
    }
    return d;
}
function buildScene() {
    const r = seeded(11);
    const stars = Array.from({ length: 70 }, () => `<circle cx="${(r() * 1600).toFixed(0)}" cy="${(r() * 300).toFixed(0)}" r="${(0.6 + r() * 1.4).toFixed(1)}" fill="#fff"/>`).join("");
    const far = ridge(seeded(3), 470, 170, 90), mid = ridge(seeded(5), 520, 120, 70), trees = pines(seeded(9), 508);
    // each moving layer is its own element (two copies side by side) so the browser can slide it on the GPU
    const layer = (inner, dur, cls) => `<svg class="layer ${cls}" style="animation-duration:${dur}s" viewBox="0 0 3200 700" preserveAspectRatio="xMinYMax slice" aria-hidden="true"><g>${inner}</g><g transform="translate(1600,0)">${inner}</g></svg>`;
    const streaks = [18, 30, 42, 54, 66].map((top, i) => `<i class="streak" style="top:${top}%;animation-delay:${i * 0.35}s;width:${90 + i * 18}px"></i>`).join("");
    return `<svg class="scene-static" viewBox="0 0 1600 700" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
        <defs><radialGradient id="sun" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff2c4"/><stop offset=".35" stop-color="#ffb27a" stop-opacity=".9"/><stop offset="1" stop-color="#ff7a6b" stop-opacity="0"/></radialGradient></defs>
        <g class="stars">${stars}</g>
        <circle cx="1130" cy="440" r="230" fill="url(#sun)"/>
      </svg>
      <svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
        <linearGradient id="m1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a4a9c"/><stop offset="1" stop-color="#22285e"/></linearGradient>
        <linearGradient id="m2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2a73"/><stop offset="1" stop-color="#101a45"/></linearGradient></defs></svg>
      ${layer(`<path d="${far}" fill="url(#m1)" opacity=".9"/>`, 140, "l-far")}
      ${layer(`<path d="${mid}" fill="url(#m2)"/>`, 80, "l-mid")}
      ${layer(`<path d="${trees}" fill="#0a1030"/>`, 36, "l-trees")}
      <svg class="scene-static" viewBox="0 0 1600 700" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
        <rect x="0" y="500" width="1600" height="200" fill="#0a1030"/>
        <rect x="0" y="514" width="1600" height="186" fill="#161e3a"/>
        <rect x="0" y="514" width="1600" height="3" fill="#33426f"/>
      </svg>
      <div class="road-dashes"></div>${streaks}`;
}

function initHero() {
    $("#hero-scene").insertAdjacentHTML("afterbegin", buildScene());
    $("#hero-car").innerHTML = CarArt.svg("suv", "#4e8f6a", { spin: true, label: "Illustration of a green SUV driving" });
    $("#placeholder-car").innerHTML = CarArt.svg("sedan", "#9fb2d8", { label: "Illustration of a car" });

    // stop the motion while the hero is not on screen (saves battery and keeps the page smooth)
    new IntersectionObserver(([e]) => document.body.classList.toggle("hero-off", !e.isIntersecting), { threshold: 0.05 }).observe($("#home"));

    // optional real video: put a file at static/media/hero.mp4 and it fades in over the animation
    const video = $("#hero-video");
    if (video) {
        video.addEventListener("playing", () => video.classList.add("ready"));
        video.play().catch(() => {});
    }

    // rotating "our thinking" captions
    const thoughts = [
        "A fair price starts with the data, not the sales pitch.",
        "Age, equipment, engine and gear box explain most of a price. We measured how much.",
        "Every estimate comes with an honest range, because no model is exact.",
        "Explain first, predict second: you should see why a car costs what it does.",
    ];
    const text = $("#thought-text"), dots = $("#thought-dots");
    dots.innerHTML = thoughts.map(() => "<i></i>").join("");
    let i = 0, timer = null;
    const show = (n) => {
        i = n;
        text.classList.add("fade");
        setTimeout(() => { text.textContent = thoughts[i]; text.classList.remove("fade"); }, 350);
        $$("i", dots).forEach((d, k) => d.classList.toggle("on", k === i));
    };
    const start = () => { if (!reduceMotion) timer = setInterval(() => show((i + 1) % thoughts.length), 5600); };
    $$("i", dots).forEach((d, k) => d.classList.toggle("on", k === 0));
    start();
    const pause = $("#pause-btn");
    pause.addEventListener("click", () => {
        const paused = document.body.classList.toggle("paused");
        pause.setAttribute("aria-pressed", String(paused));
        pause.textContent = paused ? "Play motion" : "Pause motion";
        if (paused) { clearInterval(timer); timer = null; } else if (!timer) start();
    });
    if (reduceMotion) { document.body.classList.add("paused"); pause.textContent = "Play motion"; pause.setAttribute("aria-pressed", "true"); }
}

// ------------------------------------------------------------------ data binding and counters
function bindData() {
    $$("[data-k]").forEach((el) => {
        const v = get(INS, el.dataset.k);
        if (v != null) el.textContent = FMT[el.dataset.fmt || "int"](v);
    });
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        const target = get(INS, e.target.dataset.count), f = FMT[e.target.dataset.fmt || "int"];
        if (target == null) return;
        if (reduceMotion) { e.target.textContent = f(target); return; }
        const t0 = performance.now();
        const tick = (t) => {
            const p = Math.min(1, (t - t0) / 1400);
            e.target.textContent = f(target * (1 - Math.pow(1 - p, 3)));
            if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }), { threshold: 0.4 });
    $$("[data-count]").forEach((el) => io.observe(el));
}

// ------------------------------------------------------------------ anatomy (pins on the car)
function initAnatomy() {
    const box = $("#anatomy-car");
    box.innerHTML = CarArt.svg("sedan", "#3b7bff", { label: "Car with selectable factors" });
    const imp = Object.fromEntries(INS.importance.map((x) => [x.name, x.value]));
    const median = (arr, name) => arr.find((x) => x.name === name)?.median;
    const age = INS.age_price.series["All cars"], ages = INS.age_price.ages;
    const gearSorted = INS.gearbox.filter((g) => g.n > 100).sort((a, b) => b.median - a.median);
    const makesSorted = INS.makes.slice().sort((a, b) => b.median - a.median);
    const corr = Object.fromEntries(INS.corr.map((c) => [c.name, c.value]));
    const pins = [
        { key: "Age", x: 50, y: 24, fact: () => `A typical car loses value steadily with age: the median price is ${FMT.usd(age[ages.indexOf(8)])} at 8 years old, ${FMT.usd(age[ages.indexOf(12)])} at 12 years and ${FMT.usd(age[ages.indexOf(20)])} at 20 years.` },
        { key: "Body type", x: 24, y: 40, fact: () => `Body style matters: the median SUV/Jeep sells for ${FMT.usd(median(INS.body, "Jeep"))}, a sedan for ${FMT.usd(median(INS.body, "Sedan"))} and a hatchback for ${FMT.usd(median(INS.body, "Hatchback"))}.` },
        { key: "Airbags", x: 62, y: 36, fact: () => `On its own the number of airbags barely moves with price (correlation ${corr.Airbags}), yet scrambling it costs the model ${INS.importance_r2_drop.Airbags} of R². It matters mainly in combination with other factors.` },
        { key: "Gear box", x: 45, y: 58, fact: () => `${gearSorted[0].name} cars have the highest median price (${FMT.usd(gearSorted[0].median)}) and ${gearSorted[gearSorted.length - 1].name} cars the lowest (${FMT.usd(gearSorted[gearSorted.length - 1].median)}).` },
        { key: "Engine size", x: 80, y: 46, fact: () => `Bigger engines tend to cost more: correlation with price is ${corr["Engine size"]}, the strongest positive link among the numeric factors.` },
        { key: "Make", x: 90, y: 62, fact: () => `Among the ten most common makes the median price runs from ${FMT.usd(makesSorted[makesSorted.length - 1].median)} (${makesSorted[makesSorted.length - 1].name}) to ${FMT.usd(makesSorted[0].median)} (${makesSorted[0].name}).` },
        { key: "Fuel type", x: 15, y: 54, fact: () => `Diesel cars have a median price of ${FMT.usd(median(INS.fuel, "Diesel"))} against ${FMT.usd(median(INS.fuel, "Petrol"))} for petrol and ${FMT.usd(median(INS.fuel, "Hybrid"))} for hybrid, partly because diesel is common in large SUVs.` },
        { key: "Drive wheels", x: 71, y: 74, fact: () => { const d = Object.fromEntries(INS.drive.map((x) => [x.name, x.median])); return `Four-wheel-drive cars have a median price of ${FMT.usd(d["4x4"])}, front-wheel drive ${FMT.usd(d.Front)} and rear-wheel drive ${FMT.usd(d.Rear)}.`; } },
    ];
    const title = $("#pin-title"), share = $("#pin-share"), bar = $("#pin-bar"), fact = $("#pin-fact");
    const select = (p, btn) => {
        $$(".pin", box).forEach((b) => b.classList.toggle("active", b === btn));
        title.textContent = p.key;
        share.textContent = (imp[p.key] ?? 0).toFixed(1) + "%";
        bar.style.width = Math.min(100, (imp[p.key] ?? 0) * 1.8) + "%";
        fact.textContent = p.fact();
    };
    pins.forEach((p, n) => {
        const b = document.createElement("button");
        b.className = "pin"; b.type = "button"; b.textContent = n + 1; b.dataset.label = p.key;
        b.style.left = p.x + "%"; b.style.top = p.y + "%";
        b.setAttribute("aria-label", `${p.key}: show details`);
        b.addEventListener("click", () => select(p, b));
        box.appendChild(b);
    });
    select(pins[0], $(".pin", box));
}

// ------------------------------------------------------------------ charts
function chartDefaults() {
    Chart.defaults.font.family = '"Inter", "Segoe UI", system-ui, sans-serif';
    Chart.defaults.font.size = 12.5;
    Chart.defaults.color = "#5d687e";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.tooltip.backgroundColor = "#0b1220";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.maintainAspectRatio = false;
}
const GRID = { color: "rgba(16,26,58,.07)" };
const usdTick = (v) => "$" + (v >= 1000 ? v / 1000 + "k" : v);
const BODY_NAMES = { Jeep: "SUV / Jeep", Universal: "Estate", "Goods wagon": "Goods wagon", Microbus: "Microbus" };
const bodyName = (n) => BODY_NAMES[n] || n;

function initCharts() {
    chartDefaults();
    const imp = INS.importance.slice(0, 10);
    $("#cap-importance").textContent = `${imp[0].name}, ${imp[1].name.toLowerCase()} and ${imp[2].name.toLowerCase()} lead. Share of accuracy lost when each factor is scrambled.`;
    new Chart($("#ch-importance"), { type: "bar", data: { labels: imp.map((x) => x.name), datasets: [{ data: imp.map((x) => x.value), backgroundColor: imp.map((_, i) => i < 3 ? "#2f6bff" : "#9db8ff"), borderRadius: 8 }] },
        options: { indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.parsed.x.toFixed(1)}% of accuracy` } } }, scales: { x: { grid: GRID, ticks: { callback: (v) => v + "%" } }, y: { grid: { display: false }, ticks: { autoSkip: false } } } } });

    const FROM = 2; // start at age 8: the few cars younger than that are mostly premium models and distort the line
    const a = { ages: INS.age_price.ages.slice(FROM), series: Object.fromEntries(Object.entries(INS.age_price.series).map(([k, v]) => [k, v.slice(FROM)])) }, cols = { "All cars": "#0b1220", Petrol: "#2f6bff", Diesel: "#ff6b57", Hybrid: "#12b5a6" };
    $("#cap-age").textContent = `The median price drops from ${FMT.usd(a.series["All cars"][0])} at 8 years to ${FMT.usd(a.series["All cars"][a.ages.indexOf(20)])} at 20 years. Cars under 8 years old are few and mostly premium, so they are left out.`;
    new Chart($("#ch-age"), { type: "line", data: { labels: a.ages, datasets: Object.entries(a.series).map(([k, v]) => ({ label: k, data: v, borderColor: cols[k], backgroundColor: cols[k], borderWidth: k === "All cars" ? 3 : 2, pointRadius: 0, tension: .35, spanGaps: true, borderDash: k === "All cars" ? [] : [] })) },
        options: { interaction: { mode: "index", intersect: false }, plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${FMT.usd(c.parsed.y)}`, title: (i) => `${i[0].label} years old` } } }, scales: { x: { grid: { display: false }, title: { display: true, text: "Age in years" } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const body = INS.body.filter((b) => b.n >= 200);
    const hi = body.reduce((p, c) => (c.median > p.median ? c : p)), lo = body.reduce((p, c) => (c.median < p.median ? c : p));
    $("#cap-body").textContent = `${bodyName(hi.name)} has the highest median (${FMT.usd(hi.median)}), ${bodyName(lo.name)} the lowest (${FMT.usd(lo.median)}).`;
    new Chart($("#ch-body"), { type: "bar", data: { labels: body.map((b) => bodyName(b.name)), datasets: [{ data: body.map((b) => b.median), backgroundColor: PALETTE, borderRadius: 8 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${FMT.usd(c.parsed.y)} median`, afterLabel: (c) => ` ${FMT.int(body[c.dataIndex].n)} listings` } } }, scales: { x: { grid: { display: false }, ticks: { maxRotation: 40 } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const fuel = INS.fuel;
    $("#cap-fuel").textContent = `Diesel is the priciest of the common fuels (${FMT.usd(fuel.find((f) => f.name === "Diesel").median)}); gas-converted cars (LPG, CNG) sell for the least.`;
    new Chart($("#ch-fuel"), { type: "bar", data: { labels: fuel.map((f) => f.name), datasets: [{ data: fuel.map((f) => f.median), backgroundColor: ["#2f6bff", "#ff6b57", "#12b5a6", "#ffb020", "#7c5cff"], borderRadius: 8 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${FMT.usd(c.parsed.y)} median`, afterLabel: (c) => ` ${FMT.int(fuel[c.dataIndex].n)} listings` } } }, scales: { x: { grid: { display: false } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const w = INS.wheel, L = w["Left wheel"], R = w["Right-hand drive"];
    $("#cap-wheel").textContent = `Right-hand-drive cars are only ${FMT.pct0(R.n / (L.n + R.n))} of listings and sell for ${FMT.pct0(1 - R.median / L.median)} less (median).`;
    new Chart($("#ch-wheel"), { type: "bar", data: { labels: ["Left-hand drive", "Right-hand drive"], datasets: [{ data: [L.median, R.median], backgroundColor: ["#2f6bff", "#ffb020"], borderRadius: 10, barPercentage: .55 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${FMT.usd(c.parsed.y)} median`, afterLabel: (c) => ` ${FMT.int([L.n, R.n][c.dataIndex])} listings` } } }, scales: { x: { grid: { display: false } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const mk = INS.makes;
    const mHi = mk.reduce((p, c) => (c.median > p.median ? c : p)), mLo = mk.reduce((p, c) => (c.median < p.median ? c : p));
    $("#cap-makes").textContent = `Median price runs from ${FMT.usd(mLo.median)} (${mLo.name}) to ${FMT.usd(mHi.median)} (${mHi.name}). Hover a bar for the number of listings.`;
    new Chart($("#ch-makes"), { type: "bar", data: { labels: mk.map((m) => m.name), datasets: [{ data: mk.map((m) => m.median), backgroundColor: mk.map((_, i) => PALETTE[i % PALETTE.length]), borderRadius: 8 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${FMT.usd(c.parsed.y)} median`, afterLabel: (c) => ` ${FMT.int(mk[c.dataIndex].n)} listings, typical age ${mk[c.dataIndex].age} years` } } }, scales: { x: { grid: { display: false }, ticks: { maxRotation: 40 } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const h = INS.price_hist, labels = h.counts.map((_, i) => `$${h.edges[i] / 1000}–${h.edges[i + 1] / 1000}k`);
    const top = h.counts.indexOf(Math.max(...h.counts));
    $("#cap-hist").textContent = `Most listings are priced between ${FMT.usd(h.edges[top])} and ${FMT.usd(h.edges[top + 1])}; ${FMT.int(h.over_60k)} listings are above $60,000 and not shown.`;
    new Chart($("#ch-hist"), { type: "bar", data: { labels, datasets: [{ data: h.counts, backgroundColor: h.counts.map((_, i) => (i === top ? "#ffb020" : "#2f6bff")), borderRadius: 6, categoryPercentage: 1, barPercentage: .92 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${FMT.int(c.parsed.y)} listings` } } }, scales: { x: { grid: { display: false }, ticks: { maxRotation: 50 } }, y: { grid: GRID } } } });
}

// ------------------------------------------------------------------ cars gallery
function initCars() {
    const styles = [["Sedan", "sedan", "#2f6bff"], ["Jeep", "suv", "#4e8f6a"], ["Hatchback", "hatchback", "#ff6b57"], ["Minivan", "minivan", "#7c5cff"],
        ["Coupe", "coupe", "#ffb020"], ["Universal", "wagon", "#12b5a6"], ["Microbus", "van", "#34495e"], ["Pickup", "pickup", "#c0392b"]];
    const hexA = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
    $("#car-cards").innerHTML = styles.map(([name, type, colour]) => {
        const b = INS.body.find((x) => x.name === name);
        if (!b) return "";
        return `<article class="car-card" style="--tone:${hexA(colour, 0.14)}">
            ${CarArt.svg(type, colour, { label: bodyName(name) + " illustration" })}
            <h3>${bodyName(name)}</h3>
            <p class="sub">${FMT.int(b.n)} listings${b.n < 100 ? " (few, treat with care)" : ""}</p>
            <div class="price-tag">${FMT.usd(b.median)}<small>median price</small></div>
            <div class="facts"><span>Typical age ${b.age} yrs</span><span>${FMT.int(b.km)} km</span></div>
        </article>`;
    }).join("");
}

// ------------------------------------------------------------------ models
function initModels() {
    const copy = {
        xgboost: ["Boosted trees", "Builds many small decision trees one after another, each correcting the mistakes of the last. Built-in penalties stop it memorising rare cars."],
        lightgbm: ["Boosted trees, fast", "The same idea as XGBoost, but it groups values into bins first, so it trains very quickly. Almost as accurate here."],
        random_forest: ["Forest of trees", "Many independent trees each vote on the price. Steady and hard to overfit, but slightly less sharp than boosting."],
        ridge: ["Straight-line formula", "A weighted sum of the inputs with a brake on large weights. Simple and fast, but it cannot see how factors combine."],
    };
    const names = { xgboost: "XGBoost", lightgbm: "LightGBM", random_forest: "Random Forest", ridge: "Ridge Regression" };
    const models = INS.models.slice().sort((a, b) => b.cv_tuned - a.cv_tuned);
    $("#model-cards").innerHTML = models.map((m) => `<article class="model-card${m.final ? " final" : ""}">
        ${m.final ? '<span class="tag">Final model</span>' : ""}
        <h3>${names[m.key]}</h3><p class="fam">${copy[m.key][0]}</p><p>${copy[m.key][1]}</p>
        <dl><div><dt>Test R&sup2;</dt><dd>${m.test_r2.toFixed(3)}</dd></div><div><dt>Avg. error</dt><dd>${FMT.usd(m.mae)}</dd></div>
        <div><dt>CV R&sup2;</dt><dd>${m.cv_tuned.toFixed(3)}</dd></div><div><dt>Before tuning</dt><dd>${m.cv_base.toFixed(3)}</dd></div></dl></article>`).join("");

    new Chart($("#ch-models"), { type: "bar", data: { labels: models.map((m) => names[m.key]), datasets: [
        { label: "Before tuning", data: models.map((m) => m.cv_base), backgroundColor: "#b5c2dd", borderRadius: 8 },
        { label: "After tuning", data: models.map((m) => m.cv_tuned), backgroundColor: "#2f6bff", borderRadius: 8 }] },
        options: { plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(4)}` } } }, scales: { x: { grid: { display: false } }, y: { min: 0, max: 0.9, grid: GRID, title: { display: true, text: "Cross-validated R²" } } } } });

    const pts = INS.scatter.map(([x, y]) => ({ x, y })), max = 90000;
    new Chart($("#ch-scatter"), { type: "scatter", data: { datasets: [
        { label: "Test cars", data: pts, backgroundColor: "rgba(47,107,255,.45)", pointRadius: 3 },
        { label: "Perfect estimate", data: [{ x: 0, y: 0 }, { x: max, y: max }], type: "line", borderColor: "#ff6b57", borderWidth: 2, pointRadius: 0 }] },
        options: { plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (c) => ` Actual ${FMT.usd(c.parsed.x)}, estimated ${FMT.usd(c.parsed.y)}` } } }, scales: { x: { min: 0, max, grid: GRID, ticks: { callback: usdTick }, title: { display: true, text: "Actual price" } }, y: { min: 0, max, grid: GRID, ticks: { callback: usdTick }, title: { display: true, text: "Estimated price" } } } } });

    const eb = INS.error_band;
    $("#cap-error").textContent = `Average error in dollars by actual price. For cars under $3,000 the typical estimate is off by more than the car costs.`;
    new Chart($("#ch-error"), { type: "bar", data: { labels: eb.map((b) => [({ "under 3k": "Under $3k", "3k-8k": "$3k–8k", "8k-15k": "$8k–15k", "15k-30k": "$15k–30k", "over 30k": "Over $30k" })[b.band], `${FMT.int(b.n)} cars`]), datasets: [{ data: eb.map((b) => b.mae), backgroundColor: ["#ff6b57", "#ffb020", "#12b5a6", "#2f6bff", "#7c5cff"], borderRadius: 8 }] },
        options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` Average error ${FMT.usd(c.parsed.y)}`, afterLabel: (c) => ` Typical error ${FMT.pct0(eb[c.dataIndex].median_ape)} of the price` } } }, scales: { x: { grid: { display: false } }, y: { grid: GRID, ticks: { callback: usdTick } } } } });

    const ab = INS.ablation.slice().sort((a, b) => b.cv_r2 - a.cv_r2);
    new Chart($("#ch-ablation"), { type: "bar", data: { labels: ab.map((a) => a.name), datasets: [{ data: ab.map((a) => a.cv_r2), backgroundColor: ab.map((a) => (a.name.startsWith("All") ? "#2f6bff" : a.name.startsWith("Log") ? "#ff6b57" : "#9db8ff")), borderRadius: 8 }] },
        options: { indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` CV R² ${c.parsed.x.toFixed(4)}`, afterLabel: (c) => ` Test R² ${ab[c.dataIndex].test_r2.toFixed(4)}` } } }, scales: { x: { min: 0.5, max: 0.8, grid: GRID, title: { display: true, text: "Cross-validated R² (higher is better)" } }, y: { grid: { display: false }, ticks: { autoSkip: false } } } } });
}

// ------------------------------------------------------------------ presentation deck
function initDeck() {
    $$(".slide-art[data-car]").forEach((el) => { el.innerHTML = CarArt.svg(el.dataset.car, el.dataset.colour, { label: "" }); });
    $("#funnel").innerHTML = INS.funnel.map((f, i) => `<div><i style="width:${(f.n / INS.funnel[0].n) * 100}%"></i><span><b>${f.label}</b><b>${FMT.int(f.n)}</b></span></div>`).join("");
    const top = INS.importance.slice(0, 6), maxv = top[0].value;
    $("#slide-importance").innerHTML = top.map((t) => `<div><span>${t.name}</span><i style="width:${(t.value / maxv) * 100}%"></i><span>${t.value.toFixed(0)}%</span></div>`).join("");

    const viewport = $("#deck-viewport"), slides = $$(".slide", viewport), dots = $("#deck-dots"), count = $("#deck-count"), deck = $("#deck");
    let cur = 0;
    dots.innerHTML = slides.map((_, i) => `<button type="button" role="tab" aria-label="Slide ${i + 1}"></button>`).join("");
    const go = (n) => {
        cur = (n + slides.length) % slides.length;
        viewport.style.transform = `translateX(-${cur * 100}%)`;
        $$("button", dots).forEach((b, k) => { b.classList.toggle("on", k === cur); b.setAttribute("aria-selected", String(k === cur)); });
        count.textContent = `${cur + 1} / ${slides.length}`;
        slides.forEach((s, k) => s.setAttribute("aria-hidden", String(k !== cur)));
    };
    $$("button", dots).forEach((b, k) => b.addEventListener("click", () => go(k)));
    $("#deck-prev").addEventListener("click", () => go(cur - 1));
    $("#deck-next").addEventListener("click", () => go(cur + 1));
    deck.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight") { go(cur + 1); e.preventDefault(); }
        if (e.key === "ArrowLeft") { go(cur - 1); e.preventDefault(); }
    });
    const full = $("#deck-full");
    full.addEventListener("click", () => { if (document.fullscreenElement) document.exitFullscreen(); else deck.requestFullscreen?.(); });
    document.addEventListener("fullscreenchange", () => { full.textContent = document.fullscreenElement ? "Exit full screen" : "Full screen"; });
    $$("[data-close-fullscreen]").forEach((a) => a.addEventListener("click", () => { if (document.fullscreenElement) document.exitFullscreen(); }));
    go(0);
}

// ------------------------------------------------------------------ contact form (opens an email draft)
function initContact() {
    const form = $("#contact-form"), email = document.body.dataset.contactEmail || "";
    if (!email) $("#contact-note").textContent = "This opens a draft in your email program. Nothing is sent from this page. (The site owner can set the CONTACT_EMAIL setting to fill in the recipient.)";
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const name = $("#c-name").value.trim(), from = $("#c-email").value.trim(), msg = $("#c-message").value.trim(), errs = {};
        if (!name) errs["c-name"] = "Please enter your name.";
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(from)) errs["c-email"] = "Please enter a valid email address.";
        if (msg.length < 5) errs["c-message"] = "Please write a short message.";
        $$(".error", form).forEach((s) => (s.textContent = ""));
        $$("input, textarea", form).forEach((i) => i.classList.remove("invalid"));
        Object.entries(errs).forEach(([id, m]) => { $(`[data-error-for="${id}"]`).textContent = m; $("#" + id).classList.add("invalid"); });
        if (Object.keys(errs).length) { $("#" + Object.keys(errs)[0]).focus(); return; }
        const body = `${msg}\n\n${name} (${from})`;
        window.location.href = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent("AutoWorth project enquiry")}&body=${encodeURIComponent(body)}`;
    });
}

// ------------------------------------------------------------------ live example (hero chip and presentation demo)
function liveExample() {
    fetch("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(window.EXAMPLE) })
        .then((r) => r.json()).then((d) => {
            if (!d.success) throw new Error("example failed");
            const p = d.prediction, e = window.EXAMPLE, age = 2026 - e.prod_year;
            $(".chip-age strong").textContent = `${age} years`;
            $(".chip-km strong").textContent = `${FMT.int(e.mileage)} km`;
            $(".chip-engine strong").textContent = `${e.engine_volume.toFixed(1)} L`;
            $("#chip-live-price").textContent = FMT.usd(p.price_usd);
            $("#chip-live-range").textContent = `likely ${FMT.usd(p.range_low)} to ${FMT.usd(p.range_high)}`;
            $("#chip-live").hidden = false;
            $("#slide-demo").innerHTML = `<span>${e.prod_year} ${e.manufacturer.charAt(0) + e.manufacturer.slice(1).toLowerCase()}, ${e.engine_volume.toFixed(1)} L ${e.fuel_type.toLowerCase()}, ${FMT.int(e.mileage)} km</span><strong>${FMT.usd(p.price_usd)}</strong><span>Likely range ${FMT.usd(p.range_low)} to ${FMT.usd(p.range_high)}. Estimated live by the same service you can use below.</span>`;
        }).catch(() => { $("#slide-demo").textContent = "The live example is not available right now. Use the estimator to try a car."; });
}

// ------------------------------------------------------------------ start
initHero();
fetch("/api/insights").then((r) => r.json()).then((data) => {
    INS = data;
    bindData(); initAnatomy(); initCars(); initDeck(); initContact(); liveExample();
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => { initCharts(); initModels(); });
}).catch(() => {
    const note = document.createElement("div");
    note.className = "container alert alert-error";
    note.textContent = "The analysis data could not be loaded. Please refresh the page.";
    $("#main").prepend(note);
});
