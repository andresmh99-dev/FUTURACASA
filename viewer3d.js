import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const container = document.getElementById("viewer-canvas-wrap");
if (container) {
  initViewer();
}

function createGrassTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#67724d";
  ctx.fillRect(0, 0, 512, 512);

  // Subtle organic meadow variation matching the renders
  for (let i = 0; i < 18000; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const shade = Math.random();
    ctx.fillStyle =
      shade < 0.33
        ? "rgba(84, 95, 60, 0.35)"
        : shade < 0.66
          ? "rgba(124, 134, 92, 0.28)"
          : "rgba(68, 76, 48, 0.3)";
    ctx.fillRect(x, y, 2 + Math.random() * 3, 2 + Math.random() * 4);
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(14, 14);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createMarbleTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#f4f2ee";
  ctx.fillRect(0, 0, 256, 256);
  ctx.strokeStyle = "rgba(145, 138, 128, 0.35)";
  ctx.lineWidth = 1.6;
  for (let i = 0; i < 14; i++) {
    ctx.beginPath();
    let x = Math.random() * 256;
    let y = 0;
    ctx.moveTo(x, y);
    for (let step = 0; step < 8; step++) {
      x += (Math.random() - 0.5) * 45;
      y += 32;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createSkyDome() {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0.0, "#6fa3d8");
  grad.addColorStop(0.42, "#b8d4ec");
  grad.addColorStop(0.54, "#f4f2eb");
  grad.addColorStop(0.62, "#879276");
  grad.addColorStop(1.0, "#5c664a");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 256);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const geo = new THREE.SphereGeometry(180, 32, 24);
  const mat = new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false });
  return new THREE.Mesh(geo, mat);
}

function createTree(scale = 1, withBlossoms = true) {
  const group = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x56463a, roughness: 0.92 });
  const leafDark = new THREE.MeshStandardMaterial({ color: 0x3e5b34, roughness: 0.85 });
  const leafLight = new THREE.MeshStandardMaterial({ color: 0x5c7c45, roughness: 0.82 });
  const blossomMat = new THREE.MeshStandardMaterial({ color: 0xf7f5ef, roughness: 0.7 });

  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.11 * scale, 0.19 * scale, 3.0 * scale, 8), trunkMat);
  trunk.position.y = 1.5 * scale;
  trunk.castShadow = true;
  group.add(trunk);

  // Secondary branches
  const branchOffsets = [
    [0.45, 2.7, 0.2, 0.4, 0, -0.35],
    [-0.4, 2.5, -0.25, -0.35, 0, 0.4],
    [0.1, 3.1, -0.35, -0.45, 0, 0.1],
  ];
  branchOffsets.forEach(([bx, by, bz, rx, ry, rz]) => {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(0.05 * scale, 0.09 * scale, 1.8 * scale, 6), trunkMat);
    br.position.set(bx * scale, by * scale, bz * scale);
    br.rotation.set(rx, ry, rz);
    br.castShadow = true;
    group.add(br);
  });

  // Layered organic canopy clusters
  const clusters = [
    [0, 4.3, 0, 1.35, leafDark],
    [0.85, 3.8, 0.45, 1.05, leafLight],
    [-0.8, 3.9, -0.35, 1.1, leafDark],
    [0.35, 5.1, -0.3, 1.0, leafLight],
    [-0.45, 4.9, 0.55, 0.95, leafLight],
    [0.15, 5.75, 0.1, 0.78, leafDark],
  ];
  clusters.forEach(([x, y, z, r, mat]) => {
    const puff = new THREE.Mesh(new THREE.DodecahedronGeometry(r * scale, 1), mat);
    puff.position.set(x * scale, y * scale, z * scale);
    puff.scale.set(1.1, 0.85, 1.05);
    puff.castShadow = true;
    puff.receiveShadow = true;
    group.add(puff);
  });

  if (withBlossoms) {
    for (let i = 0; i < 18; i++) {
      const a = (i / 18) * Math.PI * 2;
      const rad = (0.7 + (i % 3) * 0.45) * scale;
      const b = new THREE.Mesh(new THREE.DodecahedronGeometry(0.14 * scale, 0), blossomMat);
      b.position.set(Math.cos(a) * rad, (3.6 + (i % 5) * 0.42) * scale, Math.sin(a) * rad);
      group.add(b);
    }
  }

  return group;
}

