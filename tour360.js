import * as THREE from "three";

/**
 * Visor de Recorrido Virtual 360° Fotorealista (8 paradas — Blender 5 Cycles)
 * Cubre fachada exterior, entrada principal/cochera, pasillo/escaleras, sala/cocina,
 * patio jardín, recámara principal y recámaras/sala TV de planta baja.
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
      desc: "Modelo exacto 1:1 (15.07 m × 20.60 m) desde esquina Sur-Este con volumen en voladizo y árboles del patio.",
      src: "assets/panoramas/01_fachada_esquina.jpg",
      initialYaw: 2.38,
      initialPitch: 0.04,
      hotspots: [
        { target: "entrada", label: "Ir a Entrada y Cochera", yaw: 1.85, pitch: 0.02 },
        { target: "sala", label: "Subir a Sala y Cocina", yaw: 2.28, pitch: 0.12 },
        { target: "patio", label: "Entrar al Patio Jardín", yaw: 2.65, pitch: -0.02 },
      ],
    },
    {
      id: "entrada",
      label: "2. Entrada y Cochera",
      desc: "Cochera real a nivel calle con celosía de madera, pérgola, macetero y puerta pivotante principal.",
      src: "assets/panoramas/02_fachada_entrada.jpg",
      initialYaw: 0.78,
      initialPitch: 0.02,
      hotspots: [
        { target: "pasillo", label: "Entrar al Pasillo y Escaleras", yaw: 0.78, pitch: -0.02 },
        { target: "celosia", label: "Salir a Fachada Oeste", yaw: -2.4, pitch: -0.03 },
        { target: "patio", label: "Ver Patio Jardín", yaw: 0.35, pitch: -0.08 },
      ],
    },
    {
      id: "pasillo",
      label: "3. Pasillo y Escaleras (PA)",
      desc: "Pasillo real de planta alta con escaleras hacia sótano, cocina con isla, sala en L y ventanal panorámico.",
      src: "assets/panoramas/03_pasillo_escaleras.jpg",
      initialYaw: -1.65,
      initialPitch: -0.04,
      hotspots: [
        { target: "sala", label: "Avanzar a Sala y Comedor", yaw: -1.15, pitch: -0.02 },
        { target: "recamaras_tv", label: "Bajar escaleras a Planta Baja", yaw: -2.95, pitch: -0.10 },
        { target: "entrada", label: "Salir a Entrada Principal", yaw: -2.25, pitch: -0.02 },
      ],
    },
    {
      id: "sala",
      label: "4. Sala, Comedor y Cocina",
      desc: "Área social 1:1 en nivel superior: cocina de mármol e isla real, sala en L, comedor y ventanal panorámico.",
      src: "assets/panoramas/04_sala_cocina.jpg",
      initialYaw: -2.25,
      initialPitch: -0.04,
      hotspots: [
        { target: "pasillo", label: "Ir al Pasillo y Escaleras", yaw: -2.75, pitch: -0.04 },
        { target: "patio", label: "Bajar al Patio Jardín", yaw: -1.65, pitch: -0.12 },
        { target: "fachada", label: "Ver Fachada Exterior", yaw: -0.75, pitch: -0.04 },
      ],
    },
    {
      id: "patio",
      label: "5. Patio Jardín (PB)",
      desc: "Patio real (6.1 m × 13.4 m) con árboles en flor, sombras moteadas, rocas, lavanda, terraza y los 3 cuartos.",
      src: "assets/panoramas/05_patio_jardin.jpg",
      initialYaw: -2.05,
      initialPitch: 0.02,
      hotspots: [
        { target: "recamara_principal", label: "Entrar a Recámara Principal", yaw: 1.15, pitch: -0.04 },
        { target: "recamaras_tv", label: "Entrar a Recámaras 1 y 2 / TV", yaw: -2.85, pitch: -0.04 },
        { target: "sala", label: "Subir a Sala y Cocina (PA)", yaw: 0.95, pitch: 0.24 },
      ],
    },
    {
      id: "recamara_principal",
      label: "6. Recámara Principal (PB)",
      desc: "Recámara Principal real (Z = -2.89 m) con vestidor al fondo, escalera por pasillo, cuadros y salida al jardín.",
      src: "assets/panoramas/06_recamara_principal.jpg",
      initialYaw: 0.55,
      initialPitch: -0.04,
      hotspots: [
        { target: "patio", label: "Salir al Patio Jardín", yaw: -1.35, pitch: -0.02 },
        { target: "recamaras_tv", label: "Ir a Recámaras 1 y 2 / TV", yaw: 2.35, pitch: -0.02 },
      ],
    },
    {
      id: "recamaras_tv",
      label: "7. Recámaras 1, 2 y Sala TV",
      desc: "Cuarto Norte de planta baja con mueble TV, cama, cuadros, vista directa a la terraza del jardín y acceso a escaleras.",
      src: "assets/panoramas/07_recamaras_sala_tv.jpg",
      initialYaw: -1.55,
      initialPitch: -0.02,
      hotspots: [
        { target: "patio", label: "Salir a Terraza del Jardín", yaw: -1.55, pitch: -0.04 },
        { target: "pasillo", label: "Subir escaleras a Planta Alta", yaw: 0.85, pitch: 0.12 },
        { target: "recamara_principal", label: "Ir a Recámara Principal", yaw: 0.55, pitch: -0.02 },
      ],
    },
    {
      id: "celosia",
      label: "8. Fachada Oeste y Celosía",
      desc: "Fachada Oeste exacta sobre la pendiente vial con el volumen blanco monolítico y celosía vertical de madera.",
      src: "assets/panoramas/08_fachada_celosia.jpg",
      initialYaw: -1.55,
      initialPitch: 0.03,
      hotspots: [
        { target: "entrada", label: "Entrar a Cochera y Acceso", yaw: -1.65, pitch: 0.04 },
        { target: "fachada", label: "Rodear a Fachada Sur", yaw: -0.85, pitch: -0.03 },
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
      if (statusEl) statusEl.textContent = "Arrastra 360° para mirar · Usa los botones o puntos para recorrer toda la casa";
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
      yaw += 0.0011;
    }

    const lookTarget = new THREE.Vector3(
      Math.cos(pitch) * Math.sin(yaw),
      Math.sin(pitch),
      -Math.cos(pitch) * Math.cos(yaw)
    );
    camera.lookAt(lookTarget);
    renderer.render(scene, camera);

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
