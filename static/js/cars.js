/* Vector car illustrations (no image files needed). Cars face right.
 * CarArt.svg(type, colour) returns an <svg> string; CarArt.TYPES lists the body styles.
 */
const CarArt = (() => {
    let uid = 0;

    // body: whole silhouette; glass: window shapes; pillars: lines drawn over the glass; wheels: [x, radius]
    const SHAPES = {
        sedan: {
            body: "M30,134 C26,134 26,116 30,108 L52,102 C70,100 90,98 112,95 C140,74 170,58 222,56 L292,56 C318,58 340,72 364,92 L412,98 C436,102 452,112 454,128 L454,134 Z",
            glass: ["M134,94 C154,77 182,65 222,63 L284,63 C304,65 324,77 342,92 Z"],
            pillars: ["M222,63 L222,93", "M286,63 L292,93"], wheels: [[118, 26], [362, 26]], head: [430, 112], tail: [34, 110], sy: 1.32,
        },
        suv: {
            body: "M26,132 L24,72 C24,62 30,58 40,58 L296,56 C320,56 334,62 346,78 L374,92 L424,100 C444,104 452,114 452,126 L452,132 Z",
            glass: ["M46,66 L292,64 C310,64 320,70 330,82 L340,92 L46,92 Z"],
            pillars: ["M110,65 L112,92", "M178,65 L180,92", "M246,65 L248,92"], wheels: [[122, 29], [362, 29]], head: [432, 110], tail: [30, 96], sy: 1.12,
        },
        hatchback: {
            body: "M34,134 L30,98 C30,90 36,86 46,84 L108,72 C138,58 170,54 206,54 L264,54 C296,56 318,70 340,88 L402,96 C428,100 440,110 442,126 L442,134 Z",
            glass: ["M122,86 C148,68 176,62 206,62 L262,62 C284,64 302,76 320,90 L122,90 Z"],
            pillars: ["M206,62 L206,90", "M266,62 L270,90"], wheels: [[116, 25], [350, 25]], head: [422, 110], tail: [36, 100], sy: 1.35,
        },
        minivan: {
            body: "M28,134 L26,72 C26,60 34,54 48,54 L270,52 C296,52 316,64 336,84 L408,96 C432,100 442,110 442,126 L442,134 Z",
            glass: ["M46,62 L268,60 C288,60 304,70 322,88 L46,88 Z"],
            pillars: ["M120,61 L120,88", "M196,60 L196,88"], wheels: [[118, 26], [352, 26]], head: [422, 110], tail: [32, 80], sy: 1.12,
        },
        coupe: {
            body: "M32,134 L30,114 C30,106 36,102 50,100 L128,92 C160,68 196,58 236,58 L268,58 C300,60 324,76 346,92 L420,100 C440,106 450,114 452,128 L452,134 Z",
            glass: ["M150,92 C172,72 202,64 236,64 L266,64 C288,66 308,78 326,92 Z"],
            pillars: ["M240,64 L244,92"], wheels: [[122, 26], [364, 26]], head: [430, 114], tail: [36, 112], sy: 1.4,
        },
        wagon: {
            body: "M28,134 L26,98 C26,88 34,82 46,80 L150,62 C170,56 190,54 214,54 L316,54 C334,56 346,66 358,82 L404,96 C430,100 442,110 444,126 L444,134 Z",
            glass: ["M148,86 C168,70 190,62 214,62 L312,62 C328,64 338,74 348,88 L148,88 Z"],
            pillars: ["M214,62 L214,88", "M276,62 L278,88"], wheels: [[116, 26], [356, 26]], head: [424, 110], tail: [30, 100], sy: 1.35,
        },
        pickup: {
            body: "M24,132 L24,92 L186,92 L194,70 C204,56 226,52 252,52 L298,52 C322,54 338,66 354,84 L420,96 C440,100 450,112 450,124 L450,132 Z",
            glass: ["M208,60 C216,58 232,58 252,58 L296,58 C316,60 328,70 340,84 L204,84 Z"],
            pillars: ["M252,58 L254,84"], wheels: [[118, 29], [374, 29]], head: [430, 112], tail: [28, 100], sy: 1.2,
        },
        van: {
            body: "M26,134 L24,52 C24,46 30,42 38,42 L330,42 C346,42 356,48 364,62 L398,94 L426,100 C440,104 446,114 446,128 L446,134 Z",
            glass: ["M44,52 L322,52 C334,52 340,56 346,66 L364,90 L44,90 Z"],
            pillars: ["M120,52 L120,90", "M200,52 L200,90", "M280,52 L280,90"], wheels: [[108, 27], [364, 27]], head: [430, 114], tail: [28, 66], sy: 1.0,
        },
    };

    function shade(hex, amt) {
        const n = parseInt(hex.slice(1), 16);
        const c = (v) => Math.max(0, Math.min(255, v + amt));
        return "#" + [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => c(v).toString(16).padStart(2, "0")).join("");
    }

    function svg(type = "sedan", colour = "#2f6bff", opts = {}) {
        const s = SHAPES[type] || SHAPES.sedan;
        const id = "car" + ++uid;
        const light = shade(colour, 38), dark = shade(colour, -48);
        const wheelY = 134, SX = 0.84, SY = s.sy || 1.2;
        const X = (x) => 240 + (x - 240) * SX;
        const squash = `translate(240,${wheelY}) scale(${SX},${SY}) translate(-240,-${wheelY})`;
        const wheels = s.wheels.map(([x0, r]) => { const x = X(x0); return `
            <circle cx="${x}" cy="${wheelY}" r="${r + 7}" fill="#0b1220"/>
            <g class="wheel ${opts.spin ? "wheel-spin" : ""}" style="transform-origin:${x}px ${wheelY}px">
              <circle cx="${x}" cy="${wheelY}" r="${r}" fill="#151c2c"/>
              <circle cx="${x}" cy="${wheelY}" r="${r * 0.68}" fill="#c9d2e0"/>
              <circle cx="${x}" cy="${wheelY}" r="${r * 0.52}" fill="#8a96ab"/>
              ${[0, 72, 144, 216, 288].map((a) => `<rect x="${x - 2}" y="${wheelY - r * 0.66}" width="4" height="${r * 0.5}" rx="2" fill="#e8edf5" transform="rotate(${a} ${x} ${wheelY})"/>`).join("")}
              <circle cx="${x}" cy="${wheelY}" r="${r * 0.14}" fill="#2a3347"/>
            </g>`; }).join("");
        const hx = X(s.head[0]), hy = wheelY - (wheelY - s.head[1]) * SY, tx = X(s.tail[0]), ty = wheelY - (wheelY - s.tail[1]) * SY;
        return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 180" role="img" aria-label="${opts.label || type + " illustration"}" class="car-art">
          <defs>
            <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${light}"/><stop offset=".55" stop-color="${colour}"/><stop offset="1" stop-color="${dark}"/></linearGradient>
            <linearGradient id="${id}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#dff1ff"/><stop offset="1" stop-color="#5f7fa6"/></linearGradient>
            <radialGradient id="${id}s" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".38"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
            <linearGradient id="${id}h" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
          </defs>
          <ellipse cx="240" cy="162" rx="200" ry="11" fill="url(#${id}s)"/>
          <g transform="${squash}">
            <path d="${s.body}" fill="url(#${id}b)"/>
            ${s.glass.map((g) => `<path d="${g}" fill="url(#${id}g)" opacity=".95"/>`).join("")}
            ${s.pillars.map((p) => `<path d="${p}" stroke="${colour}" stroke-width="5" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`).join("")}
            <path d="${s.body}" fill="none" stroke="${dark}" stroke-opacity=".55" stroke-width="1.4" vector-effect="non-scaling-stroke"/>
          </g>
          <path d="M${tx + 30},${hy - 6} L${hx - 14},${hy - 6}" stroke="url(#${id}h)" stroke-width="3" opacity=".7"/>
          ${wheels}
          <rect x="${hx - 20}" y="${hy - 8}" width="24" height="9" rx="4" fill="#fff6d6" class="headlight"/>
          <rect x="${tx - 2}" y="${ty - 4}" width="11" height="8" rx="3" fill="#ff4d4d"/>
        </svg>`;
    }

    return { svg, TYPES: Object.keys(SHAPES), shade };
})();