function buildRenderDetails(clipPlane) {
  const group = new THREE.Group();
  group.name = "render-details";

  const attachClip = (mat) => {
    mat.clippingPlanes = [clipPlane];
    mat.clipShadows = true;
    return mat;
  };

  // Materials matching the 5 renders
  const warmGlowMat = attachClip(
    new THREE.MeshStandardMaterial({
      color: 0xfff3d6,
      emissive: 0xffd28a,
      emissiveIntensity: 2.2,
      roughness: 0.4,
    })
  );
  const darkMetalMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x26292e, roughness: 0.42, metalness: 0.55 }));
  const alumMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.32, metalness: 0.65 }));
  const glassMat = attachClip(
    new THREE.MeshPhysicalMaterial({
      color: 0xdbe9f4,
      transparent: true,
      opacity: 0.28,
      roughness: 0.08,
      metalness: 0.05,
      reflectivity: 0.9,
      side: THREE.DoubleSide,
    })
  );
  const woodMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x8e6f54, roughness: 0.72 }));
  const beigeCabMat = attachClip(new THREE.MeshStandardMaterial({ color: 0xd8c3aa, roughness: 0.65 }));
  const darkIslandMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x3a3f44, roughness: 0.72 }));
  const marbleMat = attachClip(new THREE.MeshStandardMaterial({ map: createMarbleTexture(), roughness: 0.35 }));
  const creamFabricMat = attachClip(new THREE.MeshStandardMaterial({ color: 0xe6dfd3, roughness: 0.92 }));
  const olivePillowMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x6f7356, roughness: 0.9 }));
  const slateDeckMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x45494e, roughness: 0.85 }));
  const concretePaverMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x8d8d88, roughness: 0.88 }));
  const rockMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x686b6e, roughness: 0.94 }));
  const lavenderMat = attachClip(new THREE.MeshStandardMaterial({ color: 0x6f5a87, roughness: 0.9 }));

  // 1. Franja horizontal iluminada bajo el volumen en voladizo (Renders 1 y 2)
  const ribbonFront = new THREE.Mesh(new THREE.BoxGeometry(10.6, 0.26, 0.14), warmGlowMat);
  ribbonFront.position.set(12.2, -0.34, 14.55);
  group.add(ribbonFront);

  const ribbonSide = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.26, 8.2), warmGlowMat);
  ribbonSide.position.set(17.25, -0.34, 10.6);
  group.add(ribbonSide);

  // 2. Ventanal panorámico del 1er Nivel (Render 1 y Render 3)
  const panWindow = new THREE.Mesh(new THREE.PlaneGeometry(8.2, 3.05), glassMat);
  panWindow.position.set(12.6, 1.46, 14.62);
  group.add(panWindow);

  // Parteluces metálicos del ventanal
  [-4.1, -1.4, 1.4, 4.1].forEach((dx) => {
    const mullion = new THREE.Mesh(new THREE.BoxGeometry(0.07, 3.05, 0.08), alumMat);
    mullion.position.set(12.6 + dx, 1.46, 14.62);
    group.add(mullion);
  });
  const transom = new THREE.Mesh(new THREE.BoxGeometry(8.2, 0.06, 0.08), alumMat);
  transom.position.set(12.6, 0.65, 14.62);
  group.add(transom);

  // 3. Interior 1er Nivel: Cocina, Sala y Comedor (Render 3)
  // Gabinetes beige de cocina + backsplash de mármol + luz LED inferior
  const cabUpper = new THREE.Mesh(new THREE.BoxGeometry(4.4, 1.15, 0.45), beigeCabMat);
  cabUpper.position.set(12.4, 2.25, 6.7);
  cabUpper.castShadow = true;
  group.add(cabUpper);

  const backsplash = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.85, 0.08), marbleMat);
  backsplash.position.set(12.4, 1.28, 6.52);
  group.add(backsplash);

  const kitchenLed = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.05, 0.06), warmGlowMat);
  kitchenLed.position.set(12.4, 1.66, 6.62);
  group.add(kitchenLed);

  const fridge = new THREE.Mesh(new THREE.BoxGeometry(0.92, 2.05, 0.72), alumMat);
  fridge.position.set(9.7, 0.9, 6.85);
  fridge.castShadow = true;
  group.add(fridge);

  // Isla oscura con cubierta de mármol
  const islandBase = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.92, 1.05), darkIslandMat);
  islandBase.position.set(12.4, 0.34, 8.65);
  islandBase.castShadow = true;
  islandBase.receiveShadow = true;
  group.add(islandBase);

  const islandTop = new THREE.Mesh(new THREE.BoxGeometry(3.62, 0.07, 1.16), marbleMat);
  islandTop.position.set(12.4, 0.83, 8.65);
  group.add(islandTop);

  // Sala (sofá en L color crema + cojines olivo + mesa de centro negra)
  const sofaMain = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.48, 1.0), creamFabricMat);
  sofaMain.position.set(12.2, 0.14, 11.4);
  sofaMain.castShadow = true;
  group.add(sofaMain);

  const sofaBack = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.55, 0.24), creamFabricMat);
  sofaBack.position.set(12.2, 0.58, 11.0);
  group.add(sofaBack);

  const sofaChaise = new THREE.Mesh(new THREE.BoxGeometry(1.05, 0.48, 2.05), creamFabricMat);
  sofaChaise.position.set(10.65, 0.14, 12.1);
  sofaChaise.castShadow = true;
  group.add(sofaChaise);

  [11.4, 12.7].forEach((px) => {
    const pillow = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.36, 0.18), olivePillowMat);
    pillow.position.set(px, 0.52, 11.24);
    pillow.rotation.z = px < 12 ? 0.12 : -0.1;
    group.add(pillow);
  });

  const coffeeTable = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 0.05, 20), darkMetalMat);
  coffeeTable.position.set(12.4, 0.25, 12.6);
  group.add(coffeeTable);

  // Comedor junto al ventanal
  const diningTop = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.06, 1.05), woodMat);
  diningTop.position.set(15.3, 0.62, 12.4);
  diningTop.castShadow = true;
  group.add(diningTop);
  [14.6, 15.3, 16.0].forEach((cx) => {
    [-0.65, 0.65].forEach((dz) => {
      const chair = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.48, 0.45), creamFabricMat);
      chair.position.set(cx, 0.25, 12.4 + dz);
      group.add(chair);
    });
  });

  // 4. Patio Jardín Privado (Planta Baja, lado derecho — Render 1, 2 y 4)
  const treeMain = createTree(1.22, true);
  treeMain.position.set(19.6, -3.25, 12.4);
  group.add(treeMain);

  const treeSecond = createTree(0.95, true);
  treeSecond.position.set(20.8, -3.25, 8.2);
  group.add(treeSecond);

  // Terraza de estar oscura + 2 sillones + mesa
  const loungeDeck = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.18, 3.6), slateDeckMat);
  loungeDeck.position.set(19.4, -3.18, 8.2);
  loungeDeck.receiveShadow = true;
  group.add(loungeDeck);

  [18.5, 20.3].forEach((sx) => {
    const chair = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.42, 0.58, 12), creamFabricMat);
    chair.position.set(sx, -2.8, 7.7);
    chair.castShadow = true;
    group.add(chair);
  });
  const patioTable = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.32, 16), concretePaverMat);
  patioTable.position.set(19.4, -2.93, 8.35);
  group.add(patioTable);

  // Andadores de concreto y rocas naturales
  for (let i = 0; i < 4; i++) {
    const paver = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.08, 0.72), concretePaverMat);
    paver.position.set(18.6 + (i % 2) * 1.45, -3.28, 11.4 + Math.floor(i / 2) * 1.05);
    paver.receiveShadow = true;
    group.add(paver);
  }

  [
    [19.2, -3.0, 10.4, 0.55],
    [21.2, -2.85, 9.6, 0.72],
    [18.1, -3.08, 13.1, 0.42],
  ].forEach(([rx, ry, rz, r]) => {
    const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 1), rockMat);
    rock.position.set(rx, ry, rz);
    rock.scale.set(1.2, 0.75, 1.0);
    rock.castShadow = true;
    group.add(rock);
  });

  // Arbustos de lavanda alrededor de los árboles
  for (let i = 0; i < 10; i++) {
    const bush = new THREE.Mesh(new THREE.DodecahedronGeometry(0.28, 0), lavenderMat);
    bush.position.set(18.8 + (i % 5) * 0.65, -3.12, 11.6 + Math.floor(i / 5) * 1.3);
    group.add(bush);
  }

  // Arbotantes cálidos en barda del patio (Render 4)
  [
    [22.4, -1.2, 8.5],
    [22.4, -1.2, 12.2],
    [19.4, -1.2, 6.2],
  ].forEach(([lx, ly, lz]) => {
    const sconce = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.16, 0.18), darkMetalMat);
    sconce.position.set(lx, ly, lz);
    group.add(sconce);
    const glow = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.24, 0.14), warmGlowMat);
    glow.position.set(lx, ly, lz);
    group.add(glow);
  });

  // Cancelería negra de recámaras hacia el patio
  const bedroomGlass = new THREE.Mesh(new THREE.PlaneGeometry(5.6, 2.55), glassMat);
  bedroomGlass.rotation.y = Math.PI / 2;
  bedroomGlass.position.set(17.28, -1.9, 10.2);
  group.add(bedroomGlass);
  [-2.8, -0.95, 0.95, 2.8].forEach((dz) => {
    const frame = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.58, 0.07), darkMetalMat);
    frame.position.set(17.28, -1.9, 10.2 + dz);
    group.add(frame);
  });

  // 5. Celosía vertical de madera en fachada lateral de acceso (Render 5)
  const slatCount = 26;
  for (let i = 0; i < slatCount; i++) {
    const slat = new THREE.Mesh(new THREE.BoxGeometry(0.08, 3.25, 0.06), woodMat);
    slat.position.set(3.25, 1.35, 4.15 + i * 0.22);
    slat.castShadow = true;
    group.add(slat);
  }

  return group;
}

