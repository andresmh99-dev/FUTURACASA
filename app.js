// Datos exactos del Cuadro de Construcción (Hoja 1 de 2 — Lote 8, Manzana 147)
const VERTICES = [
  { id: 1, x: 276463.465, y: 2178461.832 },
  { id: 2, x: 276452.185, y: 2178455.250 },
  { id: 3, x: 276460.527, y: 2178436.963 },
  { id: 4, x: 276473.544, y: 2178444.557 },
];

const SIDES = [
  {
    est: 1,
    pv: 2,
    rumbo: "S 59° 44' 21\" W",
    distancia: 13.06,
    colindancia: "Lote 9",
  },
  {
    est: 2,
    pv: 3,
    rumbo: "S 24° 31' 18\" E",
    distancia: 20.10,
    colindancia: "Calle",
  },
  {
    est: 3,
    pv: 4,
    rumbo: "N 59° 44' 21\" E",
    distancia: 15.07,
    colindancia: "Calle Zacamixtle",
  },
  {
    est: 4,
    pv: 1,
    rumbo: "N 30° 15' 39\" W",
    distancia: 20.00,
    colindancia: "Lote 7",
  },
];

// Niveles interiores aproximados dentro del polígono (en coordenadas relativas 0..1)
const LEVELS = [
  { label: "NIVEL 103.30", u: 0.44, v: 0.25 },
  { label: "NIVEL 103.14", u: 0.58, v: 0.58 },
  { label: "NIVEL 102.87", u: 0.27, v: 0.74 },
];

const SVG_NS = "http://www.w3.org/2000/svg";
const svg = document.getElementById("lot-svg");
const tbody = document.querySelector("#construction-table tbody");
const readout = document.getElementById("selection-readout");

const toggleDimensions = document.getElementById("toggle-dimensions");
const toggleLevels = document.getElementById("toggle-levels");
const toggleNeighbors = document.getElementById("toggle-neighbors");

let activeSideIndex = null;

function el(tag, attrs = {}, text = null) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    node.setAttribute(k, v);
  }
  if (text !== null) node.textContent = text;
  return node;
}

function projectVertices() {
  const xs = VERTICES.map((v) => v.x);
  const ys = VERTICES.map((v) => v.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const width = 640;
  const height = 520;
  const pad = 105;

  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);

  const offsetX = (width - spanX * scale) / 2;
  const offsetY = (height - spanY * scale) / 2;

  const map = new Map();
  for (const v of VERTICES) {
    map.set(v.id, {
      ...v,
      sx: offsetX + (v.x - minX) * scale,
      sy: height - (offsetY + (v.y - minY) * scale),
    });
  }
  return { map, scale, minX, maxX, minY, maxY };
}

function formatNum(n) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}

function buildTable() {
  tbody.innerHTML = "";
  SIDES.forEach((s, idx) => {
    const pv = VERTICES.find((v) => v.id === s.pv);
    const tr = document.createElement("tr");
    tr.dataset.side = idx;
    tr.innerHTML = `
      <td><strong>${s.est} → ${s.pv}</strong></td>
      <td>${s.rumbo}</td>
      <td class="num">${s.distancia.toFixed(2)}</td>
      <td><strong>${pv.id}</strong></td>
      <td class="num">${formatNum(pv.x)}</td>
      <td class="num">${formatNum(pv.y)}</td>
    `;
    tr.addEventListener("mouseenter", () => setActiveSide(idx));
    tr.addEventListener("mouseleave", () => setActiveSide(null));
    tr.addEventListener("click", () => setActiveSide(activeSideIndex === idx ? null : idx));
    tbody.appendChild(tr);
  });
}

function setActiveSide(idx) {
  activeSideIndex = idx;
  document.querySelectorAll("#construction-table tbody tr").forEach((tr) => {
    tr.classList.toggle("is-active", Number(tr.dataset.side) === idx);
  });
  document.querySelectorAll(".side-line").forEach((line) => {
    const isCurrent = Number(line.dataset.side) === idx;
    line.setAttribute("stroke", isCurrent ? "#b4532a" : "#1f3b5c");
    line.setAttribute("stroke-width", isCurrent ? "4.5" : "2.6");
  });

  if (idx === null) {
    readout.textContent = "Pasa el cursor sobre un vértice o lado";
  } else {
    const s = SIDES[idx];
    readout.textContent = `Lado ${s.est}–${s.pv} · ${s.rumbo} · ${s.distancia.toFixed(2)} m (${s.colindancia})`;
  }
}

