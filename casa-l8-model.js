import * as THREE from "three";

/**
 * Modelo 3D arquitectónico paramétrico y 100% abierto (sin formato propietario)
 * Fidelidad visual calibrada a la Lámina A-1 (Arq. Salvador Emmanuel Valencia Contreras)
 * y a los 5 renders fotorealistas — Lote 8, Manzana 147, Fracc. México, Morelia, Mich.
 */

// ---------------------------------------------------------------------------
// Texturas procedurales PBR (estuco, pasto fino, grava vial, mármol, follaje)
// ---------------------------------------------------------------------------
function createStuccoTexture() {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#f2f0eb";
  ctx.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 9000; i++) {
    const v = 232 + Math.floor(Math.random() * 20);
    ctx.fillStyle = `rgba(${v},${v - 2},${v - 5},0.35)`;
    ctx.fillRect(Math.random() * 256, Math.random() * 256, 2, 2);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createGrassTexture() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#626a48";
  ctx.fillRect(0, 0, 512, 512);

  // Subtle sunlit meadow patches
  for (let i = 0; i < 40; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const r = 30 + Math.random() * 70;
    const g = ctx.createRadialGradient(x, y, 2, x, y, r);
    g.addColorStop(0, i % 2 === 0 ? "rgba(112, 118, 76, 0.22)" : "rgba(68, 76, 48, 0.24)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }

  // Fine grass blades
  for (let i = 0; i < 26000; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const pick = Math.random();
    ctx.fillStyle =
      pick < 0.35
        ? "rgba(74, 82, 52, 0.45)"
        : pick < 0.7
          ? "rgba(128, 134, 92, 0.35)"
          : "rgba(56, 63, 40, 0.4)";
    ctx.fillRect(x, y, 1.4, 3 + Math.random() * 3.5);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(22, 22);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createRoadGravelTexture() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#b7b1a6";
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 32000; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const v = 145 + Math.floor(Math.random() * 68);
    ctx.fillStyle = `rgba(${v},${v - 4},${v - 10},0.48)`;
    ctx.fillRect(x, y, 1.8, 1.8);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(16, 4);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createMarbleTexture() {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#f5f3ef";
  ctx.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 16; i++) {
    ctx.strokeStyle = i % 3 === 0 ? "rgba(130, 124, 116, 0.38)" : "rgba(165, 158, 148, 0.25)";
    ctx.lineWidth = i % 3 === 0 ? 1.8 : 1.0;
    ctx.beginPath();
    let x = Math.random() * 256;
    let y = 0;
    ctx.moveTo(x, y);
    for (let s = 0; s < 10; s++) {
      x += (Math.random() - 0.5) * 38;
      y += 28;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createLeafSprigTexture(withBlossoms = true) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, 256, 256);

  // Fine twig lines
  ctx.strokeStyle = "#4d3e32";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(128, 240);
  ctx.quadraticCurveTo(124, 140, 128, 26);
  ctx.moveTo(126, 175);
  ctx.lineTo(54, 108);
  ctx.moveTo(128, 155);
  ctx.lineTo(204, 96);
  ctx.moveTo(128, 105);
  ctx.lineTo(74, 48);
  ctx.moveTo(128, 95);
  ctx.lineTo(186, 46);
  ctx.stroke();

  // Individual pointed leaves for realistic lacy tree silhouette & dappled shadows
  const leafPalette = ["#3f5a2e", "#4e6d37", "#5e7e42", "#354c27", "#6f8d4e"];
  for (let i = 0; i < 68; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = 16 + Math.random() * 94;
    const lx = 128 + Math.cos(angle) * dist * 0.92;
    const ly = 122 + Math.sin(angle) * dist * 0.96;
    const rot = Math.atan2(ly - 150, lx - 128) + (Math.random() - 0.5) * 1.1;
    const len = 14 + Math.random() * 14;
    const wid = 5 + Math.random() * 5;

    ctx.save();
    ctx.translate(lx, ly);
    ctx.rotate(rot);
    ctx.fillStyle = leafPalette[i % leafPalette.length];
    ctx.beginPath();
    ctx.ellipse(0, 0, len, wid, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // Delicate white courtyard blossoms (Render 4)
  if (withBlossoms) {
    for (let i = 0; i < 16; i++) {
      const a = Math.random() * Math.PI * 2;
      const d = 20 + Math.random() * 82;
      const bx = 128 + Math.cos(a) * d;
      const by = 116 + Math.sin(a) * d;
      ctx.fillStyle = "rgba(252, 250, 246, 0.92)";
      ctx.beginPath();
      ctx.arc(bx, by, 4 + Math.random() * 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// ---------------------------------------------------------------------------
// Helpers geométricos
// ---------------------------------------------------------------------------
function box(w, h, d, mat, x, y, z, name = "") {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  if (name) m.name = name;
  return m;
}

function createNaturalBoulder(radius, mat, sx = 1.2, sy = 0.72, sz = 1.0) {
  const geo = new THREE.IcosahedronGeometry(radius, 2);
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const vx = p.getX(i);
    const vy = p.getY(i);
    const vz = p.getZ(i);
    const n =
      1 +
      0.16 * Math.sin(vx * 4.7 + vy * 3.1) +
      0.12 * Math.cos(vz * 5.2 - vx * 2.9);
    p.setXYZ(i, vx * n * sx, vy * n * sy, vz * n * sz);
  }
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function createArchitecturalTree(scale = 1, leafTex, clipPlane = null) {
  const g = new THREE.Group();
  const clip = clipPlane ? [clipPlane] : [];
  const barkMat = new THREE.MeshStandardMaterial({
    color: 0x4f4034,
    roughness: 0.94,
    clippingPlanes: clip,
  });

  // Main slender trunk + organic forked branches (Render 1 & Render 4)
  const makeBranch = (rTop, rBot, len, x, y, z, rx, ry, rz) => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop * scale, rBot * scale, len * scale, 7), barkMat);
    m.position.set(x * scale, y * scale, z * scale);
    m.rotation.set(rx, ry, rz);
    m.castShadow = true;
    m.receiveShadow = true;
    g.add(m);
  };

  makeBranch(0.085, 0.145, 2.5, 0, 1.25, 0, 0.04, 0, -0.05);
  makeBranch(0.055, 0.085, 2.2, 0.35, 3.1, 0.15, 0.15, 0.2, -0.32);
  makeBranch(0.05, 0.08, 2.1, -0.4, 3.0, -0.18, -0.18, -0.1, 0.36);
  makeBranch(0.045, 0.07, 2.4, 0.05, 3.4, -0.25, -0.24, 0.1, 0.06);
  makeBranch(0.032, 0.055, 1.6, 0.92, 4.35, 0.42, 0.28, 0.3, -0.52);
  makeBranch(0.03, 0.05, 1.6, -0.95, 4.2, -0.32, -0.25, -0.2, 0.55);
  makeBranch(0.028, 0.045, 1.8, 0.15, 4.85, -0.38, -0.18, 0.0, -0.12);

  // Instanced alpha-cutout leaf cards for lacy organic foliage & real dappled shadows
  const cardGeo = new THREE.PlaneGeometry(1.55 * scale, 1.55 * scale);
  const leafMat = new THREE.MeshStandardMaterial({
    map: leafTex,
    alphaTest: 0.35,
    side: THREE.DoubleSide,
    roughness: 0.82,
    metalness: 0.0,
    clippingPlanes: clip,
    clipShadows: true,
  });

  const count = 92;
  const inst = new THREE.InstancedMesh(cardGeo, leafMat, count);
  inst.castShadow = true;
  inst.receiveShadow = true;

  const dummy = new THREE.Object3D();
  // Seeded pseudo-random so tree shape is deterministic and balanced
  let seed = Math.round(scale * 1000) + 17;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let i = 0; i < count; i++) {
    const layer = rand();
    const y = (2.7 + layer * 3.85) * scale;
    // Wider in middle canopy, tapering softly at top like Render 1
    const maxR = (1.95 - Math.abs(layer - 0.45) * 1.55) * scale;
    const rad = Math.sqrt(rand()) * Math.max(0.45, maxR);
    const theta = rand() * Math.PI * 2;

    dummy.position.set(Math.cos(theta) * rad, y, Math.sin(theta) * rad);
    dummy.rotation.set(
      (rand() - 0.5) * 1.4,
      rand() * Math.PI * 2,
      (rand() - 0.5) * 1.4
    );
    const s = 0.72 + rand() * 0.62;
    dummy.scale.set(s, s, s);
    dummy.updateMatrix();
    inst.setMatrixAt(i, dummy.matrix);
  }
  inst.instanceMatrix.needsUpdate = true;
  g.add(inst);

  return g;
}

function createCurvedRoad(roadMat, grassMat, clipPlane) {
  const g = new THREE.Group();
  const clip = clipPlane ? [clipPlane] : [];

  // Smooth curved street sweeping from West slope around SW corner to South/East (Renders 1, 2 & 5)
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-4.2, 2.35, -16.0),
    new THREE.Vector3(-4.0, 1.35, 2.0),
    new THREE.Vector3(-3.9, 0.35, 14.5),
    new THREE.Vector3(-3.0, -0.05, 21.8),
    new THREE.Vector3(2.8, -0.18, 24.4),
    new THREE.Vector3(14.5, -0.45, 24.8),
    new THREE.Vector3(34.0, -1.25, 26.5),
  ]);

  const segs = 72;
  const halfW = 3.25;
  const positions = [];
  const uvs = [];
  const indices = [];

  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const pt = curve.getPoint(t);
    const tan = curve.getTangent(t);
    // Horizontal right normal
    const right = new THREE.Vector3(-tan.z, 0, tan.x).normalize();

    const pL = pt.clone().addScaledVector(right, -halfW);
    const pR = pt.clone().addScaledVector(right, halfW);

    positions.push(pL.x, pL.y, pL.z, pR.x, pR.y, pR.z);
    uvs.push(t * 14, 0, t * 14, 1);

    if (i < segs) {
      const a = i * 2;
      const b = a + 1;
      const c = a + 2;
      const d = a + 3;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();

  const roadMesh = new THREE.Mesh(geo, roadMat);
  roadMesh.receiveShadow = true;
  roadMesh.name = "Vialidad_Curva";
  g.add(roadMesh);

  // Subtle green grass curb berm hugging the inner edge of the road near the house (Render 1 & 2)
  const bermMat = new THREE.MeshStandardMaterial({
    color: 0x4b5536,
    roughness: 0.96,
    clippingPlanes: clip,
  });
  const bermPts = [
    new THREE.Vector3(-0.65, 0.32, 14.5),
    new THREE.Vector3(-0.55, 0.08, 19.6),
    new THREE.Vector3(0.4, 0.04, 20.55),
    new THREE.Vector3(14.8, -0.1, 20.55),
  ];
  const bermCurve = new THREE.CatmullRomCurve3(bermPts);
  const bermGeo = new THREE.TubeGeometry(bermCurve, 32, 0.24, 6, false);
  const bermMesh = new THREE.Mesh(bermGeo, bermMat);
  bermMesh.scale.y = 0.65;
  bermMesh.receiveShadow = true;
  g.add(bermMesh);

  return g;
}

function createDistantHills() {
  const g = new THREE.Group();
  g.name = "Lomas_Horizonte";
  const ringMat = new THREE.MeshStandardMaterial({
    color: 0x4a573f,
    roughness: 1.0,
    metalness: 0.0,
    fog: true,
  });
  const hillConfigs = [
    [68, -6, -55, 42, 16, 26],
    [82, -5, 10, 36, 14, 46],
    [62, -7, 68, 48, 13, 28],
    [-68, -4, -48, 44, 15, 34],
    [-75, -5, 22, 36, 12, 42],
    [5, -6, -78, 60, 17, 26],
  ];
  hillConfigs.forEach(([x, y, z, rx, ry, rz]) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 14), ringMat);
    m.position.set(x, y, z);
    m.scale.set(rx, ry, rz);
    g.add(m);
  });
  return g;
}

function createBed(mats, x, y, z, rotY = 0) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  g.rotation.y = rotY;
  g.add(box(1.9, 0.26, 2.05, mats.darkWood, 0, 0.13, 0));
  g.add(box(1.82, 0.24, 1.98, mats.creamFabric, 0, 0.37, 0));
  g.add(box(1.86, 0.12, 1.25, mats.darkBlanket, 0, 0.47, 0.36));
  g.add(box(1.95, 1.08, 0.12, mats.beigeWood, 0, 0.54, -1.0));
  g.add(box(0.68, 0.16, 0.38, mats.whitePlaster, -0.45, 0.55, -0.72));
  g.add(box(0.68, 0.16, 0.38, mats.whitePlaster, 0.45, 0.55, -0.72));
  return g;
}

