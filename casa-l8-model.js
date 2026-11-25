import * as THREE from "three";

/**
 * Modelo 3D arquitectónico paramétrico y 100% abierto (sin formato propietario)
 * Construido desde el plano arquitectónico A-1 (Arq. Salvador Emmanuel Valencia Contreras)
 * y los 5 renders de referencia — Lote 8, Manzana 147, Fracc. México, Morelia, Mich.
 *
 * Sistema de coordenadas (metros, Y arriba):
 * - X: 0..15.0 m (Oeste → Este)
 * - Z: 0..20.0 m (Norte → Sur, frente a Calle Zacamixtle)
 * - Y = 0.00 m: Piso de Sótano / Planta Baja (Recámaras + Patio Jardín)
 * - Y = 3.25 m: Piso de Primera Planta (Cochera + Cocina + Comedor + Estancia)
 * - Y = 6.50 m: Planta de Azotea (Pérgola + Cubo de Luz + Pretiles)
 */

function createGrassTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#66714c";
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 16000; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    const r = Math.random();
    ctx.fillStyle =
      r < 0.33
        ? "rgba(82, 93, 58, 0.35)"
        : r < 0.66
          ? "rgba(122, 132, 90, 0.28)"
          : "rgba(66, 74, 46, 0.32)";
    ctx.fillRect(x, y, 2 + Math.random() * 3, 2 + Math.random() * 4);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(16, 16);
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
    for (let s = 0; s < 8; s++) {
      x += (Math.random() - 0.5) * 44;
      y += 32;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function box(w, h, d, mat, x, y, z, name = "") {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  if (name) m.name = name;
  return m;
}

function createTree(scale = 1, clipPlane = null) {
  const g = new THREE.Group();
  const clip = clipPlane ? [clipPlane] : [];
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x56463a, roughness: 0.92, clippingPlanes: clip });
  const leafDark = new THREE.MeshStandardMaterial({ color: 0x3e5b34, roughness: 0.85, clippingPlanes: clip });
  const leafLight = new THREE.MeshStandardMaterial({ color: 0x5c7c45, roughness: 0.82, clippingPlanes: clip });
  const blossomMat = new THREE.MeshStandardMaterial({ color: 0xf7f5ef, roughness: 0.7, clippingPlanes: clip });

  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * scale, 0.17 * scale, 2.8 * scale, 8), trunkMat);
  trunk.position.y = 1.4 * scale;
  trunk.castShadow = true;
  g.add(trunk);

  [
    [0.42, 2.5, 0.18, 0.38, 0, -0.35],
    [-0.38, 2.35, -0.22, -0.35, 0, 0.38],
    [0.12, 2.85, -0.32, -0.42, 0, 0.1],
  ].forEach(([bx, by, bz, rx, ry, rz]) => {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(0.045 * scale, 0.08 * scale, 1.6 * scale, 6), trunkMat);
    br.position.set(bx * scale, by * scale, bz * scale);
    br.rotation.set(rx, ry, rz);
    br.castShadow = true;
    g.add(br);
  });

  [
    [0, 4.1, 0, 1.25, leafDark],
    [0.8, 3.65, 0.4, 0.98, leafLight],
    [-0.75, 3.7, -0.3, 1.02, leafDark],
    [0.32, 4.85, -0.28, 0.94, leafLight],
    [-0.4, 4.65, 0.5, 0.9, leafLight],
    [0.12, 5.45, 0.08, 0.72, leafDark],
  ].forEach(([x, y, z, r, mat]) => {
    const puff = new THREE.Mesh(new THREE.DodecahedronGeometry(r * scale, 1), mat);
    puff.position.set(x * scale, y * scale, z * scale);
    puff.scale.set(1.08, 0.84, 1.04);
    puff.castShadow = true;
    puff.receiveShadow = true;
    g.add(puff);
  });

  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    const rad = (0.65 + (i % 3) * 0.4) * scale;
    const b = new THREE.Mesh(new THREE.DodecahedronGeometry(0.12 * scale, 0), blossomMat);
    b.position.set(Math.cos(a) * rad, (3.4 + (i % 5) * 0.4) * scale, Math.sin(a) * rad);
    g.add(b);
  }
  return g;
}