function renderSVG() {
  svg.innerHTML = "";
  const { map, scale } = projectVertices();
  const pts = VERTICES.map((v) => map.get(v.id));

  // Centroid
  const cx = pts.reduce((a, p) => a + p.sx, 0) / pts.length;
  const cy = pts.reduce((a, p) => a + p.sy, 0) / pts.length;

  // Polygon fill
  const polyPoints = pts.map((p) => `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(" ");
  svg.appendChild(
    el("polygon", {
      points: polyPoints,
      fill: "rgba(31, 59, 92, 0.08)",
      stroke: "none",
    })
  );

  // Center area label
  svg.appendChild(
    el(
      "text",
      {
        x: cx,
        y: cy - 8,
        "text-anchor": "middle",
        fill: "#171a1f",
        "font-family": "Space Grotesk, sans-serif",
        "font-size": "17",
        "font-weight": "700",
      },
      "LOTE 8"
    )
  );
  svg.appendChild(
    el(
      "text",
      {
        x: cx,
        y: cy + 12,
        "text-anchor": "middle",
        fill: "#565d67",
        "font-family": "JetBrains Mono, monospace",
        "font-size": "12",
      },
      "281.30 m²"
    )
  );

  // Sides + labels
  SIDES.forEach((s, idx) => {
    const p1 = map.get(s.est);
    const p2 = map.get(s.pv);
    const mx = (p1.sx + p2.sx) / 2;
    const my = (p1.sy + p2.sy) / 2;

    // Outward normal
    let dx = p2.sx - p1.sx;
    let dy = p2.sy - p1.sy;
    const len = Math.hypot(dx, dy);
    let nx = -dy / len;
    let ny = dx / len;
    // Ensure normal points away from centroid
    if ((mx + nx * 10 - cx) ** 2 + (my + ny * 10 - cy) ** 2 < (mx - cx) ** 2 + (my - cy) ** 2) {
      nx = -nx;
      ny = -ny;
    }

    const line = el("line", {
      x1: p1.sx,
      y1: p1.sy,
      x2: p2.sx,
      y2: p2.sy,
      stroke: activeSideIndex === idx ? "#b4532a" : "#1f3b5c",
      "stroke-width": activeSideIndex === idx ? "4.5" : "2.6",
      "stroke-linecap": "round",
      class: "side-line",
      "data-side": idx,
      style: "cursor:pointer",
    });
    line.addEventListener("mouseenter", () => setActiveSide(idx));
    line.addEventListener("mouseleave", () => setActiveSide(null));
    svg.appendChild(line);

    // Angle for text rotation (keep upright)
    let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
    if (angle > 90) angle -= 180;
    if (angle < -90) angle += 180;

    if (toggleDimensions.checked) {
      const lx = mx + nx * 18;
      const ly = my + ny * 18;
      const g = el("g", { transform: `translate(${lx.toFixed(1)}, ${ly.toFixed(1)}) rotate(${angle.toFixed(1)})` });
      g.appendChild(
        el(
          "text",
          {
            x: 0,
            y: 0,
            "text-anchor": "middle",
            fill: "#171a1f",
            "font-family": "JetBrains Mono, monospace",
            "font-size": "11.5",
            "font-weight": "600",
          },
          `${s.distancia.toFixed(2)} m`
        )
      );
      g.appendChild(
        el(
          "text",
          {
            x: 0,
            y: 13,
            "text-anchor": "middle",
            fill: "#565d67",
            "font-family": "JetBrains Mono, monospace",
            "font-size": "9.5",
          },
          s.rumbo
        )
      );
      svg.appendChild(g);
    }

    if (toggleNeighbors.checked) {
      const ox = mx + nx * 46;
      const oy = my + ny * 46;
      const ng = el("g", { transform: `translate(${ox.toFixed(1)}, ${oy.toFixed(1)}) rotate(${angle.toFixed(1)})` });
      ng.appendChild(
        el(
          "text",
          {
            x: 0,
            y: 4,
            "text-anchor": "middle",
            fill: "#b4532a",
            "font-family": "Inter, sans-serif",
            "font-size": "11.5",
            "font-weight": "600",
          },
          s.colindancia
        )
      );
      svg.appendChild(ng);
    }
  });

  // Interior levels
  if (toggleLevels.checked) {
    const p1 = map.get(1);
    const p2 = map.get(2);
    const p3 = map.get(3);
    const p4 = map.get(4);

    LEVELS.forEach((lv) => {
      // Bilinear interpolation inside quad (2=top-left, 1=top-right, 3=bottom-left, 4=bottom-right)
      const topX = p2.sx * (1 - lv.u) + p1.sx * lv.u;
      const topY = p2.sy * (1 - lv.u) + p1.sy * lv.u;
      const botX = p3.sx * (1 - lv.u) + p4.sx * lv.u;
      const botY = p3.sy * (1 - lv.u) + p4.sy * lv.u;
      const lx = topX * (1 - lv.v) + botX * lv.v;
      const ly = topY * (1 - lv.v) + botY * lv.v;

      svg.appendChild(
        el("circle", {
          cx: lx,
          cy: ly,
          r: "3.5",
          fill: "#b4532a",
        })
      );
      svg.appendChild(
        el(
          "text",
          {
            x: lx + 7,
            y: ly + 4,
            fill: "#1f3b5c",
            "font-family": "JetBrains Mono, monospace",
            "font-size": "10",
            "font-weight": "600",
          },
          lv.label
        )
      );
    });
  }

  // Vertices
  pts.forEach((p) => {
    const g = el("g", { style: "cursor:pointer" });
    g.appendChild(
      el("circle", {
        cx: p.sx,
        cy: p.sy,
        r: "10",
        fill: "#ffffff",
        stroke: "#1f3b5c",
        "stroke-width": "2.2",
      })
    );
    g.appendChild(
      el(
        "text",
        {
          x: p.sx,
          y: p.sy + 4,
          "text-anchor": "middle",
          fill: "#1f3b5c",
          "font-family": "JetBrains Mono, monospace",
          "font-size": "11",
          "font-weight": "700",
        },
        String(p.id)
      )
    );
    g.addEventListener("mouseenter", () => {
      readout.textContent = `Vértice ${p.id} · X: ${formatNum(p.x)} · Y: ${formatNum(p.y)}`;
    });
    g.addEventListener("mouseleave", () => {
      if (activeSideIndex === null) {
        readout.textContent = "Pasa el cursor sobre un vértice o lado";
      }
    });
    svg.appendChild(g);
  });

  // North arrow (top-right)
  const north = el("g", { transform: "translate(585, 56)" });
  north.appendChild(el("circle", { cx: 0, cy: 0, r: 22, fill: "#fff", stroke: "#dfdbd1", "stroke-width": "1.2" }));
  north.appendChild(el("polygon", { points: "0,-15 5,3 0,-1 -5,3", fill: "#1f3b5c" }));
  north.appendChild(
    el("text", { x: 0, y: 15, "text-anchor": "middle", fill: "#171a1f", "font-family": "Space Grotesk, sans-serif", "font-size": "10", "font-weight": "700" }, "N")
  );
  svg.appendChild(north);

  // Graphic scale bar (5 m)
  const barPx = 5 * scale;
  const barG = el("g", { transform: "translate(28, 488)" });
  barG.appendChild(el("rect", { x: 0, y: 0, width: barPx / 2, height: 6, fill: "#1f3b5c" }));
  barG.appendChild(el("rect", { x: barPx / 2, y: 0, width: barPx / 2, height: 6, fill: "#fff", stroke: "#1f3b5c", "stroke-width": "1" }));
  barG.appendChild(el("text", { x: 0, y: -5, fill: "#565d67", "font-family": "JetBrains Mono, monospace", "font-size": "10" }, "0"));
  barG.appendChild(el("text", { x: barPx, y: -5, "text-anchor": "end", fill: "#565d67", "font-family": "JetBrains Mono, monospace", "font-size": "10" }, "5 m"));
  svg.appendChild(barG);
}

[toggleDimensions, toggleLevels, toggleNeighbors].forEach((input) => {
  input.addEventListener("change", renderSVG);
});

buildTable();
renderSVG();

// Controles del visor 3D interactivo (<model-viewer>)
const modelViewer = document.getElementById("lot-model-viewer");
const viewerFallback = document.getElementById("viewer-fallback");
const toggleRotateBtn = document.getElementById("toggle-rotate");

if (modelViewer) {
  document.querySelectorAll(".chip-btn[data-orbit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      modelViewer.cameraOrbit = btn.dataset.orbit;
      modelViewer.jumpCameraToGoal?.();
      document.querySelectorAll(".chip-btn[data-orbit]").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
    });
  });

  if (toggleRotateBtn) {
    toggleRotateBtn.addEventListener("click", () => {
      const enabled = modelViewer.hasAttribute("auto-rotate");
      if (enabled) {
        modelViewer.removeAttribute("auto-rotate");
      } else {
        modelViewer.setAttribute("auto-rotate", "");
      }
      toggleRotateBtn.classList.toggle("is-active", !enabled);
    });
  }

  modelViewer.addEventListener("error", () => {
    if (viewerFallback) viewerFallback.hidden = false;
  });

  if (window.location.protocol === "file:" && viewerFallback) {
    viewerFallback.hidden = false;
  }
}
