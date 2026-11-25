import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { buildCasaL8Model } from "./casa-l8-model.js";

const container = document.getElementById("viewer-canvas-wrap");
if (container) {
  initViewer();
}

function createSkyDome() {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0.0, "#6fa3d8");
  grad.addColorStop(0.42, "#bad6ee");
  grad.addColorStop(0.54, "#f4f2eb");
  grad.addColorStop(0.62, "#879276");
  grad.addColorStop(1.0, "#5c664a");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 256);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Mesh(
    new THREE.SphereGeometry(180, 32, 24),
    new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false })
  );
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
  const exportGlbBtn = document.getElementById("export-open-glb");
  const walkHud = document.getElementById("walk-hud");
  const clipSlider = document.getElementById("clip-slider");
  const clipValueEl = document.getElementById("clip-value");
  const fullscreenBtn = document.getElementById("viewer-fullscreen");
  const viewerCard = document.getElementById("viewer-card");

  if (fallbackEl) fallbackEl.hidden = true;

  // 7 paradas guiadas calibradas al nuevo modelo abierto (plano A-1 + 5 renders)
  const TOUR_STATIONS = [
    {
      name: "1. Fachada Sur y Vialidad",
      desc: "Volumen superior en voladizo sobre barda perimetral y franja horizontal iluminada.",
      pos: new THREE.Vector3(10.5, 3.2, 34.5),
      target: new THREE.Vector3(8.5, 2.8, 14.0),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-36.jpg",
      lightboxIndex: 1,
    },
    {
      name: "2. Perspectiva Esquina y Voladizo",
      desc: "Ventanal panorámico del 1er nivel, franja cálida inferior y árboles del patio.",
      pos: new THREE.Vector3(26.5, 4.4, 27.5),
      target: new THREE.Vector3(10.0, 2.8, 12.0),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
    {
      name: "3. Fachada Oeste — Celosía y Cochera",
      desc: "Muro monolítico siguiendo la pendiente con celosía vertical de madera en cochera.",
      pos: new THREE.Vector3(-13.5, 3.6, 10.0),
      target: new THREE.Vector3(2.0, 3.6, 9.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-41-14.jpg",
      lightboxIndex: 4,
    },
    {
      name: "4. Patio Jardín y Recámaras (Sótano)",
      desc: "Jardín interior privado con andadores, rocas, árboles en flor, terraza y ventanales.",
      pos: new THREE.Vector3(13.6, 1.65, 7.6),
      target: new THREE.Vector3(8.6, 1.4, 2.8),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-59.jpg",
      lightboxIndex: 3,
    },
    {
      name: "5. Sala, Comedor y Cocina (1ª Planta)",
      desc: "Planta abierta con cocina de mármol e isla oscura, sala en L y vista panorámica.",
      pos: new THREE.Vector3(11.6, 4.95, 17.6),
      target: new THREE.Vector3(11.2, 4.75, 9.2),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-48.jpg",
      lightboxIndex: 2,
    },
    {
      name: "6. Vista Interior Sótano (Recámaras)",
      desc: "Recámaras con ventanales piso a techo hacia el patio jardín y escalera interior.",
      pos: new THREE.Vector3(6.8, 1.65, 13.4),
      target: new THREE.Vector3(6.4, 1.4, 4.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-59.jpg",
      lightboxIndex: 3,
    },
    {
      name: "7. Vista Aérea y Azotea",
      desc: "Conjunto completo sobre el Lote 8: pérgola de cochera, azotea, patio y vialidad.",
      pos: new THREE.Vector3(28.0, 19.5, 29.0),
      target: new THREE.Vector3(7.8, 2.5, 10.0),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
  ];

  // Escena, cielo y renderer
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xd5e4f2);
  scene.fog = new THREE.Fog(0xdce6ee, 68, 170);
  scene.add(createSkyDome());

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.06;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.localClippingEnabled = true;
  container.appendChild(renderer.domElement);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.42;

  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / container.clientHeight,
    0.1,
    350
  );
  camera.position.copy(TOUR_STATIONS[1].pos);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.target.copy(TOUR_STATIONS[1].target);
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minDistance = 1.0;
  controls.maxDistance = 95;
  controls.update();

  // Iluminación arquitectónica cálida + luces interiores
  const hemiLight = new THREE.HemisphereLight(0xeef6ff, 0x7c8468, 0.95);
  hemiLight.position.set(0, 45, 0);
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xfff4e0, 2.15);
  sunLight.position.set(32, 38, 22);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 120;
  sunLight.shadow.camera.left = -32;
  sunLight.shadow.camera.right = 32;
  sunLight.shadow.camera.top = 32;
  sunLight.shadow.camera.bottom = -32;
  sunLight.shadow.bias = -0.0004;
  scene.add(sunLight);

  const fillLight = new THREE.DirectionalLight(0xcfe2f7, 0.55);
  fillLight.position.set(-24, 22, -18);
  scene.add(fillLight);

  // Luces cálidas en Primera Planta (Cocina/Sala) y Sótano (Patio/Recámaras)
  const livingLight = new THREE.PointLight(0xffdca6, 16, 18, 1.5);
  livingLight.position.set(11.4, 5.7, 13.0);
  scene.add(livingLight);

  const patioLight = new THREE.PointLight(0xffd292, 14, 16, 1.5);
  patioLight.position.set(11.8, 2.2, 4.0);
  scene.add(patioLight);

  const bedLight = new THREE.PointLight(0xffd699, 10, 14, 1.6);
  bedLight.position.set(5.2, 2.3, 11.5);
  scene.add(bedLight);

  // Plano de corte horizontal (Y = 0..8.5 m)
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 8.5);

  // Construir modelo paramétrico abierto desde A-1
  const { root: casaRoot, layers } = buildCasaL8Model(clipPlane);
  scene.add(casaRoot);

  // Toggles de niveles arquitectónicos (Azotea, 1ª Planta, Sótano)
  document.querySelectorAll("[data-layer]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.layer;
      if (!layers[key]) return;
      layers[key].visible = !layers[key].visible;
      btn.classList.toggle("is-active", layers[key].visible);
    });
  });

  // Exportar modelo abierto a .GLB (estándar abierto Khronos, sin SketchUp)
  exportGlbBtn?.addEventListener("click", () => {
    if (statusEl) statusEl.textContent = "Exportando modelo abierto a .GLB…";
    const exporter = new GLTFExporter();
    exporter.parse(
      casaRoot,
      (binary) => {
        const blob = new Blob([binary], { type: "model/gltf-binary" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "Casa_L8_M147_Modelo_Abierto.glb";
        a.click();
        URL.revokeObjectURL(url);
        if (statusEl) statusEl.textContent = "Modelo abierto exportado (Casa_L8_M147_Modelo_Abierto.glb)";
      },
      (err) => {
        console.error(err);
        if (statusEl) statusEl.textContent = "Error al exportar .GLB";
      },
      { binary: true }
    );
  });

  // Estado de recorrido y caminar
  let mode = "orbit";
  let currentStation = 1; // Inicia en Perspectiva Esquina y Voladizo
  let isPlayingTour = false;
  let tourHoldTimer = 0;
  let transition = null;

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
    camera.quaternion.setFromEuler(new THREE.Euler(pitch, yaw, 0, "YXZ"));
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
      if (camera.position.distanceTo(new THREE.Vector3(8, 3, 10)) > 24) {
        camera.position.set(11.6, 4.95, 17.2);
        camera.lookAt(11.0, 4.75, 9.5);
      }
      syncYawPitchFromCamera();
      if (statusEl) statusEl.textContent = "Modo Caminar · WASD/Flechas + arrastra para mirar";
    } else {
      controls.enabled = true;
      const forward = new THREE.Vector3();
      camera.getWorldDirection(forward);
      controls.target.copy(camera.position).addScaledVector(forward, 6);
      controls.update();
      if (statusEl) statusEl.textContent = "Modelo abierto listo (Plano A-1) · Explora o inicia el recorrido";
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
      btn.className = "tour-dot" + (idx === currentStation ? " is-active" : "");
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
  if (statusEl) statusEl.textContent = "Modelo paramétrico abierto (Plano A-1) · 7 paradas guiadas";

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
      if (y < 2.5) {
        camera.position.set(12.2, y, 7.2);
        camera.lookAt(8.5, y - 0.1, 3.0);
      } else if (y < 6.0) {
        camera.position.set(11.6, y, 17.2);
        camera.lookAt(11.0, y - 0.1, 9.5);
      } else {
        camera.position.set(12.0, y, 17.5);
        camera.lookAt(7.5, 6.2, 9.0);
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
        clipValueEl.textContent = val >= 8.4 ? "Completo" : `Corte ${val.toFixed(1)} m`;
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
  window.addEventListener("keyup", (e) => keys.delete(e.code));

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
        camera.position.y = THREE.MathUtils.clamp(camera.position.y + uInput * speed * 0.75, 0.6, 18.0);
      }
    } else {
      controls.update();
    }

    renderer.render(scene, camera);
  }

  animate();
}