function createBed(mats, x, y, z, rotY = 0) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  g.rotation.y = rotY;
  g.add(box(1.9, 0.28, 2.05, mats.darkWood, 0, 0.14, 0));
  g.add(box(1.82, 0.24, 1.98, mats.creamFabric, 0, 0.38, 0));
  g.add(box(1.86, 0.12, 1.25, mats.taupeFabric, 0, 0.48, 0.36));
  g.add(box(1.95, 1.05, 0.12, mats.beigeWood, 0, 0.54, -1.0));
  g.add(box(0.68, 0.16, 0.38, mats.whitePlaster, -0.45, 0.56, -0.72));
  g.add(box(0.68, 0.16, 0.38, mats.whitePlaster, 0.45, 0.56, -0.72));
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

  const mats = {
    whitePlaster: mat({ color: 0xf4f2ed, roughness: 0.84 }),
    warmWall: mat({ color: 0xe8e2d8, roughness: 0.86 }),
    floorTile: mat({ color: 0xd9d3c8, roughness: 0.55 }),
    slateDeck: mat({ color: 0x45494e, roughness: 0.85 }),
    concretePaver: mat({ color: 0x8e8d87, roughness: 0.88 }),
    gravel: mat({ color: 0xb9b3a7, roughness: 0.94 }),
    grass: mat({ map: createGrassTexture(), roughness: 0.95 }),
    road: mat({ color: 0xbeb9af, roughness: 0.82 }),
    woodSlat: mat({ color: 0x8f6f54, roughness: 0.72 }),
    beigeWood: mat({ color: 0xd8c3aa, roughness: 0.65 }),
    darkWood: mat({ color: 0x4b3f35, roughness: 0.75 }),
    darkIsland: mat({ color: 0x393e44, roughness: 0.7 }),
    marble: mat({ map: createMarbleTexture(), roughness: 0.35 }),
    creamFabric: mat({ color: 0xe7e0d4, roughness: 0.92 }),
    taupeFabric: mat({ color: 0x7c756b, roughness: 0.9 }),
    olivePillow: mat({ color: 0x6f7457, roughness: 0.9 }),
    darkMetal: mat({ color: 0x25282d, roughness: 0.42, metalness: 0.55 }),
    alum: mat({ color: 0xa2a8ae, roughness: 0.32, metalness: 0.65 }),
    rock: mat({ color: 0x676b6e, roughness: 0.94 }),
    lavender: mat({ color: 0x705b88, roughness: 0.9 }),
    warmLed: mat({ color: 0xfff3d6, emissive: 0xffd28a, emissiveIntensity: 2.2, roughness: 0.35 }),
    glass: new THREE.MeshPhysicalMaterial({
      color: 0xd8e8f5,
      transparent: true,
      opacity: 0.28,
      roughness: 0.08,
      metalness: 0.05,
      reflectivity: 0.9,
      side: THREE.DoubleSide,
      clippingPlanes: clip,
      clipShadows: true,
    }),
  };

  // =========================================================================
  // 1. TERRENO EN PENDIENTE Y VIALIDAD CURVA (Renders 1, 2 y 5 + Topográfico)
  // =========================================================================
  const siteGroup = new THREE.Group();
  siteGroup.name = "Terreno_y_Vialidad";

  // Lomas verdes alrededor con pendiente natural (más alto al Norte/Oeste, baja al Sur/Este)
  const terrainGeo = new THREE.PlaneGeometry(110, 110, 44, 44);
  terrainGeo.rotateX(-Math.PI / 2);
  const pos = terrainGeo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    // Zona del predio excavada plana a Y = -0.18
    if (x > -0.8 && x < 15.8 && z > -0.8 && z < 20.8) {
      pos.setY(i, -0.22);
    } else {
      // Pendiente suave: sube hacia el Oeste (-X) y Norte (-Z), baja hacia el Sur/Este (+X, +Z)
      const slope = (7.5 - x) * 0.085 + (10 - z) * 0.065;
      const hill = Math.sin(x * 0.055) * 0.65 + Math.cos(z * 0.05) * 0.55;
      const y = THREE.MathUtils.clamp(slope + hill - 0.15, -5.5, 4.8);
      pos.setY(i, y);
    }
  }
  terrainGeo.computeVertexNormals();
  const terrainMesh = new THREE.Mesh(terrainGeo, mats.grass);
  terrainMesh.position.set(7.5, 0, 10);
  terrainMesh.receiveShadow = true;
  siteGroup.add(terrainMesh);

  // Calle inclinada en L (Oeste bajando hacia Sur / Calle Zacamixtle)
  const roadWest = box(6.5, 0.18, 28, mats.road, -3.6, 1.55, 8.5, "Calle_Oeste");
  roadWest.rotation.x = 0.115; // Baja de Norte a Sur siguiendo la fachada Oeste
  siteGroup.add(roadWest);

  const roadSouth = box(36, 0.18, 7.2, mats.road, 10, -0.15, 24.0, "Calle_Zacamixtle");
  roadSouth.rotation.z = -0.055; // Pendiente suave hacia el Este
  siteGroup.add(roadSouth);

  root.add(siteGroup);

  // =========================================================================
  // 2. SÓTANO / PLANTA BAJA (Y = 0.00..3.00 m) — Recámaras + Patio Jardín
  // =========================================================================
  const sotanoGroup = new THREE.Group();
  sotanoGroup.name = "Sotano_Planta_Baja";

  // Losa de desplante general (15.0 m × 20.0 m)
  sotanoGroup.add(box(15.0, 0.24, 20.0, mats.floorTile, 7.5, -0.12, 10.0, "Losa_Sotano"));

  // Barda perimetral blanca del predio (Renders 1, 2 y 4)
  sotanoGroup.add(box(15.0, 3.05, 0.25, mats.whitePlaster, 7.5, 1.52, 0.125, "Barda_Norte"));
  sotanoGroup.add(box(0.25, 3.05, 20.0, mats.whitePlaster, 14.875, 1.52, 10.0, "Barda_Este"));
  sotanoGroup.add(box(15.0, 2.95, 0.25, mats.whitePlaster, 7.5, 1.47, 19.875, "Barda_Sur"));
  sotanoGroup.add(box(0.25, 3.25, 20.0, mats.whitePlaster, 0.125, 1.62, 10.0, "Muro_Oeste_Sotano"));

  // Muros interiores de Recámaras, Vestidor, Baños y Sala TV (Plano A-1 Sótano)
  // Ala Oeste/Sur de recámaras: X = 0.25..8.4, Z = 8.4..19.75
  // Muro divisorio Norte de Recámaras (con vanos amplios hacia el Patio Jardín)
  sotanoGroup.add(box(0.22, 3.0, 11.3, mats.warmWall, 4.4, 1.5, 14.1, "Muro_Div_Rec1_Rec2"));
  sotanoGroup.add(box(8.2, 3.0, 0.22, mats.warmWall, 4.3, 1.5, 14.2, "Muro_Pasillo_Sotano"));
  sotanoGroup.add(box(0.22, 3.0, 6.2, mats.warmWall, 8.4, 1.5, 16.6, "Muro_RecPrincipal"));

  // Cancelería negra piso-techo de Recámaras hacia el Patio Jardín (Render 4 y Fachada Este)
  const patioGlassZ = 8.45;
  const gBed1 = new THREE.Mesh(new THREE.PlaneGeometry(7.8, 2.85), mats.glass);
  gBed1.position.set(4.3, 1.45, patioGlassZ);
  sotanoGroup.add(gBed1);
  [0.4, 2.35, 4.3, 6.25, 8.2].forEach((mx) => {
    sotanoGroup.add(box(0.07, 2.9, 0.08, mats.darkMetal, mx, 1.45, patioGlassZ));
  });
  sotanoGroup.add(box(7.9, 0.08, 0.09, mats.darkMetal, 4.3, 2.92, patioGlassZ));

  // Cancelería lateral hacia el jardín (Recámara Principal, X = 8.45)
  const gBed2 = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 2.85), mats.glass);
  gBed2.rotation.y = Math.PI / 2;
  gBed2.position.set(8.45, 1.45, 11.2);
  sotanoGroup.add(gBed2);
  [8.6, 10.35, 12.1, 13.8].forEach((mz) => {
    sotanoGroup.add(box(0.08, 2.9, 0.07, mats.darkMetal, 8.45, 1.45, mz));
  });

  // Mobiliario de Recámaras (Sótano — visible a través de los ventanales como en Render 4)
  sotanoGroup.add(createBed(mats, 2.3, 0.0, 11.3, 0)); // Recámara 1
  sotanoGroup.add(createBed(mats, 6.4, 0.0, 11.3, 0)); // Recámara 2
  sotanoGroup.add(createBed(mats, 6.2, 0.0, 16.9, Math.PI / 2)); // Recámara Principal

  // Escalera interior conectando Sótano (Y = 0) ↔ Primera Planta (Y = 3.25) (Sección 01)
  const stairSteps = 16;
  for (let i = 0; i < stairSteps; i++) {
    const sy = 0.1 + i * (3.15 / stairSteps);
    const sz = 14.5 + i * 0.27;
    sotanoGroup.add(box(1.15, 0.14, 0.28, mats.beigeWood, 9.4, sy, sz));
  }

  // PATIO JARDÍN PRIVADO (Norte-Este, X = 0.4..14.6, Z = 0.4..8.2 — Render 4)
  sotanoGroup.add(box(14.3, 0.06, 7.9, mats.gravel, 7.55, 0.03, 4.3, "Grava_Patio"));

  // Terraza oscura de estar + 2 sillones + mesa baja (Render 4)
  sotanoGroup.add(box(5.2, 0.2, 3.6, mats.slateDeck, 11.8, 0.1, 2.5, "Terraza_Patio"));
  [10.7, 12.9].forEach((cx) => {
    const chair = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.42, 0.62, 14), mats.creamFabric);
    chair.position.set(cx, 0.51, 1.85);
    chair.castShadow = true;
    sotanoGroup.add(chair);
  });
  const patioTable = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.48, 0.34, 18), mats.concretePaver);
  patioTable.position.set(11.8, 0.37, 2.55);
  sotanoGroup.add(patioTable);

  // Andadores de concreto flotados (Render 4)
  [
    [11.8, 0.12, 5.1, 2.5, 0.12, 1.05],
    [10.4, 0.08, 6.6, 1.1, 0.08, 1.25],
    [11.8, 0.08, 6.6, 1.35, 0.08, 1.25],
    [13.3, 0.08, 6.6, 1.1, 0.08, 1.25],
  ].forEach(([px, py, pz, pw, ph, pd]) => {
    sotanoGroup.add(box(pw, ph, pd, mats.concretePaver, px, py, pz));
  });

  // Árboles ornamentales con flores blancas (sobresaliendo sobre la barda como en Renders 1, 2 y 4)
  const tree1 = createTree(1.25, clipPlane);
  tree1.position.set(12.2, 0.05, 5.4);
  sotanoGroup.add(tree1);

  const tree2 = createTree(1.02, clipPlane);
  tree2.position.set(13.2, 0.05, 2.6);
  sotanoGroup.add(tree2);

  // Rocas volcánicas y camas de lavanda (Render 4)
  [
    [10.2, 0.38, 4.4, 0.62],
    [13.6, 0.55, 4.0, 0.78],
    [9.4, 0.3, 6.8, 0.45],
  ].forEach(([rx, ry, rz, r]) => {
    const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 1), mats.rock);
    rock.position.set(rx, ry, rz);
    rock.scale.set(1.25, 0.78, 1.05);
    rock.castShadow = true;
    sotanoGroup.add(rock);
  });

  for (let i = 0; i < 12; i++) {
    const lav = new THREE.Mesh(new THREE.DodecahedronGeometry(0.28, 0), mats.lavender);
    lav.position.set(9.8 + (i % 6) * 0.72, 0.22, 4.6 + Math.floor(i / 6) * 1.45);
    sotanoGroup.add(lav);
  }

  // Arbotantes cálidos en muros del patio (Render 4)
  [
    [14.68, 2.15, 2.6],
    [14.68, 2.15, 6.0],
    [11.5, 2.15, 0.32],
    [7.2, 2.15, 0.32],
  ].forEach(([lx, ly, lz]) => {
    sotanoGroup.add(box(0.16, 0.16, 0.16, mats.darkMetal, lx, ly, lz));
    sotanoGroup.add(box(0.12, 0.24, 0.12, mats.warmLed, lx, ly, lz));
  });

  root.add(sotanoGroup);

  // =========================================================================
  // 3. PRIMERA PLANTA / NIVEL CALLE (Y = 3.25..6.25 m) — Cochera + Área Social
  // =========================================================================
  const primeraPlantaGroup = new THREE.Group();
  primeraPlantaGroup.name = "Primera_Planta";

  // Franja horizontal iluminada bajo el volumen superior en voladizo (Renders 1 y 2)
  primeraPlantaGroup.add(box(9.4, 0.26, 0.12, mats.warmLed, 10.1, 3.12, 19.65, "Franja_LED_Sur"));
  primeraPlantaGroup.add(box(0.12, 0.26, 9.2, mats.warmLed, 14.68, 3.12, 14.9, "Franja_LED_Este"));

  // Losa de entrepiso Primera Planta (Cochera + Núcleo + Volumen Social en voladizo)
  primeraPlantaGroup.add(box(14.5, 0.26, 11.4, mats.floorTile, 7.5, 3.25, 14.0, "Losa_Primera_Planta"));

  // COCHERA (Oeste, X = 0.25..6.2, Z = 8.4..19.7) con Celosía vertical de madera (Render 5)
  primeraPlantaGroup.add(box(0.25, 3.25, 9.6, mats.whitePlaster, 0.125, 4.95, 14.9, "Muro_Oeste_Ciego"));
  // Marco de la abertura con celosía (Fachada Oeste, Z = 1.6..9.6)
  primeraPlantaGroup.add(box(0.26, 0.32, 8.6, mats.whitePlaster, 0.13, 6.42, 5.7));
  primeraPlantaGroup.add(box(0.26, 3.3, 0.35, mats.whitePlaster, 0.13, 4.9, 1.55));
  for (let i = 0; i < 36; i++) {
    primeraPlantaGroup.add(box(0.1, 3.05, 0.06, mats.woodSlat, 0.16, 4.78, 1.9 + i * 0.215));
  }

  // Muro divisor Cochera / Núcleo de Servicios (Studio, Baño, Alacena, Patio Servicio)
  primeraPlantaGroup.add(box(0.22, 3.0, 10.8, mats.whitePlaster, 6.2, 4.88, 14.2, "Muro_Cochera_Interior"));
  primeraPlantaGroup.add(box(3.0, 3.0, 0.22, mats.warmWall, 7.7, 4.88, 14.5));
  primeraPlantaGroup.add(box(0.22, 3.0, 5.2, mats.warmWall, 9.2, 4.88, 17.0));

  // VOLUMEN SOCIAL EN VOLADIZO: Cocina · Comedor · Estancia (X = 6.2..14.8, Z = 8.4..19.7)
  // Fachada Sur (ciega blanca flotante — Render 1 y Render 2)
  primeraPlantaGroup.add(box(9.2, 3.2, 0.26, mats.whitePlaster, 10.2, 4.95, 19.72, "Volumen_Voladizo_Sur"));
  // Muro Norte de cocina (fondo donde van los gabinetes y refrigerador — Render 3)
  primeraPlantaGroup.add(box(5.6, 3.15, 0.24, mats.whitePlaster, 9.0, 4.95, 8.45, "Muro_Cocina"));

  // Ventanal panorámico de piso a techo hacia el Este (Jardín y lomas — Render 1 y Render 3)
  const gLivingEast = new THREE.Mesh(new THREE.PlaneGeometry(10.8, 3.0), mats.glass);
  gLivingEast.rotation.y = Math.PI / 2;
  gLivingEast.position.set(14.72, 4.88, 14.0);
  primeraPlantaGroup.add(gLivingEast);
  [8.7, 11.4, 14.1, 16.8, 19.5].forEach((mz) => {
    primeraPlantaGroup.add(box(0.08, 3.05, 0.07, mats.alum, 14.72, 4.88, mz));
  });
  primeraPlantaGroup.add(box(0.08, 0.06, 10.8, mats.alum, 14.72, 4.05, 14.0));

  // Ventanal panorámico Norte (hacia el patio arbolado)
  const gLivingNorth = new THREE.Mesh(new THREE.PlaneGeometry(2.9, 3.0), mats.glass);
  gLivingNorth.position.set(13.25, 4.88, 8.45);
  primeraPlantaGroup.add(gLivingNorth);
  primeraPlantaGroup.add(box(0.07, 3.05, 0.08, mats.alum, 11.85, 4.88, 8.45));
  primeraPlantaGroup.add(box(0.07, 3.05, 0.08, mats.alum, 13.25, 4.88, 8.45));

  // MOBILIARIO INTERIOR DE PRIMERA PLANTA (Fiel a Render 3: Sala, Comedor y Cocina)
  const y1 = 3.38;
  // Cocina: gabinetes beige superiores, backsplash de mármol con LED cálido, refrigerador
  primeraPlantaGroup.add(box(3.8, 1.15, 0.45, mats.beigeWood, 10.4, y1 + 2.2, 8.85, "Gabinetes_Cocina"));
  primeraPlantaGroup.add(box(3.8, 0.82, 0.06, mats.marble, 10.4, y1 + 1.25, 8.64, "Backsplash_Marmol"));
  primeraPlantaGroup.add(box(3.6, 0.05, 0.06, mats.warmLed, 10.4, y1 + 1.62, 8.75, "LED_Cocina"));
  primeraPlantaGroup.add(box(3.8, 0.9, 0.65, mats.darkIsland, 10.4, y1 + 0.45, 8.95));
  primeraPlantaGroup.add(box(0.92, 2.08, 0.72, mats.alum, 8.0, y1 + 1.04, 8.98, "Refrigerador"));

  // Isla oscura con cubierta de mármol
  primeraPlantaGroup.add(box(3.4, 0.92, 1.05, mats.darkIsland, 10.4, y1 + 0.46, 10.95, "Isla_Cocina"));
  primeraPlantaGroup.add(box(3.52, 0.07, 1.15, mats.marble, 10.4, y1 + 0.95, 10.95));

  // Sala: sofá en L color crema, cojines olivo/taupe, mesa de centro negra
  primeraPlantaGroup.add(box(3.15, 0.46, 1.0, mats.creamFabric, 10.6, y1 + 0.23, 13.6, "Sofa_Principal"));
  primeraPlantaGroup.add(box(3.15, 0.52, 0.22, mats.creamFabric, 10.6, y1 + 0.66, 13.2));
  primeraPlantaGroup.add(box(1.05, 0.46, 2.15, mats.creamFabric, 9.55, y1 + 0.23, 14.55));
  [9.8, 11.2].forEach((px) => {
    const p = box(0.42, 0.36, 0.16, mats.olivePillow, px, y1 + 0.6, 13.42);
    p.rotation.z = px < 10.5 ? 0.12 : -0.1;
    primeraPlantaGroup.add(p);
  });
  const coffee = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.46, 0.05, 20), mats.darkMetal);
  coffee.position.set(11.1, y1 + 0.36, 14.95);
  primeraPlantaGroup.add(coffee);

  // Comedor junto al ventanal panorámico (mesa de madera + 6 sillas crema)
  primeraPlantaGroup.add(box(1.15, 0.06, 2.35, mats.woodSlat, 13.35, y1 + 0.74, 14.8, "Comedor"));
  [13.9, 14.8, 15.7].forEach((cz) => {
    [-0.72, 0.72].forEach((dx) => {
      primeraPlantaGroup.add(box(0.44, 0.48, 0.44, mats.creamFabric, 13.35 + dx, y1 + 0.25, cz));
    });
  });

  root.add(primeraPlantaGroup);

  // =========================================================================
  // 4. PLANTA DE AZOTEA (Y = 6.45..6.85 m) — Losa, Pretiles y Pérgola Cochera
  // =========================================================================
  const azoteaGroup = new THREE.Group();
  azoteaGroup.name = "Planta_de_Azotea";

  // Losa de azotea sobre el volumen habitable
  azoteaGroup.add(box(9.2, 0.24, 11.55, mats.whitePlaster, 10.25, 6.52, 14.1, "Losa_Azotea"));
  // Pretiles perimetrales
  azoteaGroup.add(box(9.2, 0.35, 0.22, mats.whitePlaster, 10.25, 6.78, 19.76));
  azoteaGroup.add(box(9.2, 0.35, 0.22, mats.whitePlaster, 10.25, 6.78, 8.44));
  azoteaGroup.add(box(0.22, 0.35, 11.55, mats.whitePlaster, 14.74, 6.78, 14.1));
  azoteaGroup.add(box(0.22, 0.35, 11.55, mats.whitePlaster, 5.76, 6.78, 14.1));

  // Pérgola de vigas de madera sobre la Cochera (Planta de Azotea A-1)
  for (let i = 0; i < 14; i++) {
    azoteaGroup.add(box(5.7, 0.14, 0.1, mats.woodSlat, 3.05, 6.48, 2.2 + i * 0.52));
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
