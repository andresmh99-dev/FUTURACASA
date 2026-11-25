import * as THREE from "three";

/**
 * Visor de Recorrido Virtual 360° Fotorealista (renderizado con Blender 5 Cycles)
 * Esfera equirectangular en Three.js con hotspots interactivos 3D y transiciones suaves.
 */

const wrap = document.getElementById("tour360-canvas-wrap");
if (wrap) {
  initTour360();
}

function initTour360() {
  const hotspotsLayer = document.getElementById("tour360-hotspots");
  const titleEl = document.getElementById("tour360-title");
  const descEl = document.getElementById("tour360-desc");
  const navStrip = document.getElementById("tour360-stops");
  const autoBtn = document.getElementById("tour360-autopan");
  const fsBtn = document.getElementById("tour360-fullscreen");
  const cardEl = document.getElementById("tour360-card");
  const statusEl = document.getElementById("tour360-status");

  const SCENES = [
    {
      id: "fachada",
      label: "1. Fachada y Voladizo",
      desc: "Vista 360° exterior renderizada en Blender 5 Cycles desde la esquina del Lote 8.",
      src: "assets/panoramas/01_fachada_esquina.jpg",
      initialYaw: 2.35,
      initialPitch: 0.04,
      hotspots: [
        { target: "patio", label: "Entrar al Patio Jardín", yaw: 2.55, pitch: -0.04 },
        { target: "sala", label: "Subir a Sala y Cocina", yaw: 2.22, pitch: 0.12 },
        { target: "celosia", label: "Ir a Fachada Oeste (Celosía)", yaw: 1.65, pitch: -0.02 },
      ],
    },
    {
      id: "patio",
      label: "2. Patio Jardín",
      desc: "Jardín interior privado con árboles, rocas volcánicas, terraza de estar y ventanales.",
      src: "assets/panoramas/02_patio_jardin.jpg",
      initialYaw: -1.75,
      initialPitch: 0.02,
      hotspots: [
        { target: "recamara", label: "Entrar a Recámaras (Sótano)", yaw: 0.95, pitch: -0.04 },
        { target: "sala", label: "Subir a Sala / Cocina (1ª Planta)", yaw: -0.5, pitch: 0.25 },
        { target: "fachada", label: "Salir a Fachada Exterior", yaw: -2.6, pitch: 0.02 },
      ],
    },
    {
      id: "sala",
      label: "3. Sala, Comedor y Cocina",
      desc: "Planta abierta en 1er nivel con cocina de mármol, isla oscura, sala en L y vista panorámica.",
      src: "assets/panoramas/03_sala_cocina.jpg",
      initialYaw: -2.05,
      initialPitch: -0.04,
      hotspots: [
        { target: "patio", label: "Bajar al Patio Jardín", yaw: -2.65, pitch: -0.14 },
        { target: "recamara", label: "Bajar a Recámaras", yaw: 2.45, pitch: -0.14 },
        { target: "fachada", label: "Ver Exterior desde Calle", yaw: -1.25, pitch: -0.04 },
      ],
    },
    {
      id: "recamara",
      label: "4. Recámaras (Sótano)",
      desc: "Interior de recámara con cabecera acanalada, clóset de madera, cuadros y vista al patio.",
      src: "assets/panoramas/04_recamara.jpg",
      initialYaw: -1.35,
      initialPitch: -0.02,
      hotspots: [
        { target: "patio", label: "Salir al Patio Jardín", yaw: -2.55, pitch: -0.04 },
        { target: "sala", label: "Subir a Sala y Cocina", yaw: -0.75, pitch: 0.14 },
      ],
    },
    {
      id: "celosia",
      label: "5. Fachada Oeste y Celosía",
      desc: "Vista 360° sobre la pendiente vial hacia la fachada monolítica y celosía vertical de madera.",
      src: "assets/panoramas/05_fachada_celosia.jpg",
      initialYaw: -1.55,
      initialPitch: 0.03,
      hotspots: [
        { target: "fachada", label: "Rodear a Fachada Principal", yaw: -0.95, pitch: -0.04 },
        { target: "sala", label: "Entrar a 1ª Planta", yaw: -1.65, pitch: 0.08 },
      ],
    },
  ];

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(72, wrap.clientWidth / wrap.clientHeight, 0.1, 200);
  camera.position.set(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  wrap.prepend(renderer.domElement);

  const sphereGeo = new THREE.SphereGeometry(50, 64, 40);
  sphereGeo.scale(-1, 1, 1);
  const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const sphere = new THREE.Mesh(sphereGeo, sphereMat);
  scene.add(sphere);

  const texLoader = new THREE.TextureLoader();
  const texCache = new Map();

  let currentIdx = 0;
  let yaw = SCENES[0].initialYaw;
  let pitch = SCENES[0].initialPitch;
  let fov = 72;
  let autoPan = true;
  let isDragging = false;
  let lastPtr = { x: 0, y: 0 };
  let hotspotEls = [];

  function loadScene(idx) {
    currentIdx = (idx + SCENES.length) % SCENES.length;
    const st = SCENES[currentIdx];
    yaw = st.initialYaw;
    pitch = st.initialPitch;

    if (titleEl) titleEl.textContent = st.label;
    if (descEl) descEl.textContent = st.desc;
    if (statusEl) statusEl.textContent = `Cargando panorama 360° (${st.label})…`;

    if (navStrip) {
      navStrip.querySelectorAll("button").forEach((b, i) => {
        b.classList.toggle("is-active", i === currentIdx);
      });
    }

    const applyTex = (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.minFilter = THREE.LinearFilter;
      sphereMat.map = tex;
      sphereMat.needsUpdate = true;
      if (statusEl) statusEl.textContent = "Arrastra 360° para mirar · Haz clic en los puntos para recorrer la casa";
    };

    if (texCache.has(st.src)) {
      applyTex(texCache.get(st.src));
    } else {
      texLoader.load(
        st.src,
        (tex) => {
          texCache.set(st.src, tex);
          applyTex(tex);
        },
        undefined,
        () => {
          if (statusEl) statusEl.textContent = "Panorama 360° pendiente de renderizar en Blender.";
        }
      );
    }

    buildHotspots(st);
  }

  function buildHotspots(st) {
    if (!hotspotsLayer) return;
    hotspotsLayer.innerHTML = "";
    hotspotEls = st.hotspots.map((hs) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hotspot-pin";
      btn.innerHTML = `<span class="hotspot-dot"></span><span>${hs.label}</span>`;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const targetIdx = SCENES.findIndex((s) => s.id === hs.target);
        if (targetIdx >= 0) loadScene(targetIdx);
      });
      hotspotsLayer.appendChild(btn);
      const dir = new THREE.Vector3(
        Math.cos(hs.pitch) * Math.sin(hs.yaw),
        Math.sin(hs.pitch),
        -Math.cos(hs.pitch) * Math.cos(hs.yaw)
      ).multiplyScalar(25);
      return { btn, pos3D: dir };
    });
  }

  if (navStrip) {
    navStrip.innerHTML = "";
    SCENES.forEach((st, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn" + (idx === 0 ? " is-active" : "");
      btn.textContent = st.label;
      btn.addEventListener("click", () => loadScene(idx));
      navStrip.appendChild(btn);
    });
  }

  autoBtn?.addEventListener("click", () => {
    autoPan = !autoPan;
    autoBtn.classList.toggle("is-active", autoPan);
  });

  fsBtn?.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      cardEl?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  });

  renderer.domElement.addEventListener("pointerdown", (e) => {
    isDragging = true;
    autoPan = false;
    autoBtn?.classList.remove("is-active");
    lastPtr = { x: e.clientX, y: e.clientY };
    renderer.domElement.setPointerCapture?.(e.pointerId);
  });

  renderer.domElement.addEventListener("pointermove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - lastPtr.x;
    const dy = e.clientY - lastPtr.y;
    lastPtr = { x: e.clientX, y: e.clientY };
    yaw -= dx * 0.0045;
    pitch = THREE.MathUtils.clamp(pitch + dy * 0.004, -1.15, 1.15);
  });

  const stopDrag = () => {
    isDragging = false;
  };
  renderer.domElement.addEventListener("pointerup", stopDrag);
  renderer.domElement.addEventListener("pointercancel", stopDrag);

  renderer.domElement.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      fov = THREE.MathUtils.clamp(fov + e.deltaY * 0.04, 38, 92);
      camera.fov = fov;
      camera.updateProjectionMatrix();
    },
    { passive: false }
  );

  const resizeObserver = new ResizeObserver(() => {
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  resizeObserver.observe(wrap);

  const proj = new THREE.Vector3();

  function animate() {
    requestAnimationFrame(animate);
    if (autoPan && !isDragging) {
      yaw += 0.0012;
    }

    const lookTarget = new THREE.Vector3(
      Math.cos(pitch) * Math.sin(yaw),
      Math.sin(pitch),
      -Math.cos(pitch) * Math.cos(yaw)
    );
    camera.lookAt(lookTarget);
    renderer.render(scene, camera);

    // Proyectar hotspots 3D a coordenadas 2D de pantalla
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    hotspotEls.forEach(({ btn, pos3D }) => {
      proj.copy(pos3D).project(camera);
      const visible = proj.z < 1.0 && Math.abs(proj.x) <= 1.05 && Math.abs(proj.y) <= 1.05;
      if (visible) {
        const sx = (proj.x * 0.5 + 0.5) * w;
        const sy = (-proj.y * 0.5 + 0.5) * h;
        btn.style.transform = `translate(-50%, -50%) translate(${sx.toFixed(1)}px, ${sy.toFixed(1)}px)`;
        btn.style.opacity = "1";
        btn.style.pointerEvents = "auto";
      } else {
        btn.style.opacity = "0";
        btn.style.pointerEvents = "none";
      }
    });
  }

  loadScene(0);
  animate();
}