function initViewer() {
  const statusEl = document.getElementById("viewer-status");
  const fallbackEl = document.getElementById("viewer-fallback");
  const stationTitleEl = document.getElementById("tour-station-title");
  const stationDescEl = document.getElementById("tour-station-desc");
  const refThumbEl = document.getElementById("tour-ref-thumb");
  const stationDotsEl = document.getElementById("tour-dots");
  const playBtn = document.getElementById("tour-play");
  const prevBtn = document.getElementById("tour-prev");
  const nextBtn = document.getElementById("tour-next");
  const modeOrbitBtn = document.getElementById("mode-orbit");
  const modeWalkBtn = document.getElementById("mode-walk");
  const renderStyleBtn = document.getElementById("toggle-render-style");
  const walkHud = document.getElementById("walk-hud");
  const clipSlider = document.getElementById("clip-slider");
  const clipValueEl = document.getElementById("clip-value");
  const fullscreenBtn = document.getElementById("viewer-fullscreen");
  const viewerCard = document.getElementById("viewer-card");

  if (window.location.protocol === "file:") {
    if (fallbackEl) fallbackEl.hidden = false;
    if (statusEl) statusEl.textContent = "Requiere HTTP/HTTPS (GitHub Pages o localhost)";
    return;
  }

  // Paradas calibradas a las coordenadas reales de L8_MEXICO_SKP_3.glb y vinculadas a los 5 renders
  const TOUR_STATIONS = [
    {
      name: "1. Fachada Principal y Vialidad",
      desc: "Volumen superior suspendido sobre barda perimetral y franja horizontal iluminada.",
      pos: new THREE.Vector3(14.5, 2.0, 31.5),
      target: new THREE.Vector3(13.5, 0.3, 10.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-36.jpg",
      lightboxIndex: 1,
    },
    {
      name: "2. Perspectiva Esquina y Voladizo",
      desc: "Ventanal de piso a techo en primer nivel y relación con el patio arbolado.",
      pos: new THREE.Vector3(24.5, 2.4, 24.5),
      target: new THREE.Vector3(13.2, 0.4, 10.8),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
    {
      name: "3. Acceso y Fachada con Celosía",
      desc: "Fachada lateral sobre la pendiente con celosía vertical de madera.",
      pos: new THREE.Vector3(-4.8, 1.5, 10.5),
      target: new THREE.Vector3(9.5, 0.4, 8.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-41-14.jpg",
      lightboxIndex: 4,
    },
    {
      name: "4. Patio Jardín y Recámaras (Planta Baja)",
      desc: "Jardín interior privado con árboles, rocas naturales, terraza de estar y ventanales.",
      pos: new THREE.Vector3(20.6, -1.45, 15.8),
      target: new THREE.Vector3(18.6, -1.8, 8.4),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-59.jpg",
      lightboxIndex: 3,
    },
    {
      name: "5. Sala, Comedor y Cocina (1er Nivel)",
      desc: "Espacio social abierto en primer nivel con cocina de mármol y vista panorámica.",
      pos: new THREE.Vector3(12.8, 1.45, 13.7),
      target: new THREE.Vector3(12.2, 1.2, 7.4),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-48.jpg",
      lightboxIndex: 2,
    },
    {
      name: "6. Vista Aérea y Entorno",
      desc: "Implantación completa de la casa sobre el Lote 8 y la topografía del Fracc. México.",
      pos: new THREE.Vector3(31.0, 15.5, 28.0),
      target: new THREE.Vector3(14.0, 0.0, 10.0),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
  ];

  // Escena, cielo arquitectónico y entorno PMREM
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xd5e4f2);
  scene.fog = new THREE.Fog(0xdce6ee, 65, 165);
  scene.add(createSkyDome());

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.localClippingEnabled = true;
  container.appendChild(renderer.domElement);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.45;

  // Cámara y controles de órbita
  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / container.clientHeight,
    0.1,
    350
  );
  camera.position.copy(TOUR_STATIONS[0].pos);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.target.copy(TOUR_STATIONS[0].target);
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minDistance = 1.2;
  controls.maxDistance = 90;
  controls.update();

  // Iluminación arquitectónica cálida de tarde
  const hemiLight = new THREE.HemisphereLight(0xeef6ff, 0x7c8468, 0.95);
  hemiLight.position.set(0, 40, 0);
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xfff4e0, 2.1);
  sunLight.position.set(34, 38, 22);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 120;
  sunLight.shadow.camera.left = -38;
  sunLight.shadow.camera.right = 38;
  sunLight.shadow.camera.top = 38;
  sunLight.shadow.camera.bottom = -38;
  sunLight.shadow.bias = -0.0004;
  scene.add(sunLight);

  const fillLight = new THREE.DirectionalLight(0xcfe2f7, 0.55);
  fillLight.position.set(-24, 20, -18);
  scene.add(fillLight);

  // Luces cálidas interiores y de patio
  const livingGlow = new THREE.PointLight(0xffdca6, 16, 18, 1.5);
  livingGlow.position.set(12.5, 2.15, 10.0);
  scene.add(livingGlow);

  const patioGlow = new THREE.PointLight(0xffd292, 14, 15, 1.6);
  patioGlow.position.set(19.5, -1.1, 10.2);
  scene.add(patioGlow);

  // Plano de corte horizontal (maqueta seccionada)
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 6.0);

  // Materiales de mejora "Acabados Render"
  const whiteStuccoMat = new THREE.MeshStandardMaterial({
    color: 0xf4f2ed,
    roughness: 0.84,
    metalness: 0.0,
    side: THREE.DoubleSide,
    clippingPlanes: [clipPlane],
    clipShadows: true,
  });
  const grassTerrainMat = new THREE.MeshStandardMaterial({
    map: createGrassTexture(),
    roughness: 0.95,
    metalness: 0.0,
    side: THREE.DoubleSide,
    clippingPlanes: [clipPlane],
    clipShadows: true,
  });
  const gravelPadMat = new THREE.MeshStandardMaterial({
    color: 0xc2bcb0,
    roughness: 0.92,
    metalness: 0.0,
    side: THREE.DoubleSide,
    clippingPlanes: [clipPlane],
    clipShadows: true,
  });

  // Grupo con elementos arquitectónicos de los renders
  const renderDetailsGroup = buildRenderDetails(clipPlane);
  scene.add(renderDetailsGroup);

  // Referencias para alternar entre "Acabados Render" y "Maqueta SKP original"
  let useRenderStyle = true;
  const skpMeshRecords = [];
  const skpEdgeLines = [];

  function applyVisualStyle() {
    renderDetailsGroup.visible = useRenderStyle;
    skpEdgeLines.forEach((line) => {
      line.visible = !useRenderStyle;
    });
    skpMeshRecords.forEach(({ mesh, originalMat, renderMat }) => {
      mesh.material = useRenderStyle ? renderMat : originalMat;
    });
    if (renderStyleBtn) {
      renderStyleBtn.classList.toggle("is-active", useRenderStyle);
      renderStyleBtn.textContent = useRenderStyle ? "Acabados Render" : "Maqueta SKP";
    }
  }

  renderStyleBtn?.addEventListener("click", () => {
    useRenderStyle = !useRenderStyle;
    applyVisualStyle();
  });

  // Estado de navegación
  let mode = "orbit";
  let currentStation = 0;
  let isPlayingTour = false;
  let tourHoldTimer = 0;
  let transition = null;

  // Estado modo caminar
  const keys = new Set();
  const touchMove = { forward: 0, right: 0, up: 0 };
  let yaw = 0;
  let pitch = 0;
  let isLooking = false;
  let lastPointer = { x: 0, y: 0 };

  function syncYawPitchFromCamera() {
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    yaw = Math.atan2(-dir.x, -dir.z);
    pitch = Math.asin(THREE.MathUtils.clamp(dir.y, -0.95, 0.95));
  }

  function applyYawPitchToCamera() {
    const euler = new THREE.Euler(pitch, yaw, 0, "YXZ");
    camera.quaternion.setFromEuler(euler);
  }

  function setMode(newMode) {
    mode = newMode;
    modeOrbitBtn?.classList.toggle("is-active", mode === "orbit");
    modeWalkBtn?.classList.toggle("is-active", mode === "walk");
    if (walkHud) walkHud.hidden = mode !== "walk";

    if (mode === "walk") {
      stopTour();
      transition = null;
      controls.enabled = false;
      if (camera.position.distanceTo(new THREE.Vector3(13.5, 0, 10.5)) > 26) {
        camera.position.set(12.8, 1.45, 13.7);
        camera.lookAt(12.2, 1.2, 7.4);
      }
      syncYawPitchFromCamera();
      if (statusEl) statusEl.textContent = "Modo Caminar · WASD/Flechas + arrastra para mirar";
    } else {
      controls.enabled = true;
      const forward = new THREE.Vector3();
      camera.getWorldDirection(forward);
      controls.target.copy(camera.position).addScaledVector(forward, 6);
      controls.update();
      if (statusEl) statusEl.textContent = "Modo Órbita · Arrastra para rotar · Rueda para zoom";
    }
  }

  function goToStation(index, duration = 1.6) {
    currentStation = (index + TOUR_STATIONS.length) % TOUR_STATIONS.length;
    const st = TOUR_STATIONS[currentStation];
    if (mode !== "orbit") setMode("orbit");

    transition = {
      startPos: camera.position.clone(),
      endPos: st.pos.clone(),
      startTarget: controls.target.clone(),
      endTarget: st.target.clone(),
      t: 0,
      duration,
    };
    updateTourUI();
  }

  function updateTourUI() {
    const st = TOUR_STATIONS[currentStation];
    if (stationTitleEl) stationTitleEl.textContent = st.name;
    if (stationDescEl) stationDescEl.textContent = st.desc;
    if (refThumbEl && st.render) {
      refThumbEl.src = st.render;
      refThumbEl.dataset.lightbox = String(st.lightboxIndex ?? 0);
    }
    if (stationDotsEl) {
      stationDotsEl.querySelectorAll("button").forEach((dot, idx) => {
        dot.classList.toggle("is-active", idx === currentStation);
      });
    }
    if (playBtn) {
      playBtn.textContent = isPlayingTour ? "⏸ Pausar recorrido" : "▶ Iniciar recorrido";
      playBtn.classList.toggle("is-active", isPlayingTour);
    }
  }

  function stopTour() {
    isPlayingTour = false;
    tourHoldTimer = 0;
    updateTourUI();
  }

  if (stationDotsEl) {
    stationDotsEl.innerHTML = "";
    TOUR_STATIONS.forEach((st, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tour-dot" + (idx === 0 ? " is-active" : "");
      btn.title = st.name;
      btn.setAttribute("aria-label", st.name);
      btn.addEventListener("click", () => {
        stopTour();
        goToStation(idx);
      });
      stationDotsEl.appendChild(btn);
    });
  }
  updateTourUI();

  playBtn?.addEventListener("click", () => {
    if (isPlayingTour) {
      stopTour();
    } else {
      isPlayingTour = true;
      tourHoldTimer = 0;
      goToStation(currentStation, 1.4);
      updateTourUI();
    }
  });

  prevBtn?.addEventListener("click", () => {
    stopTour();
    goToStation(currentStation - 1);
  });

  nextBtn?.addEventListener("click", () => {
    stopTour();
    goToStation(currentStation + 1);
  });

  modeOrbitBtn?.addEventListener("click", () => setMode("orbit"));
  modeWalkBtn?.addEventListener("click", () => setMode("walk"));

  document.querySelectorAll("[data-floor-y]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (mode !== "walk") setMode("walk");
      const y = parseFloat(btn.dataset.floorY);
      if (y < 0) {
        camera.position.set(20.0, y, 13.8);
        camera.lookAt(18.5, y - 0.1, 8.2);
      } else {
        camera.position.set(12.8, y, 13.7);
        camera.lookAt(12.2, y - 0.1, 7.4);
      }
      syncYawPitchFromCamera();
    });
  });

  document.querySelectorAll("[data-move]").forEach((btn) => {
    const dir = btn.dataset.move;
    const setVal = (v) => {
      if (dir === "forward") touchMove.forward = v;
      if (dir === "back") touchMove.forward = -v;
      if (dir === "left") touchMove.right = -v;
      if (dir === "right") touchMove.right = v;
      if (dir === "up") touchMove.up = v;
      if (dir === "down") touchMove.up = -v;
    };
    btn.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      setVal(1);
    });
    const stop = () => setVal(0);
    btn.addEventListener("pointerup", stop);
    btn.addEventListener("pointerleave", stop);
    btn.addEventListener("pointercancel", stop);
  });

  if (clipSlider) {
    const updateClip = () => {
      const val = parseFloat(clipSlider.value);
      clipPlane.constant = val;
      if (clipValueEl) {
        clipValueEl.textContent = val >= 5.9 ? "Completo" : `Corte ${val.toFixed(1)} m`;
      }
    };
    clipSlider.addEventListener("input", updateClip);
    updateClip();
  }

  fullscreenBtn?.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      viewerCard?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  });

  window.addEventListener("keydown", (e) => {
    if (mode !== "walk") return;
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"].includes(e.code)) {
      e.preventDefault();
    }
    keys.add(e.code);
  });

  window.addEventListener("keyup", (e) => {
    keys.delete(e.code);
  });

  renderer.domElement.addEventListener("pointerdown", (e) => {
    if (isPlayingTour) stopTour();
    transition = null;
    if (mode === "walk") {
      isLooking = true;
      lastPointer = { x: e.clientX, y: e.clientY };
      renderer.domElement.setPointerCapture?.(e.pointerId);
    }
  });

  renderer.domElement.addEventListener("pointermove", (e) => {
    if (mode !== "walk" || !isLooking) return;
    const dx = e.clientX - lastPointer.x;
    const dy = e.clientY - lastPointer.y;
    lastPointer = { x: e.clientX, y: e.clientY };
    yaw -= dx * 0.0042;
    pitch = THREE.MathUtils.clamp(pitch - dy * 0.0036, -1.25, 1.25);
    applyYawPitchToCamera();
  });

  const endLook = () => {
    isLooking = false;
  };
  renderer.domElement.addEventListener("pointerup", endLook);
  renderer.domElement.addEventListener("pointercancel", endLook);

  // Cargar modelo GLB y asignar materiales de render arquitectónico
  const loader = new GLTFLoader();
  loader.load(
    "assets/L8_MEXICO_SKP_3.glb",
    (gltf) => {
      const model = gltf.scene;
      model.traverse((obj) => {
        if (obj.isLine || obj.isLineSegments) {
          skpEdgeLines.push(obj);
          obj.visible = !useRenderStyle;
          return;
        }
        if (obj.isMesh) {
          obj.castShadow = true;
          obj.receiveShadow = true;

          const origMat = obj.material;
          if (origMat) {
            origMat.side = THREE.DoubleSide;
            origMat.clippingPlanes = [clipPlane];
            origMat.clipShadows = true;
          }

          // Distinguir terreno (Geolocation) vs. arquitectura (SKP Vertex Colors)
          const matName = origMat?.name || "";
          const bbox = new THREE.Box3().setFromObject(obj);
          const spanX = bbox.max.x - bbox.min.x;

          let renderMat = whiteStuccoMat;
          if (matName.includes("Geolocation")) {
            renderMat = spanX > 35 ? grassTerrainMat : gravelPadMat;
          }

          skpMeshRecords.push({ mesh: obj, originalMat: origMat, renderMat });
        }
      });

      scene.add(model);
      applyVisualStyle();
      if (statusEl) statusEl.textContent = "Modelo cargado con acabados de render · Inicia el recorrido";
    },
    (xhr) => {
      if (statusEl && xhr.total) {
        const pct = Math.round((xhr.loaded / xhr.total) * 100);
        statusEl.textContent = `Cargando modelo 3D… ${pct}%`;
      }
    },
    (err) => {
      console.error("Error cargando GLB:", err);
      if (fallbackEl) fallbackEl.hidden = false;
      if (statusEl) statusEl.textContent = "No se pudo cargar el modelo 3D";
    }
  );

  const resizeObserver = new ResizeObserver(() => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  resizeObserver.observe(container);

  const clock = new THREE.Clock();
  const moveForward = new THREE.Vector3();
  const moveRight = new THREE.Vector3();

  function easeInOutCubic(x) {
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  }

  function animate() {
    requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.05);

    if (transition) {
      transition.t += dt / transition.duration;
      const k = easeInOutCubic(Math.min(transition.t, 1));
      camera.position.lerpVectors(transition.startPos, transition.endPos, k);
      controls.target.lerpVectors(transition.startTarget, transition.endTarget, k);
      controls.update();

      if (transition.t >= 1) {
        transition = null;
        tourHoldTimer = 0;
      }
    } else if (isPlayingTour) {
      tourHoldTimer += dt;
      if (tourHoldTimer >= 2.6) {
        goToStation(currentStation + 1, 2.2);
      }
    }

    if (mode === "walk") {
      const speed = (keys.has("ShiftLeft") || keys.has("ShiftRight") ? 7.0 : 3.6) * dt;
      const fInput =
        (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0) -
        (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0) +
        touchMove.forward;
      const rInput =
        (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) -
        (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0) +
        touchMove.right;
      const uInput =
        (keys.has("KeyE") ? 1 : 0) - (keys.has("KeyQ") ? 1 : 0) + touchMove.up;

      if (fInput !== 0 || rInput !== 0 || uInput !== 0) {
        camera.getWorldDirection(moveForward);
        moveForward.y = 0;
        moveForward.normalize();
        moveRight.crossVectors(moveForward, camera.up).normalize();

        camera.position.addScaledVector(moveForward, fInput * speed);
        camera.position.addScaledVector(moveRight, rInput * speed);
        camera.position.y = THREE.MathUtils.clamp(camera.position.y + uInput * speed * 0.75, -3.0, 18.0);
      }
    } else {
      controls.update();
    }

    renderer.render(scene, camera);
  }

  animate();
}
