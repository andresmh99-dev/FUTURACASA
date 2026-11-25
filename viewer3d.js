import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const container = document.getElementById("viewer-canvas-wrap");
if (container) {
  initViewer();
}

function initViewer() {
  const statusEl = document.getElementById("viewer-status");
  const fallbackEl = document.getElementById("viewer-fallback");
  const stationTitleEl = document.getElementById("tour-station-title");
  const stationDescEl = document.getElementById("tour-station-desc");
  const stationDotsEl = document.getElementById("tour-dots");
  const playBtn = document.getElementById("tour-play");
  const prevBtn = document.getElementById("tour-prev");
  const nextBtn = document.getElementById("tour-next");
  const modeOrbitBtn = document.getElementById("mode-orbit");
  const modeWalkBtn = document.getElementById("mode-walk");
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

  // Paradas calibradas a las coordenadas reales de L8_MEXICO_SKP_3.glb
  // Casa: X [3.2..24.7], Y [-3.4..3.3], Z [-3.0..22.0]
  const TOUR_STATIONS = [
    {
      name: "1. Fachada Principal",
      desc: "Aproximación exterior desde el frente del predio hacia el volumen superior en voladizo.",
      pos: new THREE.Vector3(14.0, 2.2, 30.5),
      target: new THREE.Vector3(13.5, 0.4, 10.5),
    },
    {
      name: "2. Acceso y Cochera",
      desc: "Llegada a nivel de acceso y área de cochera sobre la pendiente del terreno.",
      pos: new THREE.Vector3(10.5, -1.4, 21.5),
      target: new THREE.Vector3(13.8, -1.2, 11.0),
    },
    {
      name: "3. Planta Baja",
      desc: "Recorrido interior en planta baja (nivel base del proyecto arquitectónico).",
      pos: new THREE.Vector3(13.5, -1.65, 14.5),
      target: new THREE.Vector3(12.2, -1.4, 5.5),
    },
    {
      name: "4. Primer Nivel",
      desc: "Vista interior del primer nivel (espacio principal con vano panorámico).",
      pos: new THREE.Vector3(12.8, 1.45, 13.6),
      target: new THREE.Vector3(11.8, 1.35, 6.8),
    },
    {
      name: "5. Perspectiva Lateral",
      desc: "Relación del volumen habitacional con los muros laterales y la topografía.",
      pos: new THREE.Vector3(0.8, 2.4, 16.5),
      target: new THREE.Vector3(13.5, 0.5, 10.0),
    },
    {
      name: "6. Vista Aérea",
      desc: "Implantación completa de la casa sobre el Lote 8 y el terreno inclinado.",
      pos: new THREE.Vector3(29.0, 15.5, 27.0),
      target: new THREE.Vector3(13.5, 0.0, 10.0),
    },
  ];

  // Escena y renderer
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xebe8e0);
  scene.fog = new THREE.Fog(0xebe8e0, 55, 130);

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

  // Cámara y controles de órbita
  const camera = new THREE.PerspectiveCamera(
    52,
    container.clientWidth / container.clientHeight,
    0.1,
    300
  );
  camera.position.copy(TOUR_STATIONS[0].pos);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.target.copy(TOUR_STATIONS[0].target);
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minDistance = 1.2;
  controls.maxDistance = 85;
  controls.update();

  // Iluminación arquitectónica
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0xc9c2b4, 1.15);
  hemiLight.position.set(0, 30, 0);
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xfff7ea, 1.8);
  sunLight.position.set(28, 36, 24);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 110;
  sunLight.shadow.camera.left = -35;
  sunLight.shadow.camera.right = 35;
  sunLight.shadow.camera.top = 35;
  sunLight.shadow.camera.bottom = -35;
  sunLight.shadow.bias = -0.0005;
  scene.add(sunLight);

  const fillLight = new THREE.DirectionalLight(0xdbe8f8, 0.55);
  fillLight.position.set(-22, 18, -18);
  scene.add(fillLight);

  // Plano de corte horizontal (maqueta seccionada)
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 6.0);
  const clipMaterials = [];

  // Estado de navegación
  let mode = "orbit"; // "orbit" | "walk"
  let currentStation = 0;
  let isPlayingTour = false;
  let tourHoldTimer = 0;

  // Transición suave de cámara
  let transition = null; // { startPos, endPos, startTarget, endTarget, t, duration }

  // Estado modo caminar (primera persona)
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
      // Si la cámara está muy lejos, colocarla en el acceso de la casa
      if (camera.position.distanceTo(new THREE.Vector3(13.5, 0, 10.5)) > 26) {
        camera.position.set(13.0, 1.45, 13.8);
        camera.lookAt(12.2, 1.35, 7.0);
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

  // Construir indicadores de paradas
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

  // Botones de recorrido
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

  // Botones de modo
  modeOrbitBtn?.addEventListener("click", () => setMode("orbit"));
  modeWalkBtn?.addEventListener("click", () => setMode("walk"));

  // Botones de planta rápida (en modo caminar)
  document.querySelectorAll("[data-floor-y]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (mode !== "walk") setMode("walk");
      const y = parseFloat(btn.dataset.floorY);
      camera.position.set(13.0, y, 13.5);
      camera.lookAt(12.2, y - 0.1, 6.8);
      syncYawPitchFromCamera();
    });
  });

  // Cruceta táctil / botones en pantalla para caminar
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

  // Slider de corte horizontal
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

  // Pantalla completa
  fullscreenBtn?.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      viewerCard?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  });

  // Eventos de teclado y mouse para Modo Caminar
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

  // Cargar modelo GLB
  const loader = new GLTFLoader();
  loader.load(
    "assets/L8_MEXICO_SKP_3.glb",
    (gltf) => {
      const model = gltf.scene;
      model.traverse((obj) => {
        if (obj.isMesh) {
          obj.castShadow = true;
          obj.receiveShadow = true;
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach((m) => {
            if (!m) return;
            m.side = THREE.DoubleSide;
            m.clippingPlanes = [clipPlane];
            m.clipShadows = true;
            clipMaterials.push(m);
          });
        }
      });
      scene.add(model);
      if (statusEl) statusEl.textContent = "Modelo cargado · Inicia el recorrido o explora libremente";
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

  // Resize
  const resizeObserver = new ResizeObserver(() => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  resizeObserver.observe(container);

  // Loop de animación
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
      // Pausa suave de 2.4 s en cada parada antes de avanzar a la siguiente
      if (tourHoldTimer >= 2.4) {
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
