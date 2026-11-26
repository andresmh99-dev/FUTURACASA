import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const container = document.getElementById("viewer-canvas-wrap");
if (container) {
  initViewer();
}

function createSkyDome() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0.0, "#5e97d4");
  grad.addColorStop(0.36, "#b7d4ee");
  grad.addColorStop(0.51, "#f7f5f0");
  grad.addColorStop(0.58, "#8c967a");
  grad.addColorStop(1.0, "#556044");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 256);

  for (let i = 0; i < 24; i++) {
    const cx = Math.random() * 512;
    const cy = 24 + Math.random() * 76;
    const rx = 28 + Math.random() * 75;
    const ry = 6 + Math.random() * 14;
    const cg = ctx.createRadialGradient(cx, cy, 2, cx, cy, rx);
    cg.addColorStop(0, "rgba(255,255,255,0.46)");
    cg.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = cg;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(1, ry / rx);
    ctx.beginPath();
    ctx.arc(0, 0, rx, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Mesh(
    new THREE.SphereGeometry(185, 36, 24),
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

  // 7 paradas guiadas calibradas al modelo exacto 1:1 de Blender (assets/casa_l8_abierta.glb)
  // Coordenadas Three.js: X = [0..15.07], Y = [0.00 Patio .. 3.24 Sala .. 6.15 Techo], Z = [-20.6 Norte .. 0.0 Sur]
  const TOUR_STATIONS = [
    {
      name: "1. Fachada Sur y Vialidad",
      desc: "Volumen superior en voladizo 1:1 sobre barda perimetral, franja LED y vialidad curva.",
      pos: new THREE.Vector3(5.2, 2.9, 14.5),
      target: new THREE.Vector3(7.4, 3.2, -3.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-36.jpg",
      lightboxIndex: 1,
    },
    {
      name: "2. Perspectiva Esquina y Voladizo",
      desc: "Ventanal panorámico del 1er nivel, franja cálida inferior y árboles en flor del patio.",
      pos: new THREE.Vector3(17.8, 3.3, 10.0),
      target: new THREE.Vector3(7.5, 3.4, -3.6),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
    {
      name: "3. Fachada Oeste — Celosía y Cochera",
      desc: "Muro monolítico siguiendo la pendiente con celosía de madera y pérgola en cochera.",
      pos: new THREE.Vector3(-12.2, 4.0, -11.5),
      target: new THREE.Vector3(3.5, 3.9, -11.8),
      render: "assets/galeria/PHOTO-2025-12-28-22-41-14.jpg",
      lightboxIndex: 4,
    },
    {
      name: "4. Patio Jardín y Recámaras (PB)",
      desc: "Jardín interior privado con deck de pizarra, sillones de rattan, rocas, lavanda y canceles.",
      pos: new THREE.Vector3(11.2, 1.65, -4.4),
      target: new THREE.Vector3(11.8, 1.45, -11.4),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-59.jpg",
      lightboxIndex: 3,
    },
    {
      name: "5. Sala, Comedor y Cocina (1ª Planta)",
      desc: "Cocina Calacatta hasta plafón, isla real, sofá entallado, comedor de vidrio y pasillo.",
      pos: new THREE.Vector3(4.2, 4.55, -1.2),
      target: new THREE.Vector3(5.8, 4.40, -5.6),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-48.jpg",
      lightboxIndex: 2,
    },
    {
      name: "6. Recámara Principal y Planta Baja",
      desc: "Recámaras con cabecera acanalada, cuadros de galería y salida directa al patio jardín.",
      pos: new THREE.Vector3(7.5, 1.72, -3.7),
      target: new THREE.Vector3(6.2, 1.35, -2.2),
      render: "assets/galeria/PHOTO-2025-12-28-22-40-59.jpg",
      lightboxIndex: 3,
    },
    {
      name: "7. Vista Aérea y Conjunto 1:1",
      desc: "Vista completa del proyecto 1:1 sobre el Lote 8: pérgola, azotea, patio y calle curva.",
      pos: new THREE.Vector3(24.5, 16.0, 11.0),
      target: new THREE.Vector3(7.5, 3.2, -9.5),
      render: "assets/galeria/PHOTO-2025-12-28-22-39-50.jpg",
      lightboxIndex: 0,
    },
  ];

  // Escena, cielo y renderer
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xd5e4f2);
  scene.fog = new THREE.Fog(0xdce6ee, 55, 160);
  scene.add(createSkyDome());

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.localClippingEnabled = true;
  container.appendChild(renderer.domElement);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.48;

  const camera = new THREE.PerspectiveCamera(
    48,
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
  controls.minDistance = 0.8;
  controls.maxDistance = 85;
  controls.update();

  // Iluminación arquitectónica Suroeste sincronizada con Blender Cycles
  const hemiLight = new THREE.HemisphereLight(0xeef6ff, 0x7c8468, 0.92);
  hemiLight.position.set(0, 45, 0);
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xfff1d6, 2.25);
  sunLight.position.set(-24, 24, 22);
  sunLight.target.position.set(7.5, 2.5, -9.0);
  scene.add(sunLight.target);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.camera.near = 4;
  sunLight.shadow.camera.far = 110;
  sunLight.shadow.camera.left = -28;
  sunLight.shadow.camera.right = 28;
  sunLight.shadow.camera.top = 28;
  sunLight.shadow.camera.bottom = -28;
  sunLight.shadow.bias = -0.0005;
  scene.add(sunLight);

  const fillLight = new THREE.DirectionalLight(0xd2e4f8, 0.65);
  fillLight.position.set(28, 18, -22);
  scene.add(fillLight);

  // Luces interiores cálidas (1ª Planta y Planta Baja)
  const livingLight = new THREE.PointLight(0xffdfb0, 18, 16, 1.4);
  livingLight.position.set(5.4, 5.6, -3.5);
  scene.add(livingLight);

  const kitchenLight = new THREE.PointLight(0xffd28a, 16, 12, 1.5);
  kitchenLight.position.set(5.6, 5.2, -6.5);
  scene.add(kitchenLight);

  const patioLight = new THREE.PointLight(0xffd494, 14, 16, 1.45);
  patioLight.position.set(11.8, 2.4, -9.0);
  scene.add(patioLight);

  const bedLight1 = new THREE.PointLight(0xffd28a, 14, 12, 1.5);
  bedLight1.position.set(6.5, 2.2, -2.5);
  scene.add(bedLight1);

  const bedLight2 = new THREE.PointLight(0xffd28a, 14, 12, 1.5);
  bedLight2.position.set(6.4, 2.2, -9.5);
  scene.add(bedLight2);

  // Plano de corte horizontal (Y = 0.5 .. 8.5 m)
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 8.5);

  // Grupos por nivel para los botones Azotea / 1ª Planta / Sótano
  const layerMeshes = {
    azotea: [],
    primeraPlanta: [],
    sotano: [],
  };
  const layerVisible = {
    azotea: true,
    primeraPlanta: true,
    sotano: true,
  };

  if (statusEl) statusEl.textContent = "Cargando modelo 3D abierto 1:1 amueblado (.GLB)…";

  const loader = new GLTFLoader();
  loader.load(
    "assets/casa_l8_abierta.glb",
    (gltf) => {
      const root = gltf.scene;
      scene.add(root);
      root.updateMatrixWorld(true);

      const box = new THREE.Box3();
      const center = new THREE.Vector3();

      root.traverse((child) => {
        if (!child.isMesh) return;
        const name = child.name || "";
        const isTerrain = name.includes("Terreno") || name.includes("Vialidad");
        const isGlass =
          (child.material && child.material.name === "Vidrio_ArchViz") ||
          name.includes("Glass") ||
          name.includes("Vidrio");
        const isLeaf =
          name.includes("leaf") || name.includes("blossom") || name.includes("Lavanda");

        child.castShadow = !isGlass && !isTerrain;
        child.receiveShadow = !isGlass;

        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach((m) => {
          if (!m) return;
          if (!isTerrain) {
            m.clippingPlanes = [clipPlane];
            m.clipShadows = true;
          }
          if (isGlass) {
            m.transparent = true;
            m.opacity = 0.24;
            m.depthWrite = false;
            m.side = THREE.DoubleSide;
          } else if (isLeaf) {
            m.side = THREE.DoubleSide;
          }
          m.needsUpdate = true;
        });

        // Clasificar malla en capa de nivel (sin ocultar terreno ni calle)
        if (!isTerrain && !name.startsWith("mesh-")) {
          box.setFromObject(child);
          box.getCenter(center);
          if (
            name.includes("Pergola") ||
            name.includes("Sellado_Plafon_1P") ||
            name.includes("Marquesina") ||
            name.includes("Viga_") ||
            center.y >= 5.95
          ) {
            layerMeshes.azotea.push(child);
          } else if (center.y >= 2.85) {
            layerMeshes.primeraPlanta.push(child);
          } else {
            layerMeshes.sotano.push(child);
          }
        }
      });

      if (statusEl) {
        statusEl.textContent = "Modelo 3D abierto 1:1 cargado (sincronizado con Recorrido 360°) · 7 paradas";
      }
    },
    undefined,
    (err) => {
      console.error("Error cargando assets/casa_l8_abierta.glb:", err);
      if (fallbackEl) fallbackEl.hidden = false;
      if (statusEl) statusEl.textContent = "No se pudo cargar el modelo .GLB (requiere servidor HTTP/HTTPS)";
    }
  );

  // Toggles de niveles arquitectónicos (Azotea, 1ª Planta, Sótano)
  document.querySelectorAll("[data-layer]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.layer;
      if (!(key in layerVisible)) return;
      layerVisible[key] = !layerVisible[key];
      layerMeshes[key].forEach((mesh) => {
        mesh.visible = layerVisible[key];
      });
      btn.classList.toggle("is-active", layerVisible[key]);
      // Si ocultan Azotea, ajustar clipPlane a 6.05 m para abrir también el techo real de mesh-0!
      if (key === "azotea" && clipSlider) {
        const targetClip = layerVisible.azotea ? 8.5 : 5.95;
        clipSlider.value = String(targetClip);
        clipPlane.constant = targetClip;
        if (clipValueEl) {
          clipValueEl.textContent = targetClip >= 8.4 ? "Completo" : `Corte ${targetClip.toFixed(1)} m`;
        }
      }
    });
  });

  // Descargar directamente el modelo abierto 1:1 (.GLB exportado desde Blender 5.3)
  exportGlbBtn?.addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = "assets/casa_l8_abierta.glb";
    a.download = "Casa_L8_M147_Modelo_Abierto_1a1.glb";
    a.click();
    if (statusEl) statusEl.textContent = "Descargando Casa_L8_M147_Modelo_Abierto_1a1.glb (6.3 MB)";
  });

  // Estado de recorrido y caminar
  let mode = "orbit";
  let currentStation = 1;
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
      if (camera.position.distanceTo(new THREE.Vector3(7.5, 3.0, -7.0)) > 22) {
        camera.position.set(4.4, 4.65, -1.6);
        camera.lookAt(5.8, 4.45, -6.2);
      }
      syncYawPitchFromCamera();
      if (statusEl) statusEl.textContent = "Modo Caminar 1:1 · WASD/Flechas + arrastra para mirar";
    } else {
      controls.enabled = true;
      const forward = new THREE.Vector3();
      camera.getWorldDirection(forward);
      controls.target.copy(camera.position).addScaledVector(forward, 6);
      controls.update();
      if (statusEl) statusEl.textContent = "Modelo 3D abierto 1:1 · Explora libremente o inicia el recorrido";
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
        camera.position.set(11.2, 1.65, -4.8);
        camera.lookAt(11.8, 1.45, -11.4);
      } else if (y < 6.0) {
        camera.position.set(4.4, 4.65, -1.6);
        camera.lookAt(5.8, 4.45, -6.2);
      } else {
        camera.position.set(12.0, 7.6, -2.0);
        camera.lookAt(7.5, 5.8, -9.5);
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
      const speed = (keys.has("ShiftLeft") || keys.has("ShiftRight") ? 6.5 : 3.4) * dt;
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
        camera.position.y = THREE.MathUtils.clamp(camera.position.y + uInput * speed * 0.75, 0.5, 16.0);
      }
    } else {
      controls.update();
    }

    renderer.render(scene, camera);
  }

  animate();
}