export function buildCasaL8Model(clipPlane) {
  const root = new THREE.Group();
  root.name = "Casa_L8_M147_Fracc_Mexico";

  const clip = clipPlane ? [clipPlane] : [];
  const mat = (opts) =>
    new THREE.MeshStandardMaterial({
      ...opts,
      clippingPlanes: clip,
      clipShadows: true,
    });

  const stuccoTex = createStuccoTexture();
  const leafTex = createLeafSprigTexture(true);

  const mats = {
    whitePlaster: mat({ map: stuccoTex, color: 0xf6f4ef, roughness: 0.86, metalness: 0.0 }),
    warmWall: mat({ color: 0xe6dfd4, roughness: 0.85 }),
    polishedFloor: mat({ color: 0xd6cfc2, roughness: 0.24, metalness: 0.04 }),
    slateDeck: mat({ color: 0x3e4247, roughness: 0.82 }),
    concretePaver: mat({ color: 0x868580, roughness: 0.86 }),
    gravel: mat({ color: 0xb2aba0, roughness: 0.94 }),
    grass: mat({ map: createGrassTexture(), roughness: 0.96 }),
    road: mat({ map: createRoadGravelTexture(), roughness: 0.78 }),
    woodSlat: mat({ color: 0x8b6a4e, roughness: 0.72 }),
    beigeWood: mat({ color: 0xd4bea3, roughness: 0.62 }),
    darkWood: mat({ color: 0x4a3d33, roughness: 0.72 }),
    darkIsland: mat({ color: 0x34393f, roughness: 0.65 }),
    marble: mat({ map: createMarbleTexture(), roughness: 0.3 }),
    creamFabric: mat({ color: 0xe8e1d5, roughness: 0.92 }),
    darkBlanket: mat({ color: 0x363b42, roughness: 0.9 }),
    taupePillow: mat({ color: 0x767067, roughness: 0.9 }),
    olivePillow: mat({ color: 0x6c7254, roughness: 0.9 }),
    darkMetal: mat({ color: 0x1e2126, roughness: 0.36, metalness: 0.6 }),
    alum: mat({ color: 0x8e959c, roughness: 0.28, metalness: 0.7 }),
    rock: mat({ color: 0x62666a, roughness: 0.95 }),
    lavender: mat({ color: 0x6c5686, roughness: 0.92 }),
    warmLed: mat({ color: 0xfff4d8, emissive: 0xffcf82, emissiveIntensity: 2.6, roughness: 0.3 }),
    glass: new THREE.MeshPhysicalMaterial({
      color: 0xd9e8f5,
      transparent: true,
      opacity: 0.24,
      roughness: 0.06,
      metalness: 0.05,
      reflectivity: 0.95,
      side: THREE.DoubleSide,
      clippingPlanes: clip,
      clipShadows: true,
    }),
  };

  // =========================================================================
  // 1. TERRENO SUAVE, VIALIDAD CURVA Y LOMAS LEJANAS (Renders 1, 2 y 5)
  // =========================================================================
  const siteGroup = new THREE.Group();
  siteGroup.name = "Terreno_y_Vialidad";

  // Smooth rolling green hillside with gentle integration around the house footprint (no ugly cliff)
  const terrainGeo = new THREE.PlaneGeometry(130, 130, 64, 64);
  terrainGeo.rotateX(-Math.PI / 2);
  const pos = terrainGeo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i) + 7.5;
    const z = pos.getZ(i) + 10.0;

    // Distance outside the house pad [0..15, 0..20]
    const dx = Math.max(0, -x, x - 15.0);
    const dz = Math.max(0, -z, z - 20.0);
    const dist = Math.hypot(dx, dz);

    // Smooth blend from flat pad (-0.12) to natural hillside slope
    const blend = THREE.MathUtils.smoothstep(dist, 0.5, 10.0);
    const naturalSlope = (4.0 - x) * 0.068 + (10.0 - z) * 0.052;
    const rolling = Math.sin(x * 0.045) * 0.55 + Math.cos(z * 0.042) * 0.45;
    const hillY = THREE.MathUtils.clamp(naturalSlope + rolling - 0.1, -6.5, 4.4);
    const y = THREE.MathUtils.lerp(-0.14, hillY, blend);
    pos.setY(i, y);
  }
  terrainGeo.computeVertexNormals();
  const terrainMesh = new THREE.Mesh(terrainGeo, mats.grass);
  terrainMesh.position.set(7.5, 0, 10.0);
  terrainMesh.receiveShadow = true;
  siteGroup.add(terrainMesh);

  // Curved gravel/concrete road + grass curb
  siteGroup.add(createCurvedRoad(mats.road, mats.grass, clipPlane));
  // Distant misty wooded hills on the horizon
  siteGroup.add(createDistantHills());

  root.add(siteGroup);

  // =========================================================================
  // 2. SÓTANO / PLANTA BAJA (Y = 0.00..3.00 m) — Recámaras + Patio Jardín
  // =========================================================================
  const sotanoGroup = new THREE.Group();
  sotanoGroup.name = "Sotano_Planta_Baja";

  // Losa base general + faldón de cimentación (para que nunca flote sobre la pendiente)
  sotanoGroup.add(box(15.0, 0.24, 20.0, mats.polishedFloor, 7.5, -0.12, 10.0, "Losa_Sotano"));
  sotanoGroup.add(box(15.04, 1.8, 20.04, mats.whitePlaster, 7.5, -1.0, 10.0, "Cimentacion_Base"));

  // Barda perimetral blanca monolítica (Renders 1, 2 y 4)
  sotanoGroup.add(box(15.0, 3.05, 0.28, mats.whitePlaster, 7.5, 1.52, 0.14, "Barda_Norte"));
  sotanoGroup.add(box(0.28, 3.05, 20.0, mats.whitePlaster, 14.86, 1.52, 10.0, "Barda_Este"));
  sotanoGroup.add(box(15.0, 2.98, 0.28, mats.whitePlaster, 7.5, 1.49, 19.86, "Barda_Sur"));
  sotanoGroup.add(box(0.28, 3.25, 20.0, mats.whitePlaster, 0.14, 1.62, 10.0, "Muro_Oeste_Sotano"));

  // Aleta arquitectónica alta en esquina trasera Norte-Este (visible a la derecha en Render 1!)
  sotanoGroup.add(box(0.28, 6.2, 5.2, mats.whitePlaster, 14.86, 3.1, 2.6, "Aleta_Este_Patio"));
  // Aleta arquitectónica alta en esquina Oeste-Sur (visible a la izquierda en Render 1 y 2!)
  sotanoGroup.add(box(0.28, 6.4, 4.4, mats.whitePlaster, 0.14, 3.2, 17.8, "Aleta_Oeste_Fachada"));

  // Muros interiores de Recámaras, Vestidor y Sala TV
  sotanoGroup.add(box(0.22, 3.0, 11.3, mats.warmWall, 4.4, 1.5, 14.1));
  sotanoGroup.add(box(8.2, 3.0, 0.22, mats.warmWall, 4.3, 1.5, 14.2));
  sotanoGroup.add(box(0.22, 3.0, 6.2, mats.warmWall, 8.4, 1.5, 16.6));

  // Cancelería negra piso-techo de Recámaras hacia el Patio Jardín (Render 4)
  const patioGlassZ = 8.45;
  const gBed1 = new THREE.Mesh(new THREE.PlaneGeometry(7.8, 2.86), mats.glass);
  gBed1.position.set(4.3, 1.45, patioGlassZ);
  sotanoGroup.add(gBed1);
  [0.4, 2.35, 4.3, 6.25, 8.2].forEach((mx) => {
    sotanoGroup.add(box(0.08, 2.9, 0.09, mats.darkMetal, mx, 1.45, patioGlassZ));
  });
  sotanoGroup.add(box(7.9, 0.08, 0.1, mats.darkMetal, 4.3, 2.92, patioGlassZ));

  const gBed2 = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 2.86), mats.glass);
  gBed2.rotation.y = Math.PI / 2;
  gBed2.position.set(8.45, 1.45, 11.2);
  sotanoGroup.add(gBed2);
  [8.6, 10.35, 12.1, 13.8].forEach((mz) => {
    sotanoGroup.add(box(0.09, 2.9, 0.08, mats.darkMetal, 8.45, 1.45, mz));
  });

  // Recámaras amuebladas (visibles desde el patio como en Render 4)
  sotanoGroup.add(createBed(mats, 2.3, 0.0, 11.3, 0));
  sotanoGroup.add(createBed(mats, 6.4, 0.0, 11.3, 0));
  sotanoGroup.add(createBed(mats, 6.2, 0.0, 16.9, Math.PI / 2));

  // Escalera interior Sótano ↔ 1ª Planta
  for (let i = 0; i < 16; i++) {
    sotanoGroup.add(box(1.15, 0.13, 0.28, mats.beigeWood, 9.4, 0.1 + i * (3.15 / 16), 14.5 + i * 0.27));
  }

  // PATIO JARDÍN PRIVADO (Render 4)
  sotanoGroup.add(box(14.3, 0.06, 7.9, mats.gravel, 7.55, 0.03, 4.3, "Grava_Patio"));

  // Terraza oscura con luz LED indirecta inferior + 2 sillones rattan + mesa baja
  sotanoGroup.add(box(5.3, 0.22, 3.7, mats.slateDeck, 11.75, 0.14, 2.5, "Terraza_Patio"));
  sotanoGroup.add(box(4.9, 0.04, 0.06, mats.warmLed, 11.75, 0.04, 4.36)); // Luz LED bajo escalón!
  [10.65, 12.85].forEach((cx) => {
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.4, 0.42, 16), mats.creamFabric);
    base.position.set(cx, 0.46, 1.85);
    base.castShadow = true;
    sotanoGroup.add(base);
    const back = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.48, 0.38, 16, 1, true, Math.PI * 0.75, Math.PI * 1.5), mats.woodSlat);
    back.position.set(cx, 0.72, 1.85);
    sotanoGroup.add(back);
  });
  const patioTable = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.46, 0.34, 20), mats.concretePaver);
  patioTable.position.set(11.75, 0.42, 2.58);
  patioTable.castShadow = true;
  sotanoGroup.add(patioTable);

  // Andadores de concreto flotados (Render 4)
  [
    [11.75, 0.12, 5.1, 2.6, 0.12, 1.05],
    [10.25, 0.08, 6.65, 1.12, 0.08, 1.3],
    [11.75, 0.08, 6.65, 1.42, 0.08, 1.3],
    [13.3, 0.08, 6.65, 1.12, 0.08, 1.3],
  ].forEach(([px, py, pz, pw, ph, pd]) => {
    sotanoGroup.add(box(pw, ph, pd, mats.concretePaver, px, py, pz));
  });

  // Árboles arquitectónicos realistas con follaje calado y flores blancas (Renders 1, 2 y 4)
  const tree1 = createArchitecturalTree(1.22, leafTex, clipPlane);
  tree1.position.set(12.2, 0.04, 5.6);
  sotanoGroup.add(tree1);

  const tree2 = createArchitecturalTree(0.96, leafTex, clipPlane);
  tree2.position.set(13.3, 0.04, 2.9);
  sotanoGroup.add(tree2);

  // Rocas volcánicas esculpidas y lavanda (Render 4)
  [
    [10.1, 0.35, 4.4, 0.62, 1.3, 0.68, 1.0],
    [13.65, 0.58, 4.1, 0.76, 1.1, 0.92, 0.95],
    [9.4, 0.28, 6.9, 0.45, 1.25, 0.65, 1.0],
  ].forEach(([rx, ry, rz, r, sx, sy, sz]) => {
    const rock = createNaturalBoulder(r, mats.rock, sx, sy, sz);
    rock.position.set(rx, ry, rz);
    sotanoGroup.add(rock);
  });

  for (let i = 0; i < 16; i++) {
    const lav = createNaturalBoulder(0.24, mats.lavender, 1.2, 0.85, 1.1);
    lav.position.set(9.6 + (i % 8) * 0.55, 0.18, 4.55 + Math.floor(i / 8) * 1.45);
    sotanoGroup.add(lav);
  }

  // Arbotantes negros con luz cálida arriba/abajo en bardas del patio (Render 4)
  [
    [14.66, 2.2, 2.6],
    [14.66, 2.2, 6.0],
    [11.5, 2.2, 0.34],
    [7.2, 2.2, 0.34],
  ].forEach(([lx, ly, lz]) => {
    sotanoGroup.add(box(0.16, 0.15, 0.16, mats.darkMetal, lx, ly, lz));
    sotanoGroup.add(box(0.12, 0.24, 0.12, mats.warmLed, lx, ly, lz));
  });

  root.add(sotanoGroup);

  // =========================================================================
  // 3. PRIMERA PLANTA / NIVEL CALLE (Y = 3.25..6.45 m) — Voladizo + Cochera
  // =========================================================================
  const primeraPlantaGroup = new THREE.Group();
  primeraPlantaGroup.name = "Primera_Planta";

  // Franja horizontal rehundida con cristal oscuro y brillo cálido interior (Renders 1 y 2)
  primeraPlantaGroup.add(box(9.1, 0.3, 0.1, mats.warmLed, 10.05, 3.13, 19.35, "Franja_LED_Sur"));
  primeraPlantaGroup.add(box(0.1, 0.3, 9.6, mats.warmLed, 14.35, 3.13, 14.4, "Franja_LED_Este"));
  // Vidrio de la franja horizontal
  const slitGlassS = new THREE.Mesh(new THREE.PlaneGeometry(9.3, 0.34), mats.glass);
  slitGlassS.position.set(10.05, 3.14, 19.62);
  primeraPlantaGroup.add(slitGlassS);

  // Losa de entrepiso Primera Planta (piso pulido reflejante como en Render 3)
  primeraPlantaGroup.add(box(14.5, 0.26, 11.5, mats.polishedFloor, 7.5, 3.32, 14.0, "Losa_Primera_Planta"));

  // COCHERA Y FACHADA OESTE CON CELOSÍA VERTICAL DE MADERA (Render 5)
  primeraPlantaGroup.add(box(0.28, 3.35, 10.2, mats.whitePlaster, 0.14, 4.95, 14.7, "Muro_Oeste_Ciego"));
  primeraPlantaGroup.add(box(0.28, 0.36, 8.6, mats.whitePlaster, 0.14, 6.45, 5.65));
  primeraPlantaGroup.add(box(0.28, 3.35, 0.38, mats.whitePlaster, 0.14, 4.95, 1.52));
  for (let i = 0; i < 38; i++) {
    primeraPlantaGroup.add(box(0.11, 3.08, 0.055, mats.woodSlat, 0.18, 4.78, 1.85 + i * 0.205));
  }

  // Muros interiores de Cochera y Núcleo de Servicios
  primeraPlantaGroup.add(box(0.24, 3.05, 10.9, mats.whitePlaster, 6.2, 4.95, 14.2));
  primeraPlantaGroup.add(box(3.0, 3.05, 0.22, mats.warmWall, 7.7, 4.95, 14.5));
  primeraPlantaGroup.add(box(0.22, 3.05, 5.2, mats.warmWall, 9.2, 4.95, 17.0));

  // VOLUMEN SOCIAL EN VOLADIZO CON MARCO ARQUITECTÓNICO PROFUNDO (Renders 1, 2 y 3)
  // Cara Sur ciega flotante (sobresaliendo ligeramente hacia el Sur para arrojar sombra diagonal!)
  primeraPlantaGroup.add(box(9.45, 3.22, 0.34, mats.whitePlaster, 10.12, 5.02, 19.86, "Volumen_Voladizo_Sur"));
  // Faldón inferior del marco en esquina Este
  primeraPlantaGroup.add(box(0.55, 0.28, 11.6, mats.whitePlaster, 14.62, 3.44, 14.15));
  // Faldón superior del marco en esquina Este
  primeraPlantaGroup.add(box(0.55, 0.32, 11.6, mats.whitePlaster, 14.62, 6.48, 14.15));
  // Muro de fondo de cocina (Norte)
  primeraPlantaGroup.add(box(5.8, 3.18, 0.26, mats.whitePlaster, 9.0, 5.0, 8.42, "Muro_Cocina"));

  // Ventanal panorámico REHUNDIDO 25 cm dentro del marco blanco (como en Render 1 y Render 3!)
  const winX = 14.48;
  const gLivingEast = new THREE.Mesh(new THREE.PlaneGeometry(10.8, 2.95), mats.glass);
  gLivingEast.rotation.y = Math.PI / 2;
  gLivingEast.position.set(winX, 4.96, 14.0);
  primeraPlantaGroup.add(gLivingEast);
  [8.75, 11.4, 14.05, 16.7, 19.35].forEach((mz) => {
    primeraPlantaGroup.add(box(0.08, 2.96, 0.06, mats.alum, winX, 4.96, mz));
  });
  primeraPlantaGroup.add(box(0.08, 0.055, 10.7, mats.alum, winX, 4.18, 14.0));

  const gLivingNorth = new THREE.Mesh(new THREE.PlaneGeometry(2.7, 2.95), mats.glass);
  gLivingNorth.position.set(13.15, 4.96, 8.56);
  primeraPlantaGroup.add(gLivingNorth);
  primeraPlantaGroup.add(box(0.06, 2.96, 0.08, mats.alum, 11.88, 4.96, 8.56));
  primeraPlantaGroup.add(box(0.06, 2.96, 0.08, mats.alum, 13.15, 4.96, 8.56));

  // MOBILIARIO INTERIOR DE PRIMERA PLANTA (Fiel a Render 3: Cocina, Sala y Comedor)
  const y1 = 3.45;
  // Cocina: gabinetes altos beige mate, backsplash Calacatta + tira LED cálida + refrigerador gris
  primeraPlantaGroup.add(box(3.85, 1.18, 0.44, mats.beigeWood, 10.45, y1 + 2.22, 8.84, "Gabinetes_Cocina"));
  primeraPlantaGroup.add(box(3.85, 0.84, 0.06, mats.marble, 10.45, y1 + 1.26, 8.64, "Backsplash_Marmol"));
  primeraPlantaGroup.add(box(3.65, 0.05, 0.06, mats.warmLed, 10.45, y1 + 1.62, 8.76, "LED_Cocina"));
  primeraPlantaGroup.add(box(3.85, 0.88, 0.64, mats.darkIsland, 10.45, y1 + 0.44, 8.95));
  primeraPlantaGroup.add(box(0.92, 2.1, 0.72, mats.alum, 8.0, y1 + 1.05, 8.98, "Refrigerador"));

  // Isla oscura con cubierta de mármol y mezcladora
  primeraPlantaGroup.add(box(3.45, 0.9, 1.04, mats.darkIsland, 10.45, y1 + 0.45, 10.95, "Isla_Cocina"));
  primeraPlantaGroup.add(box(3.56, 0.07, 1.14, mats.marble, 10.45, y1 + 0.93, 10.95));

  // Sofá en L crema con cojines olivo y taupe + lámpara negra + mesa redonda negra (Render 3)
  primeraPlantaGroup.add(box(3.2, 0.46, 1.02, mats.creamFabric, 10.55, y1 + 0.23, 13.55, "Sofa_Principal"));
  primeraPlantaGroup.add(box(3.2, 0.54, 0.24, mats.creamFabric, 10.55, y1 + 0.67, 13.15));
  primeraPlantaGroup.add(box(1.06, 0.46, 2.2, mats.creamFabric, 9.48, y1 + 0.23, 14.55));
  [9.8, 10.6, 11.4].forEach((px, idx) => {
    const p = box(0.42, 0.36, 0.16, idx === 1 ? mats.taupePillow : mats.olivePillow, px, y1 + 0.6, 13.38);
    p.rotation.z = idx % 2 === 0 ? 0.12 : -0.1;
    primeraPlantaGroup.add(p);
  });
  const coffeeTop = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.46, 0.05, 22), mats.darkMetal);
  coffeeTop.position.set(11.1, y1 + 0.36, 14.95);
  primeraPlantaGroup.add(coffeeTop);
  const lampShade = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.55), mats.darkMetal);
  lampShade.position.set(8.85, y1 + 0.85, 13.3);
  primeraPlantaGroup.add(lampShade);

  // Comedor junto al ventanal panorámico (Render 3)
  primeraPlantaGroup.add(box(1.12, 0.06, 2.4, mats.darkWood, 13.25, y1 + 0.75, 14.8, "Comedor"));
  [13.9, 14.8, 15.7].forEach((cz) => {
    [-0.7, 0.7].forEach((dx) => {
      primeraPlantaGroup.add(box(0.44, 0.48, 0.44, mats.creamFabric, 13.25 + dx, y1 + 0.25, cz));
    });
  });

  root.add(primeraPlantaGroup);

  // =========================================================================
  // 4. PLANTA DE AZOTEA (Y = 6.55..6.95 m) — Losa, Pretiles y Pérgola Cochera
  // =========================================================================
  const azoteaGroup = new THREE.Group();
  azoteaGroup.name = "Planta_de_Azotea";

  azoteaGroup.add(box(9.45, 0.24, 11.65, mats.whitePlaster, 10.12, 6.62, 14.15, "Losa_Azotea"));
  azoteaGroup.add(box(9.45, 0.34, 0.22, mats.whitePlaster, 10.12, 6.86, 19.86));
  azoteaGroup.add(box(9.45, 0.34, 0.22, mats.whitePlaster, 10.12, 6.86, 8.44));
  azoteaGroup.add(box(0.22, 0.34, 11.65, mats.whitePlaster, 14.74, 6.86, 14.15));
  azoteaGroup.add(box(0.22, 0.34, 11.65, mats.whitePlaster, 5.5, 6.86, 14.15));

  // Pérgola de vigas de madera sobre la Cochera (Planta de Azotea A-1)
  for (let i = 0; i < 15; i++) {
    azoteaGroup.add(box(5.6, 0.14, 0.1, mats.woodSlat, 3.0, 6.54, 2.0 + i * 0.5));
  }

  root.add(azoteaGroup);

  return {
    root,
    layers: {
      site: siteGroup,
      sotano: sotanoGroup,
      primeraPlanta: primeraPlantaGroup,
      azotea: azoteaGroup,
    },
  };
}
