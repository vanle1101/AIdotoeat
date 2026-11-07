/* AUTOProfit AI command center: procedural, selectable Three.js architecture. */
(function () {
  'use strict';

  const zoneNames = {
    command: 'AI Command Center', agents: 'AI Agents', ads: 'Ad Network',
    products: 'Web Apps', live: 'Data Hub', revenue: 'Affiliate & Revenue', global: 'Global Traffic'
  };
  const zoneOrigins = {
    command: [0, 0, -3.2], agents: [-8.2, 0, -7.4], ads: [8.2, 0, -7.4],
    products: [-9.1, 0, 6.7], live: [0, 0, 9.1], revenue: [9.1, 0, 6.7]
  };
  const zonePickAreas = [
    { zone: 'command', x: 0, z: -3.2, radius: 4.9 },
    { zone: 'agents', x: -8.2, z: -7.4, radius: 4.55 },
    { zone: 'ads', x: 8.2, z: -7.4, radius: 4.45 },
    { zone: 'products', x: -9.1, z: 6.7, radius: 4.8 },
    { zone: 'live', x: 0, z: 9.1, radius: 4.7 },
    { zone: 'revenue', x: 9.1, z: 6.7, radius: 4.65 }
  ];
  const cameraPresets = {
    panorama: { target: [0, 2.6, 0], radius: 37, phi: 1.24, theta: 0.18, zone: 'command' },
    '3d': { target: [0, 2.6, 0], radius: 37, phi: 1.24, theta: 0.18, zone: 'command' },
    command: { target: [0, 4.7, -3.2], radius: 16, phi: 1.18, theta: 0.16, zone: 'command' },
    agents: { target: [-8.2, 2.9, -7.4], radius: 12, phi: 1.34, theta: 0.06, zone: 'agents' },
    ads: { target: [8.2, 2.9, -7.4], radius: 12.2, phi: 1.33, theta: -0.07, zone: 'ads' },
    products: { target: [-9.1, 2.6, 6.7], radius: 14.5, phi: 1.34, theta: 0.08, zone: 'products' },
    live: { target: [0, 3.8, 9.1], radius: 10.4, phi: 1.28, theta: 0.05, zone: 'live' },
    revenue: { target: [9.1, 2.6, 6.7], radius: 12.2, phi: 1.34, theta: -0.08, zone: 'revenue' },
    global: { target: [0, 3.5, 9.1], radius: 8.8, phi: 1.2, theta: 0.12, zone: 'global' }
  };

  function create(options) {
    const canvas = options && options.canvas;
    const THREE = window.THREE;
    if (!canvas || !THREE || !THREE.WebGLRenderer) {
      options && options.onStatus && options.onStatus('webgl-unavailable');
      return null;
    }

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
    } catch (_) {
      options && options.onStatus && options.onStatus('webgl-unavailable');
      return null;
    }

    const host = canvas.parentElement || canvas;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080d19);
    scene.fog = new THREE.FogExp2(0x07101e, 0.00145);
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 220);
    const controlsTarget = new THREE.Vector3(0, 2.5, 0);
    const spherical = new THREE.Spherical(29, 1.18, 0.08);
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const clock = new THREE.Clock();
    const zoneGroups = new Map();
    const pickTargets = [];
    const zonePickTargets = [];
    const animated = [];
    const backdropCityObjects = [];
    const screenTextures = new Map();
    const screenAtlasColumns = 4;
    const screenAtlasRows = 6;
    const screenAtlasTileWidth = 512;
    const screenAtlasTileHeight = 288;
    let screenAtlasCanvas = null;
    let screenAtlasContext = null;
    let screenAtlasTexture = null;
    let screenAtlasMaterial = null;
    const pointers = new Map();
    const commandOrbitMeshes = [];
    const workstationCounts = new Map();
    const workstations = new Map();
    const landmarks = new Map();
    const workstationBatches = new Map();
    const serverRackBatches = new Map();
    const geometryCache = new Map();
    const standardMaterialCache = new Map();
    const basicMaterialCache = new Map();
    const pickProxyMaterial = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, transparent: true, opacity: 0, side: THREE.DoubleSide });
    const reducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    const targetPosition = new THREE.Vector3();
    const targetLookAt = new THREE.Vector3();
    let activePickMetadata = null;
    let frame = 0;
    let destroyed = false;
    let hasRenderedFrame = false;
    let renderFailed = false;
    let cameraTransition = false;
    let dragging = null;
    let pinchDistance = 0;
    let hoveredZone = null;
    let hoveredObjectId = null;
    let selectedZone = 'command';
    let selectedObjectId = 'zone:command';
    let workstationGeometry = null;
    let workstationChairGeometry = null;
    let highlightedWorkstationId = null;
    let cutawayZone = null;
    let resizeObserver = null;
    let globeGroupRef = null;
    let constructionZone = 'scene';
    let staticBatchStats = null;
    let duskSunObject = null;
    let inspectionZone = null;
    let visibleInspectionZone = undefined;
    let inspectionCutawayZone = null;

    // Render at the CSS pixel size. The stage is already large, and oversampling
    // it on integrated GPUs costs a lot of fill rate without improving the
    // dashboard-sized model after the browser scales it back down.
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1));
    renderer.info.autoReset = false;
    renderer.setClearColor(0x080d19, 1);
    if (renderer.outputColorSpace && THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;
    else if ('outputEncoding' in renderer && THREE.sRGBEncoding) renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping || THREE.NoToneMapping;
    renderer.toneMappingExposure = 0.96;
    // Keep the panorama inexpensive; static contact shadows are enabled for
    // close inspection, where they materially improve architectural depth.
    renderer.shadowMap.enabled = false;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = false;

    const skyLight = new THREE.HemisphereLight(0xc1c7d7, 0x090d16, 0.42);
    scene.add(skyLight);
    const keyLight = new THREE.DirectionalLight(0xffd4ad, 1.18);
    keyLight.position.set(-14, 28, 18);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.left = -25;
    keyLight.shadow.camera.right = 25;
    keyLight.shadow.camera.top = 25;
    keyLight.shadow.camera.bottom = -25;
    keyLight.shadow.camera.near = 1;
    keyLight.shadow.camera.far = 72;
    keyLight.shadow.bias = -0.00022;
    keyLight.shadow.normalBias = 0.018;
    keyLight.shadow.camera.updateProjectionMatrix();
    scene.add(keyLight);
    // A cool rear rim separates metal and glass from the warm dusk backdrop.
    const rimLight = new THREE.DirectionalLight(0x82dcff, 0.48);
    rimLight.position.set(18, 12, -26);
    scene.add(rimLight);
    const coreGlow = new THREE.PointLight(0x16c9f2, 1.35, 20, 2);
    coreGlow.position.set(0, 7, -3);
    scene.add(coreGlow);
    scene.environment = buildStudioEnvironment();
    buildDuskSky();

    buildStarfield();
    buildPlatform();
    buildBackdropCity();
    buildCommandCenter();
    buildAgents();
    buildAdNetwork();
    buildWebApps();
    buildDataHub();
    buildAffiliate();
    flushWorkstationBatches();
    buildEnergyRoutes();
    const holoBatchStats = batchHoloScreens();
    staticBatchStats = batchStaticMeshes();
    staticBatchStats.holoScreenBatching = holoBatchStats;
    staticBatchStats.instanceBatching = batchStaticInstances();
    setInitialCamera();
    resize();
    bindControls();
    if ('ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(host);
    } else {
      window.addEventListener('resize', resize, { passive: true });
    }
    document.addEventListener('visibilitychange', onVisibility);
    frame = requestAnimationFrame(render);

    function standard(color, emissive, emissiveIntensity, metalness, roughness, opacity) {
      const resolvedEmissive = emissive || 0x000000;
      const resolvedIntensity = emissiveIntensity == null ? 0.18 : emissiveIntensity;
      const resolvedMetalness = metalness == null ? 0.68 : metalness;
      const resolvedRoughness = roughness == null ? 0.32 : roughness;
      const key = [constructionZone, color, resolvedEmissive, resolvedIntensity, resolvedMetalness, resolvedRoughness, opacity == null ? 1 : opacity].join(':');
      if (standardMaterialCache.has(key)) return standardMaterialCache.get(key);
      const parameters = { color, emissive: resolvedEmissive, emissiveIntensity: resolvedIntensity * 0.78, metalness: resolvedMetalness, roughness: resolvedRoughness, envMapIntensity: resolvedMetalness > 0.5 ? 0.92 : 0.62 };
      if (opacity != null && opacity < 1) {
        parameters.transparent = true;
        parameters.opacity = opacity;
        parameters.depthWrite = false;
        parameters.side = THREE.DoubleSide;
      }
      const material = new THREE.MeshStandardMaterial(parameters);
      if (opacity != null && opacity < 1) {
        material.userData.baseOpacity = opacity;
        material.userData.focusOpacity = Math.min(opacity, 0.055);
      }
      standardMaterialCache.set(key, material);
      return material;
    }

    function architecturalGlass(color, accent, opacity) {
      const material = new THREE.MeshPhysicalMaterial({
        color,
        emissive: accent,
        emissiveIntensity: 0.035,
        metalness: 0.36,
        roughness: 0.2,
        clearcoat: 0.58,
        clearcoatRoughness: 0.16,
        envMapIntensity: 0.72,
        transparent: true,
        opacity,
        depthWrite: false,
        side: THREE.DoubleSide
      });
      material.userData.baseOpacity = opacity;
      material.userData.focusOpacity = Math.min(opacity, 0.045);
      return material;
    }

    function shareGeometry(geometry) {
      if (!geometry || !geometry.parameters || geometry.type === 'BufferGeometry' || geometry.type === 'TubeGeometry') return geometry;
      const parameters = geometry.parameters;
      const values = Object.keys(parameters).sort().map(name => {
        const value = parameters[name];
        return typeof value === 'number' ? Number(value.toPrecision(8)) : value;
      });
      const key = `${geometry.type}:${JSON.stringify(values)}`;
      const shared = geometryCache.get(key);
      if (shared) {
        geometry.dispose();
        return shared;
      }
      geometryCache.set(key, geometry);
      return geometry;
    }

    function addMesh(parent, geometry, material, position, zone, settings) {
      const resolvedGeometry = settings && settings.shareGeometry === false ? geometry : shareGeometry(geometry);
      const mesh = new THREE.Mesh(resolvedGeometry, material);
      if (position) mesh.position.set(position[0], position[1], position[2]);
      mesh.castShadow = !!(settings && settings.castShadow);
      mesh.receiveShadow = settings && settings.receiveShadow !== undefined ? settings.receiveShadow : true;
      if (zone) {
        mesh.userData.zone = zone;
        zonePickTargets.push(mesh);
        const interactive = activePickMetadata && activePickMetadata.zone === zone ? activePickMetadata : null;
        if (interactive) {
          Object.assign(mesh.userData, interactive);
          pickTargets.push(mesh);
        } else {
          mesh.userData.objectId = `zone:${zone}`;
          mesh.userData.objectType = 'zone';
          mesh.userData.objectName = zoneNames[zone] || zone;
        }
        const group = zoneGroups.get(zone);
        if (group && material) {
          const materials = Array.isArray(material) ? material : [material];
          materials.forEach(item => { if (item && group.materials.indexOf(item) < 0) group.materials.push(item); });
        }
      }
      parent.add(mesh);
      return mesh;
    }

    function addLandmarkTarget(parent, geometry, zone, objectId, name, localPosition, worldPosition, cameraAngle) {
      const proxy = new THREE.Mesh(shareGeometry(geometry), pickProxyMaterial);
      proxy.position.set(localPosition[0], localPosition[1], localPosition[2]);
      // Keep the color-write-disabled mesh active so Raycaster can reach the
      // landmark through its surrounding structure without drawing a marker.
      proxy.visible = false;
      const metadata = { objectId, objectType: 'landmark', zone, name, worldPosition, cameraAngle: cameraAngle || 0, assignmentStatus: 'not_applicable' };
      Object.assign(proxy.userData, metadata);
      parent.add(proxy);
      pickTargets.push(proxy);
      landmarks.set(objectId, { metadata, object: proxy });
      return proxy;
    }

    function addBox(parent, size, material, position, zone, settings) {
      return addMesh(parent, new THREE.BoxGeometry(size[0], size[1], size[2]), material, position, zone, settings);
    }

    function addInstancedBoxes(parent, boxes, material, zone) {
      if (!boxes.length) return null;
      return addInstancedPrimitives(parent, new THREE.BoxGeometry(1, 1, 1), material, boxes, zone);
    }

    function addInstancedPrimitives(parent, geometry, material, parts, zone) {
      if (!parts.length) return null;
      const instanceGeometry = shareGeometry(geometry).clone();
      if (!instanceGeometry.boundingSphere) instanceGeometry.computeBoundingSphere();
      const instanceBounds = new THREE.Sphere(new THREE.Vector3(), 0);
      let hasInstanceBounds = false;
      const mesh = new THREE.InstancedMesh(instanceGeometry, material, parts.length);
      const transform = new THREE.Object3D();
      parts.forEach((part, index) => {
        if (part.matrix) {
          mesh.setMatrixAt(index, part.matrix);
          if (part.color != null) mesh.setColorAt(index, new THREE.Color(part.color));
          const bounds = instanceGeometry.boundingSphere.clone().applyMatrix4(part.matrix);
          if (hasInstanceBounds) instanceBounds.union(bounds);
          else { instanceBounds.copy(bounds); hasInstanceBounds = true; }
          return;
        }
        transform.position.set(part.position[0], part.position[1], part.position[2]);
        if (part.rotation) transform.rotation.set(part.rotation[0], part.rotation[1], part.rotation[2]);
        else transform.rotation.set(0, part.rotationY || 0, 0);
        const scale = part.size || [1, 1, 1];
        transform.scale.set(scale[0], scale[1], scale[2]);
        transform.updateMatrix();
        mesh.setMatrixAt(index, transform.matrix);
        if (part.color != null) mesh.setColorAt(index, new THREE.Color(part.color));
        const bounds = instanceGeometry.boundingSphere.clone().applyMatrix4(transform.matrix);
        if (hasInstanceBounds) instanceBounds.union(bounds);
        else { instanceBounds.copy(bounds); hasInstanceBounds = true; }
      });
      if (hasInstanceBounds) {
        instanceBounds.radius += 0.04;
        instanceGeometry.boundingSphere = instanceBounds;
      }
      mesh.frustumCulled = true;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      if (zone) {
        mesh.userData.zone = zone;
        mesh.userData.objectId = `zone:${zone}`;
        mesh.userData.objectType = 'zone';
        mesh.userData.objectName = zoneNames[zone] || zone;
        zonePickTargets.push(mesh);
        const group = zoneGroups.get(zone);
        if (group && group.materials.indexOf(material) < 0) group.materials.push(material);
      }
      parent.add(mesh);
      return mesh;
    }

    function addRing(parent, radius, tube, y, color, opacity, zone, segments) {
      const ringOpacity = Math.max(0.1, opacity * 0.84);
      const key = ['ring', color, ringOpacity].join(':');
      let ringMat = basicMaterialCache.get(key);
      if (!ringMat) {
        ringMat = new THREE.MeshBasicMaterial({ color, transparent: ringOpacity < 1, opacity: ringOpacity, depthWrite: false });
        basicMaterialCache.set(key, ringMat);
      }
      const ring = addMesh(parent, new THREE.TorusGeometry(radius, tube, 10, segments || 96), ringMat, [0, y, 0], zone);
      ring.rotation.x = Math.PI / 2;
      return ring;
    }

    function addTube(parent, points, radius, material, zone, segments) {
      const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(point[0], point[1], point[2])));
      const tube = addMesh(parent, new THREE.TubeGeometry(curve, segments || 42, radius, 8, false), material, null, zone);
      return { curve, tube };
    }

    function addInstancedBeams(parent, segments, radius, material, zone, sides) {
      if (!segments.length) return null;
      const up = new THREE.Vector3(0, 1, 0);
      const parts = segments.map(segment => {
        const start = new THREE.Vector3(segment.start[0], segment.start[1], segment.start[2]);
        const end = new THREE.Vector3(segment.end[0], segment.end[1], segment.end[2]);
        const direction = end.clone().sub(start);
        const length = direction.length();
        const matrix = new THREE.Matrix4().compose(
          start.add(end).multiplyScalar(0.5),
          new THREE.Quaternion().setFromUnitVectors(up, direction.normalize()),
          new THREE.Vector3(1, length, 1)
        );
        return { matrix, color: segment.color };
      });
      const beamGeometry = new THREE.CylinderGeometry(radius * 0.78, radius, 1, sides || 8, 1, false);
      return addInstancedPrimitives(parent, beamGeometry, material, parts, zone);
    }

    function addGlassVault(parent, zone, width, depth, baseY, rise, accent, cutawayBelowY) {
      const lengthSegments = 10;
      const archSegments = 16;
      const positions = [];
      const uvs = [];
      const indices = [];
      for (let along = 0; along <= lengthSegments; along += 1) {
        const x = -width / 2 + (along / lengthSegments) * width;
        for (let arch = 0; arch <= archSegments; arch += 1) {
          const angle = (arch / archSegments) * Math.PI;
          positions.push(x, baseY + Math.sin(angle) * rise, Math.cos(angle) * depth / 2);
          uvs.push(along / lengthSegments, arch / archSegments);
        }
      }
      for (let along = 0; along < lengthSegments; along += 1) {
        for (let arch = 0; arch < archSegments; arch += 1) {
          const a = along * (archSegments + 1) + arch;
          const b = a + archSegments + 1;
          indices.push(a, b, a + 1, b, b + 1, a + 1);
        }
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      const vault = addMesh(parent, geometry, architecturalGlass(0x6eb8c8, accent, 0.17), null, zone);
      vault.userData.workstationCutaway = true;
      if (cutawayBelowY != null) vault.userData.workstationCutawayBelowY = cutawayBelowY;
      return vault;
    }

    function mergeBufferGeometries(geometries) {
      const positions = [];
      const normals = [];
      const uvs = [];
      const indices = [];
      let vertexOffset = 0;
      geometries.forEach(geometry => {
        const position = geometry.getAttribute('position');
        const normal = geometry.getAttribute('normal');
        const uv = geometry.getAttribute('uv');
        for (let i = 0; i < position.array.length; i += 1) positions.push(position.array[i]);
        if (normal) for (let i = 0; i < normal.array.length; i += 1) normals.push(normal.array[i]);
        if (uv) for (let i = 0; i < uv.array.length; i += 1) uvs.push(uv.array[i]);
        const sourceIndices = geometry.index;
        if (sourceIndices) {
          for (let i = 0; i < sourceIndices.count; i += 1) indices.push(sourceIndices.getX(i) + vertexOffset);
        } else {
          for (let i = 0; i < position.count; i += 1) indices.push(i + vertexOffset);
        }
        vertexOffset += position.count;
        geometry.dispose();
      });
      const merged = new THREE.BufferGeometry();
      merged.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      if (normals.length) merged.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
      if (uvs.length) merged.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      merged.setIndex(indices);
      merged.computeBoundingSphere();
      return merged;
    }

    function registerZone(key, position, parent) {
      constructionZone = key;
      const group = new THREE.Group();
      group.name = zoneNames[key] || key;
      group.userData.zone = key;
      group.userData.objectId = `zone:${key}`;
      group.userData.objectType = 'zone';
      group.userData.objectName = zoneNames[key] || key;
      group.userData.worldPosition = position.slice();
      group.materials = [];
      if (parent) parent.add(group);
      else scene.add(group);
      if (position && !parent) group.position.set(position[0], position[1], position[2]);
      zoneGroups.set(key, group);
      return group;
    }

    function colored(color) {
      const key = `${constructionZone}:${color}`;
      if (basicMaterialCache.has(key)) return basicMaterialCache.get(key);
      const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.78 });
      basicMaterialCache.set(key, material);
      return material;
    }

    function buildStudioEnvironment() {
      const art = document.createElement('canvas');
      art.width = 512;
      art.height = 256;
      const ctx = art.getContext('2d');
      const sky = ctx.createLinearGradient(0, 0, 0, art.height);
      sky.addColorStop(0, '#071127');
      sky.addColorStop(0.42, '#102534');
      sky.addColorStop(0.56, '#1c3f50');
      sky.addColorStop(0.72, '#0d1d31');
      sky.addColorStop(1, '#040b19');
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, art.width, art.height);
      // A compact procedural city reflection gives metal and glass readable
      // silhouettes without adding scene geometry or overlaying the model.
      const skylineBase = 214;
      for (let index = 0; index < 64; index += 1) {
        const x = index * 8;
        const width = 4 + ((index * 7) % 6);
        const height = 24 + ((index * 47) % 86);
        const top = skylineBase - height;
        const facade = ctx.createLinearGradient(x, top, x + width, skylineBase);
        facade.addColorStop(0, index % 4 ? 'rgba(13, 37, 58, 0.96)' : 'rgba(25, 37, 75, 0.96)');
        facade.addColorStop(1, 'rgba(4, 15, 31, 0.98)');
        ctx.fillStyle = facade;
        ctx.fillRect(x, top, width, height);
        ctx.strokeStyle = index % 3 ? 'rgba(63, 163, 197, 0.28)' : 'rgba(144, 105, 218, 0.32)';
        ctx.lineWidth = 0.7;
        ctx.strokeRect(x + 0.35, top + 0.35, width - 0.7, height - 0.7);
        ctx.fillStyle = 'rgba(91, 221, 255, 0.34)';
        for (let windowY = top + 5; windowY < skylineBase - 3; windowY += 8) {
          for (let windowX = x + 1.5; windowX < x + width - 1; windowX += 3.5) {
            const lightPattern = (index * 13 + Math.floor(windowY) * 3 + Math.floor(windowX)) % 9;
            if (lightPattern < 3) {
              ctx.globalAlpha = lightPattern === 0 ? 0.72 : 0.42;
              ctx.fillRect(windowX, windowY, 1.4, 2.4);
            }
          }
        }
        ctx.globalAlpha = 1;
        if (index % 7 === 2) {
          ctx.strokeStyle = 'rgba(108, 224, 255, 0.38)';
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(x + width / 2, top);
          ctx.lineTo(x + width / 2, Math.max(18, top - 9 - (index % 3) * 4));
          ctx.stroke();
        }
      }
      const horizon = ctx.createLinearGradient(0, skylineBase - 18, 0, skylineBase + 28);
      horizon.addColorStop(0, 'rgba(58, 202, 240, 0.2)');
      horizon.addColorStop(0.4, 'rgba(44, 129, 182, 0.12)');
      horizon.addColorStop(1, 'rgba(3, 11, 26, 0)');
      ctx.fillStyle = horizon;
      ctx.fillRect(0, skylineBase - 18, art.width, 46);
      ctx.save();
      ctx.filter = 'blur(12px)';
      [[54, 82, 0x38, '#27dfff'], [152, 114, 0x28, '#7b65ff'], [280, 73, 0x32, '#42e9d4'], [408, 102, 0x35, '#a365ff']].forEach(([x, y, width, color]) => {
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.4;
        ctx.fillRect(x, y, width, 118);
      });
      ctx.restore();
      ctx.save();
      ctx.filter = 'blur(10px)';
      ctx.globalAlpha = 0.34;
      ctx.fillStyle = '#d9f7ff';
      ctx.fillRect(32, 66, 44, 128);
      ctx.fillRect(310, 58, 38, 138);
      ctx.fillStyle = '#ffcda9';
      ctx.fillRect(208, 78, 25, 108);
      ctx.restore();
      ctx.globalAlpha = 0.28;
      ctx.fillStyle = '#78eaff';
      for (let i = 0; i < 30; i += 1) {
        const x = (i * 83) % art.width;
        const y = 102 + ((i * 47) % 82);
        ctx.fillRect(x, y, 20 + (i % 4) * 7, 1 + (i % 2));
      }
      ctx.globalAlpha = 1;
      const texture = new THREE.CanvasTexture(art);
      texture.mapping = THREE.EquirectangularReflectionMapping;
      if (texture.colorSpace !== undefined && THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
      else if (texture.encoding !== undefined && THREE.sRGBEncoding) texture.encoding = THREE.sRGBEncoding;
      texture.needsUpdate = true;
      return texture;
    }

    function buildDuskSky() {
      // A real enclosing 3D sky volume gives the campus a readable horizon
      // without placing a flat image behind or over the architecture.
      const geometry = new THREE.SphereGeometry(150, 32, 20);
      const positions = geometry.getAttribute('position');
      const colors = [];
      const stops = [
        { at: -0.08, color: new THREE.Color(0x040914) },
        { at: 0.08, color: new THREE.Color(0x091227) },
        { at: 0.18, color: new THREE.Color(0x151b32) },
        { at: 0.24, color: new THREE.Color(0x30243f) },
        { at: 0.33, color: new THREE.Color(0x11192f) },
        { at: 0.52, color: new THREE.Color(0x0d152a) },
        { at: 1, color: new THREE.Color(0x060b17) }
      ];
      const color = new THREE.Color();
      for (let index = 0; index < positions.count; index += 1) {
        const elevation = positions.getY(index) / 150;
        const amount = clamp((elevation + 0.08) / 1.08, 0, 1);
        let stopIndex = 1;
        while (stopIndex < stops.length - 1 && amount > stops[stopIndex].at) stopIndex += 1;
        const lower = stops[stopIndex - 1];
        const upper = stops[stopIndex];
        const local = clamp((amount - lower.at) / (upper.at - lower.at), 0, 1);
        color.copy(lower.color).lerp(upper.color, local);
        colors.push(color.r, color.g, color.b);
      }
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      const dome = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({
        vertexColors: true,
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        toneMapped: false
      }));
      dome.name = 'Procedural dusk sky volume';
      dome.renderOrder = -1000;
      scene.add(dome);

      const sun = new THREE.Mesh(
        new THREE.SphereGeometry(2.25, 24, 16),
        new THREE.MeshBasicMaterial({ color: 0xffa26b, toneMapped: false })
      );
      sun.name = 'Dusk sun';
      sun.position.set(-25, 11.5, -30);
      scene.add(sun);
      duskSunObject = sun;
    }

    function getScreenTexture(title, accent) {
      const key = `${title}:${accent}`;
      if (screenTextures.has(key)) return screenTextures.get(key);
      if (!screenAtlasCanvas) {
        screenAtlasCanvas = document.createElement('canvas');
        screenAtlasCanvas.width = screenAtlasColumns * screenAtlasTileWidth;
        screenAtlasCanvas.height = screenAtlasRows * screenAtlasTileHeight;
        screenAtlasContext = screenAtlasCanvas.getContext('2d');
        screenAtlasTexture = new THREE.CanvasTexture(screenAtlasCanvas);
        if (THREE.sRGBEncoding) screenAtlasTexture.encoding = THREE.sRGBEncoding;
        screenAtlasTexture.generateMipmaps = false;
        screenAtlasTexture.minFilter = THREE.LinearFilter;
        screenAtlasTexture.magFilter = THREE.LinearFilter;
        screenAtlasMaterial = new THREE.MeshBasicMaterial({ map: screenAtlasTexture, side: THREE.DoubleSide, transparent: true, toneMapped: false });
      }
      const slot = screenTextures.size;
      if (slot >= screenAtlasColumns * screenAtlasRows) return null;
      const column = slot % screenAtlasColumns;
      const row = Math.floor(slot / screenAtlasColumns);
      const art = document.createElement('canvas');
      art.width = screenAtlasTileWidth;
      art.height = screenAtlasTileHeight;
      const context = art.getContext('2d');
      context.fillStyle = '#031229';
      context.fillRect(0, 0, screenAtlasTileWidth, screenAtlasTileHeight);
      context.fillStyle = '#082847';
      context.fillRect(0, 0, screenAtlasTileWidth, 34);
      context.fillStyle = `#${accent.toString(16).padStart(6, '0')}`;
      context.font = '700 17px Segoe UI, Arial, sans-serif';
      context.fillText(title, 18, 23);
      context.strokeStyle = '#155174';
      context.lineWidth = 1;
      for (let x = 20; x < 512; x += 41) { context.beginPath(); context.moveTo(x, 48); context.lineTo(x, 270); context.stroke(); }
      for (let y = 58; y < 280; y += 34) { context.beginPath(); context.moveTo(12, y); context.lineTo(500, y); context.stroke(); }
      context.fillStyle = '#0c3554';
      context.fillRect(20, 54, 135, 72);
      context.fillRect(168, 54, 145, 72);
      context.fillRect(326, 54, 165, 72);
      context.strokeStyle = `#${accent.toString(16).padStart(6, '0')}`;
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(18, 224);
      for (let i = 0; i < 13; i += 1) context.lineTo(18 + i * 39, 188 + Math.sin(i * 1.25) * 25 + Math.cos(i * 0.52) * 14);
      context.stroke();
      context.fillStyle = `#${accent.toString(16).padStart(6, '0')}`;
      for (let i = 0; i < 8; i += 1) context.fillRect(30 + i * 57, 254 - ((i * 17) % 48), 24, 20 + ((i * 17) % 48));
      const x = column * screenAtlasTileWidth;
      const y = row * screenAtlasTileHeight;
      screenAtlasContext.clearRect(x, y, screenAtlasTileWidth, screenAtlasTileHeight);
      screenAtlasContext.drawImage(art, x + 2, y + 2, screenAtlasTileWidth - 4, screenAtlasTileHeight - 4);
      screenAtlasTexture.needsUpdate = true;
      const region = {
        material: screenAtlasMaterial,
        uv: [
          (x + 2) / screenAtlasCanvas.width,
          1 - (y + screenAtlasTileHeight - 2) / screenAtlasCanvas.height,
          (x + screenAtlasTileWidth - 2) / screenAtlasCanvas.width,
          1 - (y + 2) / screenAtlasCanvas.height
        ]
      };
      screenTextures.set(key, region);
      return region;
    }

    function applyScreenAtlasUv(geometry, region) {
      if (!region || !region.uv || !geometry) return geometry;
      const uv = geometry.getAttribute('uv');
      for (let index = 0; index < uv.count; index += 1) {
        const localU = uv.getX(index);
        const localV = uv.getY(index);
        uv.setXY(index, region.uv[0] + localU * (region.uv[2] - region.uv[0]), region.uv[1] + localV * (region.uv[3] - region.uv[1]));
      }
      uv.needsUpdate = true;
      return geometry;
    }

    function addHoloScreen(parent, width, height, position, zone, title, accent, rotationY) {
      const frameMat = standard(0x142945, 0x08769e, 0.48, 0.76, 0.22);
      const frame = addMesh(parent, new THREE.BoxGeometry(width + 0.2, height + 0.2, 0.18), frameMat, position, zone);
      frame.userData.workstationCutaway = true;
      frame.userData.hologram = true;
      frame.rotation.y = rotationY || 0;
      const screenRegion = getScreenTexture(title, accent);
      const screenGeometry = applyScreenAtlasUv(new THREE.PlaneGeometry(width, height), screenRegion);
      const screenMaterial = screenRegion ? screenRegion.material : new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(document.createElement('canvas')), side: THREE.DoubleSide, transparent: true, toneMapped: false });
      const screen = addMesh(parent, screenGeometry, screenMaterial, [position[0], position[1], position[2] + 0.101], zone, { shareGeometry: false });
      screen.userData.workstationCutaway = true;
      screen.userData.holoAtlas = !!screenRegion;
      screen.userData.hologram = true;
      screen.rotation.y = rotationY || 0;
      const underline = addMesh(parent, new THREE.BoxGeometry(width * 0.88, 0.035, 0.045), colored(accent), [position[0], position[1] - height / 2 - 0.06, position[2] + 0.12], zone);
      underline.userData.workstationCutaway = true;
      underline.userData.hologram = true;
      underline.rotation.y = rotationY || 0;
      return screen;
    }

    function addLabel(parent, text, position, color, scale, zone) {
      const labelCanvas = document.createElement('canvas');
      labelCanvas.width = 512;
      labelCanvas.height = 128;
      const ctx = labelCanvas.getContext('2d');
      ctx.clearRect(0, 0, 512, 128);
      ctx.fillStyle = 'rgba(3, 14, 31, .92)';
      ctx.strokeStyle = `#${color.toString(16).padStart(6, '0')}`;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.roundRect(8, 8, 496, 112, 18);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
      ctx.font = '700 37px Segoe UI, Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.shadowColor = `#${color.toString(16).padStart(6, '0')}`;
      ctx.shadowBlur = 12;
      ctx.fillText(text, 256, 64, 468);
      const texture = new THREE.CanvasTexture(labelCanvas);
      if (THREE.sRGBEncoding) texture.encoding = THREE.sRGBEncoding;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false, toneMapped: false }));
      sprite.position.set(position[0], position[1], position[2]);
      sprite.scale.set(scale * 3.35, scale * 0.84, 1);
      sprite.renderOrder = 4;
      if (zone) sprite.userData.zone = zone;
      parent.add(sprite);
      return sprite;
    }

    function buildPlatform() {
      const baseMat = standard(0x071326, 0x031a34, 0.35, 0.78, 0.34);
      const armorMat = standard(0x142846, 0x0a385e, 0.32, 0.72, 0.3);
      const darkMat = standard(0x040b17, 0x071a2b, 0.3, 0.88, 0.4);
      addMesh(scene, new THREE.CylinderGeometry(17.7, 19.2, 1.2, 128, 1, false), baseMat, [0, -0.52, 0], null, { castShadow: true });
      addMesh(scene, new THREE.CylinderGeometry(18.1, 18.3, 0.28, 128), armorMat, [0, 0.16, 0], null, { castShadow: true });
      addMesh(scene, new THREE.CylinderGeometry(16.6, 17.6, 0.2, 128), darkMat, [0, 0.4, 0], null);
      addMesh(scene, new THREE.CylinderGeometry(13.6, 16.7, 0.12, 128), standard(0x0b2038, 0x062944, 0.26, 0.64, 0.3), [0, 0.55, 0], null);
      [18.25, 17.25, 15.9, 13.9, 10.4].forEach((radius, index) => {
        const ring = addRing(scene, radius, index % 2 ? 0.035 : 0.075, index < 2 ? -0.04 : 0.62, index % 2 ? 0x6bb9bc : 0xb38a55, 0.4, null, 128);
        animated.push({ kind: 'ring', object: ring, speed: index % 2 ? -0.035 : 0.026 });
      });
      const inset = new THREE.GridHelper(31, 24, 0x0a5273, 0x09283e);
      inset.position.y = 0.615;
      inset.material.transparent = true;
      inset.material.opacity = 0.055;
      scene.add(inset);
      const ribMat = standard(0x193452, 0x05749b, 0.38, 0.72, 0.28);
      const ribParts = [];
      const beaconParts = [];
      for (let i = 0; i < 24; i += 1) {
        const angle = i * Math.PI / 12;
        ribParts.push({ size: [0.2, 0.24, 2.3], position: [Math.sin(angle) * 18, -0.7, Math.cos(angle) * 18], rotationY: angle });
        beaconParts.push({ position: [Math.sin(angle) * 18.5, -0.2, Math.cos(angle) * 18.5], color: i % 3 ? 0x6cc4c0 : 0xffc778 });
      }
      addInstancedBoxes(scene, ribParts, ribMat, null);
      addInstancedPrimitives(scene, new THREE.SphereGeometry(0.12, 10, 8), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), beaconParts, null);
      const spokeParts = [];
      for (let i = 0; i < 16; i += 1) {
        const angle = i * Math.PI / 8;
        spokeParts.push({ size: [0.08, 0.035, 8.3], position: [Math.sin(angle) * 11.7, 0.64, Math.cos(angle) * 11.7], rotationY: angle, color: i % 2 ? 0x157db0 : 0x3b61ab });
      }
      addInstancedBoxes(scene, spokeParts, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.84, toneMapped: false }), null);
      const supportParts = [];
      const supportRingParts = [];
      for (let i = 0; i < 12; i += 1) {
        const angle = i * Math.PI / 6;
        supportParts.push({ position: [Math.sin(angle) * 14.9, -1.16, Math.cos(angle) * 14.9], rotationY: angle });
        supportRingParts.push({ position: [Math.sin(angle) * 14.9, -1.58, Math.cos(angle) * 14.9], rotation: [Math.PI / 2, 0, 0] });
      }
      addInstancedPrimitives(scene, new THREE.CylinderGeometry(0.4, 0.72, 0.85, 8), armorMat, supportParts, null);
      addInstancedPrimitives(scene, new THREE.TorusGeometry(0.7, 0.035, 10, 32), new THREE.MeshBasicMaterial({ color: 0x00b9e8, transparent: true, opacity: 0.42, depthWrite: false }), supportRingParts, null);
      buildThrusters();
      buildLandscaping();
      buildCampusThreshold();
    }

    function buildThrusters() {
      const casing = standard(0x101e32, 0x071b30, 0.22, 0.86, 0.28);
      const collar = standard(0x1d3752, 0x073a59, 0.32, 0.78, 0.22);
      const exhaustMat = new THREE.MeshBasicMaterial({ color: 0x21cfff, transparent: true, opacity: 0.2, side: THREE.DoubleSide, depthWrite: false });
      const casingParts = [];
      const collarParts = [];
      const nozzleRingParts = [];
      const exhaustParts = [];
      const coreParts = [];
      const energyRingParts = [];
      for (let i = 0; i < 8; i += 1) {
        const angle = (i / 8) * Math.PI * 2 + Math.PI / 8;
        const radius = 11.8;
        const x = Math.sin(angle) * radius;
        const z = Math.cos(angle) * radius;
        const position = (localY) => [x, -1.18 + localY, z];
        casingParts.push({ position: position(-0.12) });
        collarParts.push({ position: position(-0.78) });
        nozzleRingParts.push({ position: position(-0.94) });
        exhaustParts.push({ position: position(-1.72), rotation: [0, 0, Math.PI] });
        coreParts.push({ position: position(-1.02), rotation: [0, 0, Math.PI] });
        energyRingParts.push({ position: position(-0.88), rotation: [Math.PI / 2, 0, 0] });
      }
      addInstancedPrimitives(scene, new THREE.CylinderGeometry(0.78, 0.54, 1.15, 10), casing, casingParts, null);
      addInstancedPrimitives(scene, new THREE.CylinderGeometry(0.58, 0.66, 0.2, 16), collar, collarParts, null);
      addInstancedPrimitives(scene, new THREE.CylinderGeometry(0.42, 0.5, 0.12, 20), colored(0x38dfff), nozzleRingParts, null);
      addInstancedPrimitives(scene, new THREE.ConeGeometry(0.38, 1.5, 12, 1, true), exhaustMat, exhaustParts, null);
      addInstancedPrimitives(scene, new THREE.CylinderGeometry(0.2, 0.09, 0.42, 12), new THREE.MeshBasicMaterial({ color: 0x82efff, toneMapped: false }), coreParts, null);
      const energyRingMaterial = new THREE.MeshBasicMaterial({ color: 0x24dfff, transparent: true, opacity: 0.76 * 0.84, depthWrite: false });
      addInstancedPrimitives(scene, new THREE.TorusGeometry(0.55, 0.035, 10, 48), energyRingMaterial, energyRingParts, null);
      addMesh(scene, new THREE.CylinderGeometry(2.1, 1.25, 1.4, 12), standard(0x112840, 0x064369, 0.34, 0.82, 0.24), [0, -1.55, 0], null, { castShadow: true });
      addMesh(scene, new THREE.ConeGeometry(0.86, 1.7, 16, 1, true), new THREE.MeshBasicMaterial({ color: 0x188fc9, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false }), [0, -3.0, 0], null);
      const coreRing = addRing(scene, 1.5, 0.055, -2.22, 0x29dfff, 0.72, null, 64);
      animated.push({ kind: 'ring', object: coreRing, speed: -0.08 });
    }

    function buildLandscaping() {
      const count = 8;
      const positions = Array.from({ length: count }, (_, index) => {
        const angle = (index / count) * Math.PI * 2 + 0.16;
        return [Math.sin(angle) * 15.6, Math.cos(angle) * 15.6, index];
      });
      const addInstances = (geometry, material, applyTransform) => {
        const mesh = new THREE.InstancedMesh(geometry, material, count);
        const transform = new THREE.Object3D();
        mesh.frustumCulled = false;
        positions.forEach(([x, z, index], instance) => {
          applyTransform(transform, x, z, index);
          transform.updateMatrix();
          mesh.setMatrixAt(instance, transform.matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
        scene.add(mesh);
        return mesh;
      };
      const lampSteel = standard(0x273746, 0x21180d, 0.08, 0.58, 0.42);
      addInstances(new THREE.CylinderGeometry(0.075, 0.12, 4.0, 8), lampSteel, (t, x, z) => t.position.set(x, 2.68, z));
      const arms = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), lampSteel, count);
      const globes = new THREE.InstancedMesh(
        new THREE.SphereGeometry(0.14, 8, 6),
        new THREE.MeshBasicMaterial({ color: 0xffd08a, toneMapped: false }),
        count
      );
      const beams = new THREE.InstancedMesh(
        new THREE.ConeGeometry(1, 1, 10, 1, true),
        new THREE.MeshBasicMaterial({ color: 0xffc778, transparent: true, opacity: 0.045, side: THREE.DoubleSide, depthWrite: false, toneMapped: false }),
        count
      );
      const transform = new THREE.Object3D();
      positions.forEach(([x, z], index) => {
        const angle = Math.atan2(x, z);
        const inwardX = -Math.sin(angle) * 0.34;
        const inwardZ = -Math.cos(angle) * 0.34;
        transform.position.set(x + inwardX * 0.5, 4.58, z + inwardZ * 0.5);
        transform.rotation.set(0, angle + Math.PI / 2, 0);
        transform.scale.set(0.62, 0.12, 0.16);
        transform.updateMatrix();
        arms.setMatrixAt(index, transform.matrix);
        transform.position.set(x + inwardX, 4.52, z + inwardZ);
        transform.rotation.set(0, 0, 0);
        transform.scale.set(1, 1, 1);
        transform.updateMatrix();
        globes.setMatrixAt(index, transform.matrix);
        transform.position.set(x + inwardX, 2.36, z + inwardZ);
        transform.rotation.set(Math.PI, 0, 0);
        transform.scale.set(1.35, 4.35, 1.35);
        transform.updateMatrix();
        beams.setMatrixAt(index, transform.matrix);
      });
      [arms, globes, beams].forEach(mesh => {
        mesh.frustumCulled = false;
        mesh.instanceMatrix.needsUpdate = true;
        scene.add(mesh);
      });
    }

    function buildCampusThreshold() {
      const radius = 16.1;
      const panelCount = 72;
      const step = Math.PI * 2 / panelCount;
      const postParts = [];
      const railParts = [];
      const infillParts = [];
      const steel = standard(0x263849, 0x0a2938, 0.1, 0.62, 0.4);
      const wire = standard(0x607b88, 0x102b34, 0.035, 0.44, 0.5);

      for (let index = 0; index < panelCount; index += 1) {
        const start = -Math.PI + index * step;
        const end = start + step;
        const middle = (start + end) / 2;
        const normalized = Math.atan2(Math.sin(middle), Math.cos(middle));
        if (Math.abs(normalized) < 0.29) continue;
        const chord = radius * 2 * Math.sin(step / 2);
        const x = Math.sin(middle) * radius;
        const z = Math.cos(middle) * radius;
        const yaw = middle;
        postParts.push({ size: [0.12, 2.42, 0.12], position: [Math.sin(start) * radius, 1.93, Math.cos(start) * radius] });
        railParts.push(
          { size: [chord + 0.04, 0.075, 0.075], position: [x, 0.84, z], rotationY: yaw },
          { size: [chord + 0.04, 0.075, 0.075], position: [x, 3.02, z], rotationY: yaw }
        );
        infillParts.push({ size: [0.035, 2.02, 0.035], position: [x, 1.93, z], rotationY: yaw });
        const diagonalLength = Math.hypot(chord, 1.88);
        const tilt = Math.atan2(1.88, chord);
        [-1, 1].forEach(direction => {
          const yawRotation = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw);
          const localTilt = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), direction * tilt);
          const matrix = new THREE.Matrix4().compose(
            new THREE.Vector3(x, 1.93, z),
            yawRotation.multiply(localTilt),
            new THREE.Vector3(diagonalLength, 0.024, 0.024)
          );
          infillParts.push({ matrix });
        });
      }
      addInstancedBoxes(scene, postParts, steel, null);
      addInstancedBoxes(scene, railParts, steel, null);
      addInstancedBoxes(scene, infillParts, wire, null);

      const road = standard(0x202933, 0x05090d, 0.025, 0.12, 0.86);
      addMesh(scene, new THREE.BoxGeometry(5.9, 0.035, 5.4), road, [0, 0.645, 15.15], null);
      const marking = new THREE.MeshBasicMaterial({ color: 0xcaa46a, transparent: true, opacity: 0.7 });
      const laneParts = [];
      for (let index = 0; index < 7; index += 1) {
        laneParts.push({ size: [0.055, 0.012, 0.32], position: [0, 0.67, 12.95 + index * 0.62] });
      }
      addInstancedBoxes(scene, laneParts, marking, null);

      const gateParts = [];
      const trimParts = [];
      const lightParts = [];
      [-1, 1].forEach(side => {
        const x = side * 4.05;
        gateParts.push(
          { size: [0.62, 3.05, 0.62], position: [x, 2.15, 15.85] },
          { size: [0.84, 0.22, 0.84], position: [x, 3.72, 15.85] },
          { size: [0.78, 0.16, 0.78], position: [x, 0.79, 15.85] }
        );
        trimParts.push({ size: [0.055, 2.3, 0.035], position: [x - side * 0.24, 2.12, 16.18] });
        lightParts.push({ size: [0.11, 0.12, 0.11], position: [x - side * 0.24, 3.42, 16.0] });
      });
      gateParts.push(
        { size: [7.85, 0.28, 0.42], position: [0, 3.95, 15.85] },
        { size: [5.8, 0.78, 0.16], position: [0, 4.13, 16.13] }
      );
      trimParts.push(
        { size: [7.45, 0.065, 0.48], position: [0, 4.14, 15.85] },
        { size: [7.45, 0.045, 0.48], position: [0, 3.76, 15.85] }
      );
      lightParts.push({ size: [5.3, 0.035, 0.025], position: [0, 4.15, 16.1] });
      addInstancedBoxes(scene, gateParts, standard(0x25384b, 0x091b2b, 0.08, 0.58, 0.48), null);
      addInstancedBoxes(scene, trimParts, standard(0xb3945e, 0x432b0f, 0.12, 0.54, 0.38), null);
      addInstancedBoxes(scene, lightParts, new THREE.MeshBasicMaterial({ color: 0xffcb7f, toneMapped: false }), null);
      addLabel(scene, 'AUTOProfit AI  •  OPERATIONS CAMPUS', [0, 4.13, 16.24], 0xffd18b, 0.7, null);
    }

    function buildStarfield() {
      const positions = [];
      for (let i = 0; i < 420; i += 1) {
        const angle = i * 2.399963;
        const radius = 42 + (i % 7) * 4.6;
        positions.push(Math.cos(angle) * radius, 10 + ((i * 37) % 78), Math.sin(angle) * radius - 5);
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      const material = new THREE.PointsMaterial({ color: 0x66cfff, size: 0.12, transparent: true, opacity: 0.7, depthWrite: false });
      scene.add(new THREE.Points(geometry, material));
    }

    function buildBackdropCity() {
      const windowMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
      // At skyline distance, thin two-sided glazing reads like the same lit
      // windows as the former tiny boxes while using one sixth of the triangles.
      const windowGeometry = new THREE.PlaneGeometry(0.28, 0.22);
      windowMaterial.side = THREE.DoubleSide;
      const capacity = 5200;
      const windows = new THREE.InstancedMesh(windowGeometry, windowMaterial, capacity);
      windows.frustumCulled = false;
      const transform = new THREE.Object3D();
      const worldUp = new THREE.Vector3(0, 1, 0);
      let count = 0;
      const boxParts = [];
      const towerParts = [];
      const mastParts = [];
      const beaconParts = [];
      const colors = [0x263d5b, 0x34385d, 0x20506a];
      const accentColors = [0x35dfff, 0xa56dff, 0x59ebcf];
      const towerProfile = [
        [0, 0.5], [0.08, 0.5], [0.08, 0.46], [0.12, 0.46], [0.12, 0.42],
        [0.29, 0.42], [0.29, 0.39], [0.33, 0.39], [0.33, 0.35], [0.5, 0.35],
        [0.5, 0.32], [0.54, 0.32], [0.54, 0.28], [0.88, 0.28], [0.9, 0.24], [1, 0.24]
      ];
      const towerRadiusAt = normalizedHeight => {
        for (let index = 1; index < towerProfile.length; index += 1) {
          const upper = towerProfile[index];
          if (normalizedHeight <= upper[0]) {
            const lower = towerProfile[index - 1];
            if (upper[0] === lower[0]) return Math.min(upper[1], lower[1]);
            const amount = (normalizedHeight - lower[0]) / (upper[0] - lower[0]);
            return lower[1] + (upper[1] - lower[1]) * amount;
          }
        }
        return towerProfile[towerProfile.length - 1][1];
      };
      const addPart = (parts, x, z, rotationY, size, position, color) => {
        const local = new THREE.Vector3(position[0], position[1], position[2]).applyAxisAngle(worldUp, rotationY);
        parts.push({
          position: [x + local.x, local.y, z + local.z],
          rotationY,
          size,
          color
        });
      };
      // Keep the existing 14-building skyline. Wider stepped mid-rises and
      // visible window bands replace the old needle-like poles without crowding
      // the orbit path around the functional campus.
      const towers = 14;
      for (let i = 0; i < towers; i += 1) {
        const angle = Math.PI * 0.36 + (i / (towers - 1)) * Math.PI * 1.28 + (i % 3) * 0.035;
        const radius = 43 + (i % 4) * 1.5;
        const width = 4.8 + (i % 5) * 0.48;
        const depth = 3.8 + ((i + 2) % 4) * 0.48;
        const height = 12.5 + ((i * 13) % 7) * 1.35;
        const x = Math.sin(angle) * radius;
        const z = Math.cos(angle) * radius;
        const rotationY = angle * 0.72;
        const baseColor = colors[i % colors.length];
        addPart(boxParts, x, z, rotationY, [width * 1.28, 0.52, depth * 1.26], [0, 0.26, 0], 0x182c47);
        towerParts.push({
          position: [x, height / 2 - 0.1, z],
          rotationY,
          size: [width, height, depth],
          color: baseColor
        });
        const crownWidth = width * (0.54 + (i % 3) * 0.12);
        addPart(boxParts, x, z, rotationY, [crownWidth, 0.85, depth * 0.72], [0, height + 0.32, 0], colors[(i + 1) % colors.length]);
        addPart(boxParts, x, z, rotationY, [width * 0.76, 0.12, depth * 0.82], [0, height + 0.82, 0], i % 3 ? 0x27dfff : 0xb278ff);
        [-1, 1].forEach(sign => {
          addPart(boxParts, x, z, rotationY, [0.075, height * 0.74, 0.085], [sign * width * 0.43, height * 0.46, depth * 0.51], accentColors[(i + (sign > 0 ? 0 : 1)) % accentColors.length]);
          addPart(boxParts, x, z, rotationY, [0.075, height * 0.74, 0.085], [depth * 0.51, height * 0.46, sign * width * 0.43], accentColors[(i + 1) % accentColors.length]);
        });
        for (let beltY = 3.4; beltY < height - 1; beltY += 3.5) {
          const radiusAtBelt = towerRadiusAt(beltY / height);
          const halfWidth = width * radiusAtBelt;
          const halfDepth = depth * radiusAtBelt;
          const beltColor = i % 4 === 0 ? 0xb58769 : 0x36516b;
          addPart(boxParts, x, z, rotationY, [halfWidth * 2, 0.075, 0.075], [0, beltY, halfDepth + 0.025], beltColor);
          addPart(boxParts, x, z, rotationY, [halfWidth * 2, 0.075, 0.075], [0, beltY, -halfDepth - 0.025], beltColor);
          addPart(boxParts, x, z, rotationY, [0.075, 0.075, halfDepth * 2], [halfWidth + 0.025, beltY, 0], beltColor);
          addPart(boxParts, x, z, rotationY, [0.075, 0.075, halfDepth * 2], [-halfWidth - 0.025, beltY, 0], beltColor);
        }
        if (i % 3 === 0) {
          addPart(boxParts, x, z, rotationY, [width * 0.62, 1.15, depth * 0.62], [0, height + 1.38, 0], 0x203952);
          mastParts.push({ position: [x, height + 3.0, z], rotationY, size: [1, 2.1 + (i % 4) * 0.38, 1], color: baseColor, type: 'spire' });
        }
        mastParts.push({ position: [x, height + 1.05, z], rotationY, size: [1, 1.7 + (i % 3) * 0.3, 1], color: 0x50748b, type: 'mast' });
        beaconParts.push({ position: [x, height + 2, z], rotationY, size: [1, 1, 1], color: 0x65efff });
        const floors = Math.floor((height - 1.4) / 1.16);
        const localWindow = new THREE.Vector3();
        for (let floor = 0; floor < floors; floor += 1) {
          const y = 0.78 + floor * 1.16;
          const radiusAtFloor = towerRadiusAt((y + 0.1) / height);
          for (let column = -1; column <= 1; column += 1) {
            const lightPattern = (i * 13 + floor * 5 + column + 3) % 9;
            const lightColor = lightPattern === 0 ? 0xffc184 : lightPattern < 4 ? 0x62d9f3 : 0x24415c;
            const addWindow = (localX, localZ, localRotation) => {
              if (count >= capacity) return;
              localWindow.set(localX, 0, localZ).applyAxisAngle(worldUp, rotationY);
              transform.position.set(x + localWindow.x, y, z + localWindow.z);
              transform.rotation.set(0, localRotation + rotationY, 0);
              transform.scale.set(1, 1, 1);
              transform.updateMatrix();
              windows.setMatrixAt(count, transform.matrix);
              windows.setColorAt(count, new THREE.Color(lightColor));
              count += 1;
            };
            const xOffset = column * width * 0.31;
            const zOffset = column * depth * 0.31;
            addWindow(xOffset, depth * radiusAtFloor + 0.035, 0);
            addWindow(xOffset, -depth * radiusAtFloor - 0.035, 0);
            addWindow(width * radiusAtFloor + 0.035, zOffset, Math.PI / 2);
            addWindow(-width * radiusAtFloor - 0.035, zOffset, Math.PI / 2);
          }
        }
      }
      const boxMesh = new THREE.InstancedMesh(
        new THREE.BoxGeometry(1, 1, 1),
        standard(0xffffff, 0x08243a, 0.34, 0.66, 0.32),
        boxParts.length
      );
      const boxTransform = new THREE.Object3D();
      boxParts.forEach((part, index) => {
        boxTransform.position.set(...part.position);
        boxTransform.rotation.set(0, part.rotationY, 0);
        boxTransform.scale.set(...part.size);
        boxTransform.updateMatrix();
        boxMesh.setMatrixAt(index, boxTransform.matrix);
        boxMesh.setColorAt(index, new THREE.Color(part.color));
      });
      boxMesh.frustumCulled = false;
      boxMesh.instanceMatrix.needsUpdate = true;
      if (boxMesh.instanceColor) boxMesh.instanceColor.needsUpdate = true;
      scene.add(boxMesh);
      backdropCityObjects.push(boxMesh);

      const towerMesh = new THREE.InstancedMesh(
        createBackdropTowerGeometry(towerProfile),
        standard(0xffffff, 0x08243a, 0.34, 0.66, 0.32),
        towerParts.length
      );
      const towerTransform = new THREE.Object3D();
      towerParts.forEach((part, index) => {
        towerTransform.position.set(...part.position);
        towerTransform.rotation.set(0, part.rotationY, 0);
        towerTransform.scale.set(...part.size);
        towerTransform.updateMatrix();
        towerMesh.setMatrixAt(index, towerTransform.matrix);
        towerMesh.setColorAt(index, new THREE.Color(part.color));
      });
      towerMesh.frustumCulled = false;
      towerMesh.instanceMatrix.needsUpdate = true;
      if (towerMesh.instanceColor) towerMesh.instanceColor.needsUpdate = true;
      scene.add(towerMesh);
      backdropCityObjects.push(towerMesh);

      const mastGeometry = new THREE.CylinderGeometry(0.045, 0.11, 1, 8);
      const mastMesh = new THREE.InstancedMesh(mastGeometry, standard(0xffffff, 0x0b293e, 0.28, 0.68, 0.3), mastParts.length);
      const mastTransform = new THREE.Object3D();
      mastParts.forEach((part, index) => {
        mastTransform.position.set(...part.position);
        mastTransform.rotation.set(0, part.rotationY, 0);
        mastTransform.scale.set(...part.size);
        mastTransform.updateMatrix();
        mastMesh.setMatrixAt(index, mastTransform.matrix);
        mastMesh.setColorAt(index, new THREE.Color(part.color));
      });
      mastMesh.frustumCulled = false;
      mastMesh.instanceMatrix.needsUpdate = true;
      if (mastMesh.instanceColor) mastMesh.instanceColor.needsUpdate = true;
      scene.add(mastMesh);
      backdropCityObjects.push(mastMesh);

      const beaconMesh = new THREE.InstancedMesh(
        new THREE.SphereGeometry(0.1, 8, 6),
        new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }),
        beaconParts.length
      );
      beaconParts.forEach((part, index) => {
        beaconMesh.setMatrixAt(index, new THREE.Matrix4().compose(
          new THREE.Vector3(...part.position),
          new THREE.Quaternion(),
          new THREE.Vector3(...part.size)
        ));
        beaconMesh.setColorAt(index, new THREE.Color(part.color));
      });
      beaconMesh.frustumCulled = false;
      beaconMesh.instanceMatrix.needsUpdate = true;
      if (beaconMesh.instanceColor) beaconMesh.instanceColor.needsUpdate = true;
      scene.add(beaconMesh);
      backdropCityObjects.push(beaconMesh);
      windows.count = count;
      windows.instanceMatrix.needsUpdate = true;
      scene.add(windows);
      backdropCityObjects.push(windows);
      addRing(scene, 22.2, 0.055, 0.02, 0x126ca0, 0.34, null, 128);
    }

    function createBackdropTowerGeometry(profile) {
      const positions = [];
      const indices = [];
      const segments = 8;
      const point = (angle, y, radius) => [Math.cos(angle) * radius, y - 0.5, Math.sin(angle) * radius];
      const quad = (a, b, c, d) => {
        const offset = positions.length / 3;
        positions.push(...a, ...b, ...c, ...d);
        indices.push(offset, offset + 1, offset + 2, offset, offset + 2, offset + 3);
      };
      for (let level = 1; level < profile.length; level += 1) {
        const lower = profile[level - 1];
        const upper = profile[level];
        for (let segment = 0; segment < segments; segment += 1) {
          const angle0 = (segment / segments) * Math.PI * 2;
          const angle1 = ((segment + 1) / segments) * Math.PI * 2;
          if (upper[0] === lower[0]) {
            const outer = Math.max(lower[1], upper[1]);
            const inner = Math.min(lower[1], upper[1]);
            if (outer - inner < 0.001) continue;
            const y = lower[0];
            if (lower[1] > upper[1]) {
              quad(point(angle0, y, outer), point(angle0, y, inner), point(angle1, y, inner), point(angle1, y, outer));
            } else {
              quad(point(angle0, y, inner), point(angle0, y, outer), point(angle1, y, outer), point(angle1, y, inner));
            }
          } else {
            quad(
              point(angle0, lower[0], lower[1]),
              point(angle0, upper[0], upper[1]),
              point(angle1, upper[0], upper[1]),
              point(angle1, lower[0], lower[1])
            );
          }
        }
      }
      const baseOffset = positions.length / 3;
      positions.push(0, -0.5, 0);
      for (let segment = 0; segment < segments; segment += 1) {
        const angle0 = (segment / segments) * Math.PI * 2;
        const angle1 = ((segment + 1) / segments) * Math.PI * 2;
        positions.push(...point(angle0, 0, profile[0][1]), ...point(angle1, 0, profile[0][1]));
        indices.push(baseOffset, baseOffset + 1 + segment * 2, baseOffset + 2 + segment * 2);
      }
      const capOffset = positions.length / 3;
      positions.push(0, 0.5, 0);
      const topRadius = profile[profile.length - 1][1];
      for (let segment = 0; segment < segments; segment += 1) {
        const angle0 = (segment / segments) * Math.PI * 2;
        const angle1 = ((segment + 1) / segments) * Math.PI * 2;
        positions.push(...point(angle0, 1, topRadius), ...point(angle1, 1, topRadius));
        indices.push(capOffset, capOffset + 2 + segment * 2, capOffset + 1 + segment * 2);
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();
      return geometry;
    }

    function buildDistrictPad(group, zone, radius, accent) {
      addMesh(group, new THREE.CylinderGeometry(radius * 0.92, radius, 0.34, 64), standard(0x0b1930, 0x042c49, 0.32, 0.74, 0.3), [0, 0.72, 0], zone, { castShadow: true });
      addMesh(group, new THREE.CylinderGeometry(radius * 0.84, radius * 0.86, 0.14, 64), standard(0x16304d, 0x064b70, 0.35, 0.7, 0.24), [0, 0.96, 0], zone);
      addRing(group, radius * 0.91, 0.055, 0.76, accent, 0.82, zone, 80);
      addRing(group, radius * 0.68, 0.028, 1.04, accent, 0.42, zone, 80);
      const railParts = [];
      for (let i = 0; i < 8; i += 1) {
        const angle = i * Math.PI / 4;
        railParts.push({ size: [0.1, 0.035, radius * 0.3], position: [Math.sin(angle) * radius * 0.8, 1.05, Math.cos(angle) * radius * 0.8], rotationY: angle });
      }
      addInstancedBoxes(group, railParts, colored(accent), zone);
    }

    function buildCommandCenter() {
      const group = registerZone('command', zoneOrigins.command);
      const frame = standard(0x182944, 0x0a5b82, 0.55, 0.78, 0.2);
      const glass = architecturalGlass(0x0a1c2b, 0x07617a, 0.17);
      const cyan = colored(0x28eaff);
      buildDistrictPad(group, 'command', 5.4, 0x27e8ff);
      addMesh(group, new THREE.CylinderGeometry(3.95, 4.35, 0.4, 48), frame, [0, 1.24, 0], 'command', { castShadow: true });
      addRing(group, 4.12, 0.08, 1.48, 0x28eaff, 0.82, 'command');
      addMesh(group, new THREE.CylinderGeometry(3.3, 3.9, 0.26, 48), standard(0x061426, 0x063350, 0.35, 0.84, 0.2), [0, 1.57, 0], 'command');
      const buttressParts = [];
      const stripParts = [];
      for (let i = 0; i < 10; i += 1) {
        const angle = i * Math.PI / 5;
        const x = Math.sin(angle) * 3.25;
        const z = Math.cos(angle) * 3.25;
        buttressParts.push({ position: [x, 3.18, z], rotation: [0, 0, -x * 0.025] });
        stripParts.push({ size: [0.07, 2.55, 0.075], position: [x * 1.02, 3.35, z * 1.02], rotationY: angle });
      }
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.14, 0.3, 3.4, 8), frame, buttressParts, 'command');
      addInstancedBoxes(group, stripParts, cyan, 'command');
      addMesh(group, new THREE.CylinderGeometry(1.75, 2.65, 4.9, 24, 3), standard(0x102d43, 0x0a6385, 0.46, 0.72, 0.2), [0, 3.85, 0], 'command', { castShadow: true });
      const coreFins = [];
      for (let i = 0; i < 16; i += 1) {
        const angle = (i + 0.5) * Math.PI * 2 / 16;
        coreFins.push({
          start: [Math.sin(angle) * 2.52, 1.92, Math.cos(angle) * 2.52],
          end: [Math.sin(angle) * 1.91, 5.74, Math.cos(angle) * 1.91]
        });
      }
      addInstancedBeams(group, coreFins, 0.105, frame, 'command', 8);
      [[2.35, 2.9], [2.17, 3.95], [1.99, 5.0], [1.87, 5.68]].forEach(([radius, y], index) => {
        addWindowRing(group, 'command', radius, y, 20, index < 2 ? 0.42 : 0.35, 0.36, index === 1 ? 0x47eaff : 0x9d68ff);
      });
      addMesh(group, new THREE.CylinderGeometry(2.45, 2.7, 0.22, 48), frame, [0, 1.74, 0], 'command');
      addMesh(group, new THREE.CylinderGeometry(2.15, 1.7, 0.24, 48), standard(0x18314e, 0x5b34bc, 0.72, 0.68, 0.22), [0, 6.2, 0], 'command');
      addRing(group, 2.58, 0.06, 1.89, 0x7c4cff, 0.76, 'command');
      addRing(group, 2.06, 0.045, 6.32, 0x4eeaff, 0.84, 'command');
      addMesh(group, new THREE.CylinderGeometry(0.45, 1.55, 2.05, 32, 1, true), new THREE.MeshPhysicalMaterial({ color: 0x36dcff, emissive: 0x006ab5, emissiveIntensity: 0.9, transparent: true, opacity: 0.18, roughness: 0.08, metalness: 0.08, side: THREE.DoubleSide, depthWrite: false }), [0, 7.23, 0], 'command');
      const brain = new THREE.Group();
      brain.position.set(0, 8.42, 0);
      brain.scale.setScalar(1.22);
      addLandmarkTarget(brain, new THREE.SphereGeometry(1.28, 16, 12), 'command', 'ai-core', 'AI Core', [0, 0, 0], [zoneOrigins.command[0], zoneOrigins.command[1] + 8.42, zoneOrigins.command[2]], 0);
      group.add(brain);
      const brainMat = new THREE.MeshPhysicalMaterial({ color: 0x1380a8, emissive: 0x07517d, emissiveIntensity: 0.46, transparent: true, opacity: 0.84, metalness: 0.14, roughness: 0.28, clearcoat: 0.48, clearcoatRoughness: 0.18, envMapIntensity: 0.86, side: THREE.DoubleSide, depthWrite: false, vertexColors: true });
      const brainLobeGeometry = createBrainLobeGeometry();
      [-1, 1].forEach(side => {
        const lobe = addMesh(brain, brainLobeGeometry, brainMat, [side * 0.58, 0.06, 0], 'command');
        lobe.scale.set(0.7, 0.92, 0.73);
      });
      const corticalFolds = [];
      [-1, 1].forEach(side => {
        [-0.82, -0.28, 0.28, 0.82].forEach((longitude, foldIndex) => {
          const points = [];
          for (let index = 0; index <= 28; index += 1) {
            const latitude = -1.02 + index / 28 * 2.04;
            const foldedLongitude = longitude + Math.sin(latitude * 4.2 + foldIndex * 1.7 + side) * 0.13;
            const radius = 1.16;
            points.push(new THREE.Vector3(
              side * 0.58 + Math.cos(latitude) * Math.sin(foldedLongitude) * 0.7 * radius,
              0.06 + Math.sin(latitude) * 0.92 * radius,
              Math.cos(latitude) * Math.cos(foldedLongitude) * 0.73 * radius
            ));
          }
          corticalFolds.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 36, 0.024, 4, false));
        });
      });
      addMesh(brain, mergeBufferGeometries(corticalFolds), new THREE.MeshBasicMaterial({ color: 0x43e7ff, transparent: true, opacity: 0.86, depthWrite: false, toneMapped: false }), null, 'command');
      const brainSeam = [];
      for (let index = 0; index <= 40; index += 1) {
        const y = -0.66 + index / 40 * 1.32;
        const normalizedY = y / 0.92;
        const normalizedX = 0.58 / 0.7;
        const z = 0.73 * Math.sqrt(Math.max(0.008, 1 - normalizedX * normalizedX - normalizedY * normalizedY));
        brainSeam.push(new THREE.Vector3(0, y, z));
      }
      const seamCurve = new THREE.CatmullRomCurve3(brainSeam);
      addMesh(brain, new THREE.TubeGeometry(seamCurve, 48, 0.028, 5, false), new THREE.MeshBasicMaterial({ color: 0x052c49, transparent: true, opacity: 0.9, depthWrite: false }), null, 'command');
      addMesh(brain, new THREE.IcosahedronGeometry(1.3, 2), new THREE.MeshBasicMaterial({ color: 0x54eaff, wireframe: true, transparent: true, opacity: 0.035, depthWrite: false }), [0, 0, 0], 'command');
      const fiberPositions = [];
      const fiberColors = [];
      const neuronGeometry = new THREE.SphereGeometry(0.055, 8, 6);
      const neurons = new THREE.InstancedMesh(neuronGeometry, new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), 22);
      const neuronTransform = new THREE.Object3D();
      neurons.frustumCulled = false;
      for (let i = 0; i < 22; i += 1) {
        const angle = i * Math.PI * 2 / 22;
        const p1 = new THREE.Vector3(Math.cos(angle) * 0.95, Math.sin(i * 1.43) * 0.62, Math.sin(angle) * 0.66);
        const p2 = new THREE.Vector3(-p1.x * 0.58, -p1.y * 0.72, -p1.z * 0.58);
        const curve = new THREE.QuadraticBezierCurve3(p1, new THREE.Vector3(0, Math.sin(angle * 2.5) * 0.45, 0), p2);
        const points = curve.getPoints(14);
        const fiberColor = new THREE.Color(i % 4 ? 0x48dfff : 0xc293ff);
        for (let segment = 0; segment < points.length - 1; segment += 1) {
          fiberPositions.push(...points[segment].toArray(), ...points[segment + 1].toArray());
          fiberColors.push(fiberColor.r, fiberColor.g, fiberColor.b, fiberColor.r, fiberColor.g, fiberColor.b);
        }
        neuronTransform.position.copy(p1);
        neuronTransform.scale.setScalar(i % 5 === 0 ? 1.22 : 1);
        neuronTransform.updateMatrix();
        neurons.setMatrixAt(i, neuronTransform.matrix);
        neurons.setColorAt(i, new THREE.Color(i % 4 ? 0x53eaff : 0xd49bff));
      }
      const fiberGeometry = new THREE.BufferGeometry();
      fiberGeometry.setAttribute('position', new THREE.Float32BufferAttribute(fiberPositions, 3));
      fiberGeometry.setAttribute('color', new THREE.Float32BufferAttribute(fiberColors, 3));
      brain.add(new THREE.LineSegments(fiberGeometry, new THREE.LineBasicMaterial({ color: 0xffffff, vertexColors: true, transparent: true, opacity: 0.72, toneMapped: false })));
      neurons.instanceMatrix.needsUpdate = true;
      if (neurons.instanceColor) neurons.instanceColor.needsUpdate = true;
      brain.add(neurons);
      animated.push({ kind: 'brain', object: brain });
      for (let i = 0; i < 3; i += 1) {
        const ring = addRing(group, 1.55 + i * 0.65, 0.038, 7.8 + i * 0.52, i % 2 ? 0x9a58ff : 0x27eaff, 0.72, 'command');
        ring.rotation.x = Math.PI / 2 + i * 0.21;
        ring.rotation.z = i * 0.53;
        commandOrbitMeshes.push(ring);
        animated.push({ kind: 'orbit-ring', object: ring, speed: i % 2 ? -0.18 : 0.14 });
      }
      addHoloScreen(group, 1.7, 0.95, [-2.7, 2.55, 1.5], 'command', 'COMMAND', 0x35eaff, 0.27);
      addHoloScreen(group, 1.7, 0.95, [2.7, 2.55, 1.5], 'command', 'AI NETWORK', 0xa667ff, -0.27);
      addLabel(group, 'AUTOProfit AI', [0, 1.5, 2.5], 0x79eaff, 0.92, 'command');
    }

    function createBrainLobeGeometry() {
      const geometry = new THREE.SphereGeometry(1, 48, 32);
      const positions = geometry.getAttribute('position');
      const point = new THREE.Vector3();
      const vertexColors = [];
      for (let index = 0; index < positions.count; index += 1) {
        point.fromBufferAttribute(positions, index).normalize();
        const longitude = Math.atan2(point.z, point.x);
        const latitude = Math.asin(clamp(point.y, -1, 1));
        const folds =
          0.11 * Math.sin(longitude * 9 + Math.sin(latitude * 3) * 1.2) * Math.sin(latitude * 7 - longitude * 0.6) +
          0.046 * Math.sin(longitude * 5 - latitude * 4) * Math.cos(latitude * 8);
        const radius = 1 + folds;
        positions.setXYZ(index, point.x * radius, point.y * radius, point.z * radius);
        const shade = clamp(0.78 + folds * 2.2, 0.58, 1);
        vertexColors.push(shade, Math.min(1, shade * 1.08), Math.min(1, shade * 1.12));
      }
      positions.needsUpdate = true;
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(vertexColors, 3));
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();
      return geometry;
    }

    function createWorkstationGeometry() {
      const parts = [
        { size: [1.35, 0.13, 0.72], position: [0, 0.78, 0] },
        ...[-0.55, 0.55].flatMap(px => [-0.27, 0.27].map(pz => ({ size: [0.07, 0.76, 0.07], position: [px, 0.39, pz] }))),
        { size: [0.72, 0.47, 0.09], position: [0, 1.08, -0.22] },
        { size: [0.08, 0.24, 0.09], position: [0, 0.84, -0.22] },
        { size: [0.42, 0.045, 0.24], position: [0, 0.73, -0.22] },
        { size: [0.43, 0.38, 0.075], position: [0.47, 1.08, -0.2], rotation: [0, -0.24, 0] },
        { size: [0.045, 0.22, 0.055], position: [0.47, 0.84, -0.2], rotation: [0, -0.24, 0] },
        { size: [0.48, 0.035, 0.2], position: [0, 0.88, 0.12] },
        { size: [0.08, 0.42, 0.08], position: [0, 0.2, 0.82] },
        { size: [0.25, 0.39, 0.35], position: [-0.41, 0.36, -0.08] },
        { size: [0.19, 0.025, 0.035], position: [-0.41, 0.4, 0.115] },
        { size: [0.72, 0.065, 0.07], position: [0, 0.73, 0.5] },
        ...[-0.38, 0.38].flatMap(px => [
          { size: [0.07, 0.055, 0.46], position: [px, 0.7, 0.79] },
          { size: [0.06, 0.18, 0.06], position: [px, 0.61, 0.58] }
        ]),
        ...[0, 1, 2, 3, 4].map(i => ({ size: [0.055, 0.035, 0.44], position: [0, 0.06, 0.82], rotation: [0, i * Math.PI * 2 / 5, 0] }))
      ];
      const positions = [];
      const normals = [];
      const uvs = [];
      const indices = [];
      parts.forEach(part => {
        const geometry = part.shape === 'sphere' ? new THREE.SphereGeometry(1, 14, 10) : new THREE.BoxGeometry(1, 1, 1);
        const rotation = part.rotation || [0, 0, 0];
        const matrix = new THREE.Matrix4().compose(
          new THREE.Vector3(...part.position),
          new THREE.Quaternion().setFromEuler(new THREE.Euler(...rotation)),
          new THREE.Vector3(...part.size)
        );
        geometry.applyMatrix4(matrix);
        const vertexOffset = positions.length / 3;
        positions.push(...geometry.attributes.position.array);
        normals.push(...geometry.attributes.normal.array);
        uvs.push(...geometry.attributes.uv.array);
        geometry.index.array.forEach(index => indices.push(index + vertexOffset));
        geometry.dispose();
      });
      const merged = new THREE.BufferGeometry();
      merged.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      merged.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
      merged.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      merged.setIndex(indices);
      merged.computeBoundingSphere();
      return merged;
    }

    function createWorkstationChairGeometry() {
      const parts = [];
      const seatShape = new THREE.Shape();
      seatShape.moveTo(-0.34, -0.24);
      seatShape.lineTo(0.34, -0.24);
      seatShape.quadraticCurveTo(0.43, -0.2, 0.4, -0.04);
      seatShape.quadraticCurveTo(0.37, 0.25, 0.25, 0.3);
      seatShape.quadraticCurveTo(0, 0.37, -0.25, 0.3);
      seatShape.quadraticCurveTo(-0.37, 0.25, -0.4, -0.04);
      seatShape.quadraticCurveTo(-0.43, -0.2, -0.34, -0.24);

      const seat = new THREE.ExtrudeGeometry(seatShape, {
        depth: 0.1, bevelEnabled: true, bevelSegments: 2, steps: 1,
        bevelSize: 0.025, bevelThickness: 0.025, curveSegments: 8
      });
      seat.rotateX(Math.PI / 2);
      seat.translate(0, 0.52, 0.82);
      parts.push(seat);

      const backShape = new THREE.Shape();
      backShape.moveTo(-0.25, -0.24);
      backShape.lineTo(0.25, -0.24);
      backShape.quadraticCurveTo(0.29, 0.04, 0.27, 0.21);
      backShape.quadraticCurveTo(0.24, 0.37, 0, 0.42);
      backShape.quadraticCurveTo(-0.24, 0.37, -0.27, 0.21);
      backShape.quadraticCurveTo(-0.29, 0.04, -0.25, -0.24);
      const back = new THREE.ExtrudeGeometry(backShape, {
        depth: 0.09, bevelEnabled: true, bevelSegments: 2, steps: 1,
        bevelSize: 0.025, bevelThickness: 0.025, curveSegments: 8
      });
      back.rotateX(0.055);
      back.translate(0, 0.8, 0.58);
      parts.push(back);

      const addChairPart = (geometry, position) => {
        geometry.translate(position[0], position[1], position[2]);
        parts.push(geometry);
      };
      const addChairPad = (scale, position) => {
        const pad = new THREE.SphereGeometry(1, 12, 8);
        pad.scale(scale[0], scale[1], scale[2]);
        addChairPart(pad, position);
      };
      addChairPad([0.27, 0.055, 0.07], [0, 0.57, 0.82]);
      addChairPad([0.17, 0.055, 0.04], [0, 0.87, 0.55]);
      addChairPad([0.23, 0.09, 0.045], [0, 1.13, 0.55]);
      [-1, 1].forEach(side => {
        addChairPart(new THREE.BoxGeometry(0.045, 0.17, 0.055), [side * 0.35, 0.66, 0.77]);
        addChairPart(new THREE.BoxGeometry(0.11, 0.045, 0.42), [side * 0.35, 0.76, 0.72]);
      });
      addChairPart(new THREE.CylinderGeometry(0.045, 0.06, 0.34, 10), [0, 0.3, 0.82]);
      addChairPart(new THREE.CylinderGeometry(0.085, 0.085, 0.08, 10), [0, 0.12, 0.82]);
      for (let index = 0; index < 5; index += 1) {
        const angle = index * Math.PI * 2 / 5;
        const wheel = new THREE.CylinderGeometry(0.045, 0.045, 0.09, 10);
        wheel.rotateX(Math.PI / 2);
        wheel.rotateY(angle + Math.PI / 2);
        addChairPart(wheel, [Math.sin(angle) * 0.22, 0.055, 0.82 + Math.cos(angle) * 0.22]);
      }
      return mergeBufferGeometries(parts);
    }

    function buildWorkstation(parent, x, z, y, zone, accent, angle) {
      const count = (workstationCounts.get(zone) || 0) + 1;
      workstationCounts.set(zone, count);
      const objectId = `${zone}-workstation-${String(count).padStart(2, '0')}`;
      const titles = { agents: 'AI Agent', ads: 'Ad Campaign', products: 'Web App Builder', revenue: 'Affiliate' };
      const worldOrigin = zoneOrigins[zone] || [0, 0, 0];
      const metadata = {
        objectId,
        objectType: 'workstation',
        zone,
        name: `${titles[zone] || zoneNames[zone]} Workstation ${String(count).padStart(2, '0')}`,
        worldPosition: [worldOrigin[0] + x, worldOrigin[1] + y, worldOrigin[2] + z],
        cameraAngle: Number.isFinite(angle) ? angle : 0,
        assignmentStatus: 'unassigned'
      };
      const station = new THREE.Group();
      station.position.set(x, y, z);
      station.rotation.y = angle || 0;
      Object.assign(station.userData, metadata);
      parent.add(station);
      if (!workstationGeometry) workstationGeometry = createWorkstationGeometry();
      let batch = workstationBatches.get(zone);
      if (!batch) {
        const screenRegion = getScreenTexture('WORKSTATION', accent);
        batch = {
          parent, zone, desks: [], screens: [], sideScreens: [], details: [], chairs: [],
          deskMaterial: standard(0x17283c, 0x0a2b40, 0.14, 0.78, 0.28),
          chairMaterial: standard(0x172331, 0x050d16, 0.04, 0.1, 0.74),
          screenMaterial: screenRegion ? screenRegion.material : new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(document.createElement('canvas')), side: THREE.DoubleSide, toneMapped: false }),
          screenUv: screenRegion && screenRegion.uv,
          detailMaterial: colored(accent)
        };
        workstationBatches.set(zone, batch);
      }
      const stationMatrix = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(0, angle || 0, 0)),
        new THREE.Vector3(1, 1, 1)
      );
      batch.desks.push({ matrix: stationMatrix });
      if (!workstationChairGeometry) workstationChairGeometry = createWorkstationChairGeometry();
      batch.chairs.push({ matrix: stationMatrix.clone() });
      const screenLocal = new THREE.Matrix4().compose(
        new THREE.Vector3(0, 1.08, -0.135),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.04, 0, 0)),
        new THREE.Vector3(1, 1, 1)
      );
      batch.screens.push({ matrix: stationMatrix.clone().multiply(screenLocal) });
      const sideScreenLocal = new THREE.Matrix4().compose(
        new THREE.Vector3(0.47, 1.08, -0.15),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.04, -0.24, 0)),
        new THREE.Vector3(1, 1, 1)
      );
      batch.sideScreens.push({ matrix: stationMatrix.clone().multiply(sideScreenLocal) });
      const detailParts = [
        { size: [0.72, 0.022, 0.025], position: [0, 1.33, -0.11] },
        { size: [0.72, 0.022, 0.025], position: [0, 0.83, -0.11] },
        { size: [0.022, 0.5, 0.025], position: [-0.37, 1.08, -0.11] },
        { size: [0.022, 0.5, 0.025], position: [0.37, 1.08, -0.11] },
        { size: [0.58, 0.035, 0.2], position: [0, 0.878, 0.105] },
        ...Array.from({ length: 23 }, (_, index) => {
          const row = Math.floor(index / 8);
          const column = index % 8;
          const rowCount = row === 0 ? 8 : row === 1 ? 8 : 7;
          return {
            size: [0.042, 0.024, 0.04],
            position: [-((rowCount - 1) * 0.064) / 2 + column * 0.064, 0.908, 0.04 + row * 0.066]
          };
        }),
        { size: [0.075, 0.035, 0.105], position: [0.48, 0.89, 0.12] }
      ];
      detailParts.forEach(part => {
        const local = new THREE.Matrix4().compose(
          new THREE.Vector3(...part.position),
          new THREE.Quaternion(),
          new THREE.Vector3(...part.size)
        );
        batch.details.push({ matrix: stationMatrix.clone().multiply(local) });
      });
      const hitProxy = new THREE.Mesh(
        new THREE.BoxGeometry(1.25, 1.4, 1.45),
        pickProxyMaterial
      );
      hitProxy.visible = false;
      hitProxy.position.set(0, 0.72, 0.35);
      Object.assign(hitProxy.userData, metadata);
      station.add(hitProxy);
      pickTargets.push(hitProxy);
      const highlight = new THREE.Mesh(new THREE.TorusGeometry(0.88, 0.045, 8, 48), new THREE.MeshBasicMaterial({ color: 0x53ffd1, transparent: true, opacity: 0.95, toneMapped: false, depthWrite: false }));
      highlight.rotation.x = Math.PI / 2;
      highlight.position.set(0, 0.7, 0.4);
      highlight.visible = false;
      highlight.userData.nonInteractive = true;
      station.add(highlight);
      workstations.set(objectId, { metadata, group: station, highlight });
      return station;
    }

    function flushWorkstationBatches() {
      workstationBatches.forEach(batch => {
        addInstancedPrimitives(batch.parent, workstationGeometry, batch.deskMaterial, batch.desks, batch.zone);
        addInstancedPrimitives(batch.parent, workstationChairGeometry, batch.chairMaterial, batch.chairs, batch.zone);
        addInstancedPrimitives(batch.parent, applyScreenAtlasUv(new THREE.PlaneGeometry(0.58, 0.32), { uv: batch.screenUv }), batch.screenMaterial, batch.screens, batch.zone);
        addInstancedPrimitives(batch.parent, applyScreenAtlasUv(new THREE.PlaneGeometry(0.34, 0.29), { uv: batch.screenUv }), batch.screenMaterial, batch.sideScreens, batch.zone);
        addInstancedPrimitives(batch.parent, new THREE.BoxGeometry(1, 1, 1), batch.detailMaterial, batch.details, batch.zone);
      });
      workstationBatches.clear();
    }

    function buildFacadeGrid(parent, zone, width, height, depth, baseY, accent, floors) {
      const frame = standard(0x132943, 0x075276, 0.34, 0.82, 0.24);
      // Reflective dark glazing with sparse warm and cyan lit panes gives each
      // building real facade rhythm without a transparent overdraw layer.
      const glass = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: 0x17232d,
        emissiveIntensity: 0.24,
        metalness: 0.62,
        roughness: 0.22,
        envMapIntensity: 0.92
      });
      const frameBoxes = [];
      const glassBoxes = [];
      const pushBox = (collection, size, position, rotationY, color) => collection.push({ size, position, rotationY: rotationY || 0, color });
      const accentPane = new THREE.Color(accent).multiplyScalar(0.62).getHex();
      const paneColor = (floor, column, face) => {
        const pattern = (floor * 7 + column * 3 + face * 5 + zone.length) % 11;
        if (pattern === 0 || pattern === 5 || pattern === 7) return 0xffbb79;
        return pattern < 7 ? accentPane : 0x142337;
      };
      const front = [1, -1];
      const floorCount = Math.max(1, floors || 3);
      const floorHeight = height / floorCount;
      const frontColumns = Math.max(3, Math.floor(width / 1.02));
      const sideColumns = Math.max(3, Math.floor(depth / 1.0));
      const paneHeight = Math.min(0.72, floorHeight * 0.66);
      const paneYInset = (floorHeight - paneHeight) / 2;
      const faceZ = depth / 2 + 0.09;
      const faceX = width / 2 + 0.09;

      front.forEach(sign => {
        const z = sign * faceZ;
        pushBox(frameBoxes, [width + 0.2, 0.13, 0.15], [0, baseY, z]);
        pushBox(frameBoxes, [width + 0.2, 0.16, 0.17], [0, baseY + height, z]);
        for (let floor = 1; floor < floorCount; floor += 1) {
          pushBox(frameBoxes, [width + 0.16, 0.075, 0.13], [0, baseY + floor * floorHeight, z]);
        }
        for (let column = 0; column <= frontColumns; column += 1) {
          const x = -width / 2 + (column / frontColumns) * width;
          const doorwayMullion = zone === 'agents' && sign > 0 && Math.abs(x) < 0.08;
          if (doorwayMullion) continue;
          pushBox(frameBoxes, [0.11, height, 0.13], [x, baseY + height / 2, z]);
        }
        for (let floor = 0; floor < floorCount; floor += 1) {
          for (let column = 0; column < frontColumns; column += 1) {
            const x = -width / 2 + ((column + 0.5) / frontColumns) * width;
            const entranceOpening = zone === 'agents' && sign > 0 && floor === 0 && Math.abs(x) < 1.1;
            if (entranceOpening) continue;
            const paneY = baseY + floor * floorHeight + paneYInset + paneHeight / 2;
            const paneWidth = width / frontColumns * 0.68;
            const paneZ = z + sign * 0.075;
            pushBox(glassBoxes, [paneWidth, paneHeight, 0.055], [x, paneY, paneZ], sign < 0 ? Math.PI : 0, paneColor(floor, column, sign));
            // Four proud mullions and a deep sill turn flat glazing tiles into
            // framed, recessed windows while staying in the existing instance.
            const frameZ = paneZ + sign * 0.055;
            const frameDepth = 0.16;
            const rail = 0.045;
            pushBox(frameBoxes, [rail, paneHeight + 0.08, frameDepth], [x - paneWidth / 2 - rail / 2, paneY, frameZ], sign < 0 ? Math.PI : 0);
            pushBox(frameBoxes, [rail, paneHeight + 0.08, frameDepth], [x + paneWidth / 2 + rail / 2, paneY, frameZ], sign < 0 ? Math.PI : 0);
            pushBox(frameBoxes, [paneWidth + 0.12, rail, frameDepth], [x, paneY - paneHeight / 2 - rail / 2, frameZ], sign < 0 ? Math.PI : 0);
            pushBox(frameBoxes, [paneWidth + 0.16, 0.075, 0.24], [x, paneY + paneHeight / 2 + 0.032, frameZ]);
          }
        }
      });

      [-1, 1].forEach(sign => {
        const x = sign * faceX;
        pushBox(frameBoxes, [0.15, 0.13, depth + 0.2], [x, baseY, 0]);
        pushBox(frameBoxes, [0.17, 0.16, depth + 0.2], [x, baseY + height, 0]);
        for (let floor = 1; floor < floorCount; floor += 1) {
          pushBox(frameBoxes, [0.13, 0.075, depth + 0.16], [x, baseY + floor * floorHeight, 0]);
        }
        for (let column = 0; column <= sideColumns; column += 1) {
          const z = -depth / 2 + (column / sideColumns) * depth;
          pushBox(frameBoxes, [0.13, height, 0.11], [x, baseY + height / 2, z]);
        }
        for (let floor = 0; floor < floorCount; floor += 1) {
          for (let column = 0; column < sideColumns; column += 1) {
            const z = -depth / 2 + ((column + 0.5) / sideColumns) * depth;
            const paneY = baseY + floor * floorHeight + paneYInset + paneHeight / 2;
            const paneLength = depth / sideColumns * 0.68;
            const paneX = x + sign * 0.075;
            pushBox(glassBoxes, [0.055, paneHeight, paneLength], [paneX, paneY, z], 0, paneColor(floor, column, sign + 2));
            const frameX = paneX + sign * 0.055;
            const frameDepth = 0.16;
            const rail = 0.045;
            pushBox(frameBoxes, [frameDepth, paneHeight + 0.08, rail], [frameX, paneY, z - paneLength / 2 - rail / 2]);
            pushBox(frameBoxes, [frameDepth, paneHeight + 0.08, rail], [frameX, paneY, z + paneLength / 2 + rail / 2]);
            pushBox(frameBoxes, [frameDepth, rail, paneLength + 0.08], [frameX, paneY - paneHeight / 2 - rail / 2, z]);
            pushBox(frameBoxes, [0.24, 0.075, paneLength + 0.16], [frameX, paneY + paneHeight / 2 + 0.032, z]);
          }
        }
      });

      const facadeFrame = addInstancedBoxes(parent, frameBoxes, frame, zone);
      const facadeGlass = addInstancedBoxes(parent, glassBoxes, glass, zone);
      if (facadeFrame) facadeFrame.userData.workstationCutaway = true;
      if (facadeGlass) facadeGlass.userData.workstationCutaway = true;

      const beaconMat = colored(accent);
      [-1, 1].forEach(xSign => [-1, 1].forEach(zSign => {
        const beacon = addMesh(parent, new THREE.SphereGeometry(0.105, 10, 8), beaconMat, [xSign * (width / 2 + 0.16), baseY + height + 0.18, zSign * (depth / 2 + 0.16)], zone);
        animated.push({ kind: 'beacon', object: beacon, phase: (xSign + 2) * 0.4 + (zSign + 2) * 0.2 });
      }));
    }

    function addWindowRing(parent, zone, radius, y, count, width, height, accent, thetaStart, thetaLength) {
      const trim = standard(0x122641, 0x073750, 0.26, 0.78, 0.25);
      const pane = standard(0x082642, accent, 0.68, 0.46, 0.16, 0.78);
      const paneBoxes = [];
      const sillBoxes = [];
      const start = thetaStart == null ? 0 : thetaStart;
      const length = thetaLength == null ? Math.PI * 2 : thetaLength;
      for (let i = 0; i < count; i += 1) {
        const angle = start + (i + 0.5) * length / count;
        const x = Math.sin(angle) * radius;
        const z = Math.cos(angle) * radius;
        paneBoxes.push({ size: [width, height, 0.075], position: [x, y, z], rotationY: angle });
        sillBoxes.push({ size: [width * 1.14, 0.055, 0.11], position: [x, y - height / 2 - 0.055, z], rotationY: angle });
      }
      addInstancedBoxes(parent, paneBoxes, pane, zone);
      addInstancedBoxes(parent, sillBoxes, trim, zone);
    }

    function buildAgents() {
      const group = registerZone('agents', zoneOrigins.agents);
      const steel = standard(0x182d48, 0x0a4066, 0.38, 0.76, 0.24);
      const glass = architecturalGlass(0x091725, 0x082537, 0.1);
      const frame = standard(0x253b57, 0x0c5470, 0.35, 0.8, 0.23);
      buildDistrictPad(group, 'agents', 4.5, 0x39dfff);
      addInstancedBoxes(group, [
        { size: [7.25, 0.35, 5.8], position: [0, 1.22, 0], color: 0x101a27 },
        { size: [6.62, 0.008, 0.025], position: [0, 1.4, -1.65], color: 0x29425a },
        { size: [6.62, 0.008, 0.025], position: [0, 1.4, 0.12], color: 0x29425a },
        { size: [6.62, 0.008, 0.025], position: [0, 1.4, 1.82], color: 0x29425a },
        { size: [0.025, 0.008, 4.96], position: [-2.18, 1.4, 0], color: 0x29425a },
        { size: [0.025, 0.008, 4.96], position: [0, 1.4, 0], color: 0x29425a },
        { size: [0.025, 0.008, 4.96], position: [2.18, 1.4, 0], color: 0x29425a }
      ], standard(0xffffff, 0x000811, 0.06, 0.52, 0.46), 'agents');
      addBox(group, [6.95, 0.24, 5.55], standard(0x142b45, 0x064464, 0.42, 0.69, 0.25), [0, 3.06, 0], 'agents', { castShadow: true }).userData.workstationCutawayBelowY = 2.5;
      addBox(group, [7.6, 0.28, 0.34], steel, [0, 5.12, -2.93], 'agents', { castShadow: true }).userData.workstationCutawayBelowY = 5.3;
      addBox(group, [7.6, 0.28, 0.34], steel, [0, 5.12, 2.93], 'agents', { castShadow: true }).userData.workstationCutawayBelowY = 5.3;
      addBox(group, [0.34, 0.28, 5.55], steel, [-3.63, 5.12, 0], 'agents', { castShadow: true }).userData.workstationCutawayBelowY = 5.3;
      addBox(group, [0.34, 0.28, 5.55], steel, [3.63, 5.12, 0], 'agents', { castShadow: true }).userData.workstationCutawayBelowY = 5.3;
      addBox(group, [7.2, 0.05, 0.08], colored(0x42dfff), [0, 4.95, 2.93], 'agents').userData.workstationCutawayBelowY = 5.3;
      const cornerPosts = [];
      const cornerLights = [];
      [-3.35, 3.35].forEach(x => [-2.55, 2.55].forEach(z => {
        cornerPosts.push({ size: [0.24, 4.1, 0.24], position: [x, 3.04, z] });
        cornerLights.push({ size: [0.07, 3.4, 0.1], position: [x * 1.01, 3.1, z + 0.12] });
      }));
      addInstancedBoxes(group, cornerPosts, frame, 'agents');
      addInstancedBoxes(group, cornerLights, colored(0x3ce8ff), 'agents');
      addBox(group, [6.9, 3.65, 0.12], glass, [0, 3.1, -2.76], 'agents').userData.workstationCutaway = true;
      addBox(group, [0.12, 3.65, 5.35], glass, [-3.48, 3.1, 0], 'agents').userData.workstationCutaway = true;
      addBox(group, [0.12, 3.65, 5.35], glass, [3.48, 3.1, 0], 'agents').userData.workstationCutaway = true;
      buildFacadeGrid(group, 'agents', 6.82, 3.35, 5.28, 1.4, 0x3ce8ff, 3);
      // Give the AI lab a readable, built entrance instead of letting its
      // lower facade read as an uninterrupted grid of windows.
      const entranceFrame = [
        ...[-0.76, 0.76].map(x => ({ size: [0.14, 1.92, 0.18], position: [x, 2.38, 2.98] })),
        { size: [1.72, 0.16, 0.46], position: [0, 3.34, 2.98] },
        { size: [2.56, 0.08, 0.58], position: [0, 3.25, 3.13] },
        { size: [2.35, 0.045, 0.055], position: [0, 3.18, 3.43] }
      ];
      addInstancedBoxes(group, entranceFrame, frame, 'agents');
      addInstancedBoxes(group, [
        { size: [2.48, 0.1, 0.36], position: [0, 1.4, 3.15] },
        { size: [2.72, 0.1, 0.38], position: [0, 1.31, 3.5] }
      ], steel, 'agents');
      const entranceGlass = addBox(group, [1.28, 1.72, 0.055], architecturalGlass(0x0a1e30, 0x0a425e, 0.24), [0, 2.36, 2.91], 'agents');
      entranceGlass.userData.workstationCutaway = true;
      entranceGlass.userData.zoneInspectionCutaway = true;
      const entranceMullion = addBox(group, [0.045, 1.58, 0.035], standard(0x36536e, 0x185274, 0.2, 0.76, 0.26), [0, 2.36, 2.95], 'agents');
      entranceMullion.userData.workstationCutaway = true;
      entranceMullion.userData.zoneInspectionCutaway = true;
      for (let floor = 0; floor < 2; floor += 1) {
        const y = 1.48 + floor * 1.84;
        [-2.2, 0, 2.2].forEach((x, index) => buildWorkstation(group, x, floor ? -0.2 : -1.0 + (index % 2) * 1.35, y, 'agents', 0x39dfff, index % 2 ? Math.PI : 0));
      }
      addHoloScreen(group, 2.6, 0.9, [0, 4.55, 2.95], 'agents', 'AI AGENTS', 0x48eaff, 0);
      addHoloScreen(group, 1.6, 0.72, [-2.5, 2.75, 2.92], 'agents', 'TASK FLOW', 0x8e78ff, 0.05);
      addHoloScreen(group, 1.6, 0.72, [2.5, 2.75, 2.92], 'agents', 'RUNTIME', 0x44eac6, -0.05);
      addMesh(group, new THREE.CylinderGeometry(0.1, 0.12, 0.82, 8), frame, [0, 5.84, -2.1], 'agents');
      const antenna = addMesh(group, new THREE.SphereGeometry(0.12, 12, 8), colored(0x42e7ff), [0, 6.3, -2.1], 'agents');
      animated.push({ kind: 'beacon', object: antenna, phase: 1.2 });
      const canopy = addMesh(
        group,
        new THREE.TorusGeometry(3.9, 0.06, 8, 112),
        standard(0x1d3a51, 0x0a3b54, 0.2, 0.86, 0.22),
        [0, 5.42, 0],
        'agents'
      );
      canopy.rotation.x = Math.PI / 2;
      canopy.userData.workstationCutawayBelowY = 5.3;
      const ribMaterial = standard(0x31536a, 0x0b526c, 0.2, 0.82, 0.26);
      [-3.2, 0, 3.2].forEach(x => {
        const rib = addTube(group, [[x, 3.4, -2.55], [x * 1.04, 4.72, -2.15], [x * 0.92, 5.72, 0], [x * 1.04, 4.72, 2.15], [x, 3.4, 2.55]], 0.035, ribMaterial, 'agents', 36);
        rib.tube.userData.workstationCutawayBelowY = 5.3;
      });
      [-2.55, 2.55].forEach(z => {
        const truss = addTube(group, [[-3.35, 5.22, z], [-2.1, 5.6, z * 1.04], [0, 5.72, z * 1.06], [2.1, 5.6, z * 1.04], [3.35, 5.22, z]], 0.03, standard(0x51486c, 0x4b3278, 0.16, 0.8, 0.24), 'agents', 32);
        truss.tube.userData.workstationCutawayBelowY = 5.3;
      });
      addGlassVault(group, 'agents', 7.15, 5.45, 5.14, 0.58, 0x42dfff, 5.3);
      const braceSegments = [];
      const addCrossBrace = (pointA, pointB) => braceSegments.push({ start: pointA, end: pointB });
      const floorLow = 1.58;
      const floorHigh = 4.88;
      addCrossBrace([-3.24, floorLow, -3.02], [3.24, floorHigh, -3.02]);
      addCrossBrace([3.24, floorLow, -3.02], [-3.24, floorHigh, -3.02]);
      [-3.56, 3.56].forEach(x => {
        addCrossBrace([x, floorLow, -2.55], [x, floorHigh, 2.55]);
        addCrossBrace([x, floorLow, 2.55], [x, floorHigh, -2.55]);
      });
      const facadeBraces = addInstancedBeams(group, braceSegments, 0.047, standard(0x506c82, 0x0b3043, 0.15, 0.86, 0.23), 'agents', 6);
      if (facadeBraces) facadeBraces.userData.workstationCutaway = true;
    }

    function buildAdNetwork() {
      const group = registerZone('ads', zoneOrigins.ads);
      const frame = standard(0x1c2d4c, 0x0c4771, 0.36, 0.76, 0.22);
      const glass = architecturalGlass(0x121426, 0x24123c, 0.14);
      buildDistrictPad(group, 'ads', 4.45, 0xb169ff);
      addMesh(group, new THREE.CylinderGeometry(3.55, 3.82, 0.38, 12), frame, [0, 1.23, 0], 'ads', { castShadow: true });
      addMesh(group, new THREE.CylinderGeometry(3.25, 3.42, 4.0, 12, 2, true, 0, Math.PI * 1.72), glass, [0, 3.34, -0.05], 'ads', { castShadow: true }).userData.workstationCutaway = true;
      const canopy = addMesh(group, new THREE.TorusGeometry(3.62, 0.12, 10, 64), standard(0x172742, 0x50359b, 0.44, 0.74, 0.21), [0, 5.43, 0], 'ads');
      canopy.rotation.x = Math.PI / 2;
      addRing(group, 3.68, 0.07, 5.56, 0xae69ff, 0.86, 'ads');
      addRing(group, 3.15, 0.04, 1.58, 0x4cdcff, 0.7, 'ads');
      const canopySpokes = [];
      for (let i = 0; i < 12; i += 1) {
        const angle = i * Math.PI / 6;
        const direction = new THREE.Vector3(Math.sin(angle), 0, Math.cos(angle));
        const rotation = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
        canopySpokes.push({ matrix: new THREE.Matrix4().compose(
          new THREE.Vector3(direction.x * 1.62, 5.38, direction.z * 1.62),
          rotation,
          new THREE.Vector3(1, 1, 1)
        ), color: i % 3 === 0 ? 0xb56cff : 0x4b718c });
      }
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.045, 0.065, 3.05, 6), standard(0x273a53, 0x39236f, 0.18, 0.84, 0.22), canopySpokes, 'ads');
      const innerCanopy = addMesh(group, new THREE.TorusGeometry(1.38, 0.075, 8, 64), standard(0x1b2946, 0x513293, 0.28, 0.78, 0.18), [0, 5.36, 0], 'ads');
      innerCanopy.rotation.x = Math.PI / 2;
      [2.4, 3.45, 4.48].forEach((y, index) => addWindowRing(group, 'ads', 3.31, y, 16, 0.54, 0.4, index === 1 ? 0xb26cff : 0x39dfff));
      const adColumnParts = [];
      const adStripParts = [];
      for (let i = 0; i < 10; i += 1) {
        const angle = i * Math.PI / 5;
        const x = Math.sin(angle) * 3.05;
        const z = Math.cos(angle) * 3.05;
        adColumnParts.push({ position: [x, 3.5, z], rotation: [0, 0, -x * 0.018] });
        adStripParts.push({ position: [x * 1.01, 3.46, z * 1.01], rotation: [0, 0, -x * 0.018], color: i % 2 ? 0x52eaff : 0xb86cff });
      }
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.09, 0.17, 4.0, 8), frame, adColumnParts, 'ads');
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.025, 0.04, 3.1, 6), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.92 }), adStripParts, 'ads');
      const adBraces = [];
      for (let i = 0; i < 10; i += 1) {
        const a = i * Math.PI / 5;
        const b = (i + 1) * Math.PI / 5;
        const point = (angle, y) => [Math.sin(angle) * 3.31, y, Math.cos(angle) * 3.31];
        adBraces.push({ start: point(a, 2.12), end: point(b, 4.92) });
        adBraces.push({ start: point(b, 2.12), end: point(a, 4.92) });
      }
      addInstancedBeams(group, adBraces, 0.052, standard(0x42516b, 0x42256c, 0.24, 0.88, 0.2), 'ads', 6);
      addMesh(group, new THREE.CylinderGeometry(0.16, 1.2, 1.45, 20, 1, true), new THREE.MeshStandardMaterial({ color: 0x182545, emissive: 0x7f39c8, emissiveIntensity: 0.5, transparent: true, opacity: 0.3, side: THREE.DoubleSide, depthWrite: false }), [0, 6.05, -0.4], 'ads');
      const layouts = [
        { p: [0, 3.7, 2.92], w: 2.45, h: 0.92, r: 0 },
        { p: [-2.48, 3.25, 1.54], w: 1.55, h: 0.85, r: 0.86 },
        { p: [2.48, 3.25, 1.54], w: 1.55, h: 0.85, r: -0.86 }
      ];
      layouts.forEach((layout, i) => addHoloScreen(group, layout.w, layout.h, layout.p, 'ads', i ? 'CAMPAIGN OPS' : 'AD NETWORK', i ? 0x38ddff : 0xb16bff, layout.r));
      for (let i = 0; i < 3; i += 1) buildWorkstation(group, -1.6 + i * 1.6, 0.25, 1.6, 'ads', 0xb46cff, 0);
      const dish = addMesh(group, new THREE.SphereGeometry(0.8, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), standard(0x223457, 0x4776be, 0.44, 0.72, 0.22), [0, 6.02, -2.05], 'ads', { castShadow: true });
      dish.rotation.x = Math.PI;
      addMesh(group, new THREE.CylinderGeometry(0.06, 0.08, 0.72, 8), frame, [0, 6.42, -2.05], 'ads');
      const beacon = addMesh(group, new THREE.SphereGeometry(0.12, 10, 8), colored(0xd59bff), [0, 6.86, -2.05], 'ads');
      animated.push({ kind: 'beacon', object: beacon, phase: 2.1 });
    }

    function buildServerRack(parent, x, z, y, zone, accent) {
      let batch = serverRackBatches.get(zone);
      if (!batch) {
        batch = {
          parent, zone,
          cases: [], caps: [], shelves: [], leds: [],
          caseMaterial: standard(0x111f36, 0x071a31, 0.35, 0.82, 0.27),
          capMaterial: standard(0x213a57, accent, 0.45, 0.75, 0.2),
          shelfMaterial: standard(0x0a182b, 0x073453, 0.25, 0.55, 0.25),
          ledMaterial: new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
        };
        serverRackBatches.set(zone, batch);
      }
      batch.cases.push({ size: [0.82, 1.8, 0.82], position: [x, y + 0.9, z] });
      batch.caps.push({ size: [0.91, 0.09, 0.9], position: [x, y + 1.85, z] });
      for (let row = 0; row < 7; row += 1) {
        batch.shelves.push({ size: [0.59, 0.105, 0.04], position: [x, y + 0.34 + row * 0.21, z + 0.43] });
        batch.leds.push({ position: [x - 0.27, y + 0.34 + row * 0.21, z + 0.47], color: row % 3 ? accent : 0x6affc7 });
      }
    }

    function flushServerRackBatches() {
      serverRackBatches.forEach(batch => {
        addInstancedBoxes(batch.parent, batch.cases, batch.caseMaterial, batch.zone);
        addInstancedBoxes(batch.parent, batch.caps, batch.capMaterial, batch.zone);
        addInstancedBoxes(batch.parent, batch.shelves, batch.shelfMaterial, batch.zone);
        addInstancedPrimitives(batch.parent, new THREE.SphereGeometry(0.034, 6, 5), batch.ledMaterial, batch.leds, batch.zone);
      });
      serverRackBatches.clear();
    }

    function buildWebApps() {
      const group = registerZone('products', zoneOrigins.products);
      const steel = standard(0x172e49, 0x084564, 0.36, 0.78, 0.22);
      const glass = architecturalGlass(0x081927, 0x06263a, 0.11);
      buildDistrictPad(group, 'products', 4.6, 0x35dfff);
      addMesh(group, new THREE.CylinderGeometry(3.5, 3.9, 0.34, 10), steel, [0, 1.22, 0], 'products', { castShadow: true });
      addInstancedBoxes(group, [
        { size: [6.1, 0.28, 5.0], position: [0, 1.53, -0.05], color: 0x101a27 },
        { size: [5.58, 0.006, 0.024], position: [0, 1.676, -1.58], color: 0x29425a },
        { size: [5.58, 0.006, 0.024], position: [0, 1.676, 0.02], color: 0x29425a },
        { size: [5.58, 0.006, 0.024], position: [0, 1.676, 1.54], color: 0x29425a },
        { size: [0.024, 0.006, 4.46], position: [-1.86, 1.676, -0.05], color: 0x29425a },
        { size: [0.024, 0.006, 4.46], position: [0, 1.676, -0.05], color: 0x29425a },
        { size: [0.024, 0.006, 4.46], position: [1.86, 1.676, -0.05], color: 0x29425a }
      ], standard(0xffffff, 0x000811, 0.06, 0.52, 0.46), 'products');
      addInstancedBoxes(group, [
        { size: [5.8, 0.18, 0.16], position: [0, 3.27, -2.42] },
        { size: [5.8, 0.18, 0.16], position: [0, 3.27, 2.22] },
        { size: [0.16, 0.18, 4.64], position: [-2.82, 3.27, -0.1] },
        { size: [0.16, 0.18, 4.64], position: [2.82, 3.27, -0.1] }
      ], standard(0x0e2943, 0x0c3a58, 0.3, 0.65, 0.25), 'products');
      addBox(group, [6.6, 0.28, 0.3], steel, [0, 4.85, -2.7], 'products', { castShadow: true });
      addBox(group, [6.6, 0.28, 0.3], steel, [0, 4.85, 2.5], 'products', { castShadow: true });
      addBox(group, [0.3, 0.28, 5.2], steel, [-3.15, 4.85, -0.1], 'products', { castShadow: true });
      addBox(group, [0.3, 0.28, 5.2], steel, [3.15, 4.85, -0.1], 'products', { castShadow: true });
      const forgePosts = [];
      const forgeLights = [];
      [-2.75, 2.75].forEach(x => [-2.25, 2.25].forEach(z => {
        forgePosts.push({ position: [x, 3.14, z] });
        forgeLights.push({ position: [x * 1.02, 3.12, z * 1.02] });
      }));
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.14, 0.2, 3.5, 8), steel, forgePosts, 'products');
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.035, 0.055, 3.1, 6), colored(0x34dfff), forgeLights, 'products');
      const roofRibs = [-2.0, 0, 2.0].map(x => ({
        matrix: new THREE.Matrix4().compose(
          new THREE.Vector3(x, 3.42, -0.1),
          new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI / 2, 0)),
          new THREE.Vector3(1, 1, 1)
        )
      }));
      addInstancedPrimitives(group, new THREE.TorusGeometry(2.34, 0.055, 6, 40, Math.PI), standard(0x234057, 0x07506b, 0.18, 0.84, 0.2), roofRibs, 'products');
      addGlassVault(group, 'products', 5.65, 4.62, 3.34, 2.22, 0x39dfff, 5.3);
      const vaultRibs = [];
      for (let rib = 0; rib < 5; rib += 1) {
        const x = -2.55 + rib * 1.275;
        for (let segment = 0; segment < 8; segment += 1) {
          const angleA = Math.PI * segment / 8;
          const angleB = Math.PI * (segment + 1) / 8;
          vaultRibs.push({
            start: [x, 4.62 + Math.sin(angleA) * 2.26, Math.cos(angleA) * 2.34],
            end: [x, 4.62 + Math.sin(angleB) * 2.26, Math.cos(angleB) * 2.34]
          });
        }
      }
      const vaultFrame = addInstancedBeams(group, vaultRibs, 0.042, standard(0x43667c, 0x08718e, 0.2, 0.9, 0.2), 'products', 6);
      if (vaultFrame) vaultFrame.userData.workstationCutawayBelowY = 5.3;
      const appEntryGlass = addBox(group, [5.65, 3.0, 0.12], glass, [0, 3.2, 2.37], 'products');
      appEntryGlass.userData.workstationCutaway = true;
      appEntryGlass.userData.zoneInspectionCutaway = true;
      buildFacadeGrid(group, 'products', 5.56, 1.48, 4.62, 1.64, 0x39dfff, 2);
      for (let i = 0; i < 4; i += 1) buildServerRack(group, -2.1 + i * 1.4, -2.0, 1.7, 'products', 0x29e4ff);
      addHoloScreen(group, 3.0, 0.92, [0, 4.25, 2.62], 'products', 'WEB APPS', 0x54eaff, 0);
      addHoloScreen(group, 1.5, 0.78, [-2.45, 2.78, 2.63], 'products', 'APP BUILDER', 0x9b78ff, 0.06);
      addHoloScreen(group, 1.5, 0.78, [2.45, 2.78, 2.63], 'products', 'DEPLOY HUB', 0x44eac6, -0.06);
      flushServerRackBatches();
      for (let i = 0; i < 3; i += 1) buildWorkstation(group, -1.8 + i * 1.8, 0.5, 1.72, 'products', 0x39dfff, 0);
      for (let i = 0; i < 5; i += 1) {
        const pod = addMesh(group, new THREE.CylinderGeometry(0.36, 0.58, 2.0 + (i % 2) * 0.6, 6), standard(0x12304a, 0x0875a0, 0.42, 0.72, 0.24), [-2.8 + i * 1.4, 2.65, -2.25], 'products');
        pod.rotation.y = Math.PI / 8;
        addRing(group, 0.47, 0.03, 1.8, 0x30dfff, 0.62, 'products', 32).position.x = -2.8 + i * 1.4;
      }
    }

    function buildDataHub() {
      const group = registerZone('live', zoneOrigins.live);
      buildDistrictPad(group, 'live', 4.55, 0x28e6ff);
      const pedestal = standard(0x102640, 0x08719a, 0.45, 0.76, 0.2);
      [2.15, 1.72, 1.32].forEach((radius, index) => addMesh(group, new THREE.CylinderGeometry(radius, radius * 1.08, index ? 0.22 : 0.3, 64), pedestal, [0, 1.24 + index * 0.25, 0], 'live', { castShadow: true }));
      [1.5, 1.95, 2.45, 3.0].forEach((radius, index) => {
        const ring = addRing(group, radius, index === 0 ? 0.06 : 0.032, 1.53 + (index % 2) * 0.28, index % 2 ? 0x9f65ff : 0x29e8ff, 0.82, 'live', 80);
        animated.push({ kind: 'orbit-ring', object: ring, speed: index % 2 ? -0.2 : 0.16 });
      });
      const globeSupports = [0, Math.PI / 3, Math.PI * 2 / 3].map(angle => ({
        matrix: new THREE.Matrix4().compose(
          new THREE.Vector3(0, 3.45, 0),
          new THREE.Quaternion().setFromEuler(new THREE.Euler(0, angle, 0)),
          new THREE.Vector3(1, 1, 1)
        )
      }));
      addInstancedPrimitives(group, new THREE.TorusGeometry(2.0, 0.045, 6, 48, Math.PI), standard(0x23384f, 0x07536a, 0.18, 0.84, 0.2), globeSupports, 'live');
      const hubCradle = [];
      for (let i = 0; i < 8; i += 1) {
        const angle = i * Math.PI / 4;
        hubCradle.push({
          start: [Math.sin(angle) * 1.54, 1.78, Math.cos(angle) * 1.54],
          end: [Math.sin(angle + 0.18) * 2.0, 3.05, Math.cos(angle + 0.18) * 2.0]
        });
      }
      addInstancedBeams(group, hubCradle, 0.065, standard(0x46647c, 0x08617d, 0.28, 0.9, 0.18), 'live', 8);
      const globeGroup = new THREE.Group();
      globeGroupRef = globeGroup;
      globeGroup.position.set(0, 3.55, 0);
      globeGroup.scale.setScalar(1.08);
      addLandmarkTarget(globeGroup, new THREE.SphereGeometry(1.88, 24, 16), 'global', 'traffic-globe', 'Global Traffic Globe', [0, 0, 0], [zoneOrigins.live[0], zoneOrigins.live[1] + 3.55, zoneOrigins.live[2]], 0);
      globeGroup.userData.zone = 'global';
      globeGroup.userData.objectId = 'zone:global';
      globeGroup.userData.objectType = 'zone';
      globeGroup.userData.objectName = zoneNames.global;
      globeGroup.userData.worldPosition = [0, 3.55, 0];
      globeGroup.materials = [];
      group.add(globeGroup);
      zoneGroups.set('global', globeGroup);
      const atmosphere = addMesh(globeGroup, new THREE.SphereGeometry(1.67, 32, 22), new THREE.MeshPhysicalMaterial({ color: 0x20baff, emissive: 0x0068d0, emissiveIntensity: 0.42, transparent: true, opacity: 0.1, roughness: 0.16, metalness: 0.08, side: THREE.DoubleSide, depthWrite: false }), [0, 0, 0], 'global');
      const globe = addMesh(globeGroup, new THREE.SphereGeometry(1.42, 32, 24), new THREE.MeshStandardMaterial({ color: 0x16405f, emissive: 0x07496a, emissiveIntensity: 0.32, metalness: 0.18, roughness: 0.3 }), [0, 0, 0], 'global');
      const latitudeParts = [0, 0.58, -0.58].map((angle, index) => {
        const radius = 1.51 - Math.abs(angle) * 0.25;
        return {
          matrix: new THREE.Matrix4().compose(
            new THREE.Vector3(0, Math.sin(angle) * 0.72, 0),
            new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, 0)),
            new THREE.Vector3(radius, radius, 1)
          ),
          color: index === 1 ? 0xb381ff : 0x49e7ff
        };
      });
      addInstancedPrimitives(globeGroup, new THREE.TorusGeometry(1, 0.012, 6, 72), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.68 }), latitudeParts, 'global');
      const longitudeParts = [];
      for (let i = 0; i < 8; i += 1) {
        longitudeParts.push({
          matrix: new THREE.Matrix4().compose(
            new THREE.Vector3(0, 0, 0),
            new THREE.Quaternion().setFromEuler(new THREE.Euler(0, i * Math.PI / 8, 0)),
            new THREE.Vector3(1, 1, 1)
          ),
          color: i % 2 ? 0x31cfff : 0x8e63ff
        });
      }
      addInstancedPrimitives(globeGroup, new THREE.TorusGeometry(1.5, 0.014, 6, 72), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.46 }), longitudeParts, 'global');
      const continentPolygons = [
        [[-168,71],[-145,72],[-128,63],[-112,58],[-96,54],[-82,50],[-66,46],[-60,34],[-78,8],[-94,17],[-108,25],[-117,34],[-126,49],[-147,59],[-160,60]],
        [[-81,12],[-69,10],[-57,5],[-49,-7],[-52,-21],[-61,-34],[-70,-54],[-77,-45],[-74,-29],[-80,-12]],
        [[-12,70],[7,72],[29,61],[31,51],[24,43],[14,37],[-3,36],[-11,46]],
        [[-18,36],[6,38],[31,31],[47,11],[43,-12],[31,-33],[19,-35],[8,-25],[-1,-8],[-14,12]],
        [[30,70],[54,78],[92,76],[128,69],[157,59],[170,50],[145,41],[132,32],[119,20],[102,8],[83,8],[68,24],[52,29],[39,44]],
        [[112,-11],[132,-12],[151,-18],[154,-29],[142,-39],[126,-35],[114,-24]],
        [[-52,83],[-35,78],[-25,67],[-39,58],[-52,61],[-59,72]]
      ];
      const mapArt = document.createElement('canvas');
      mapArt.width = 1024;
      mapArt.height = 512;
      const mapCtx = mapArt.getContext('2d');
      mapCtx.fillStyle = '#04162f';
      mapCtx.fillRect(0, 0, mapArt.width, mapArt.height);
      mapCtx.strokeStyle = 'rgba(60, 207, 255, 0.2)';
      mapCtx.lineWidth = 1;
      for (let longitude = -150; longitude <= 180; longitude += 30) {
        const x = ((longitude + 180) / 360) * mapArt.width;
        mapCtx.beginPath(); mapCtx.moveTo(x, 0); mapCtx.lineTo(x, mapArt.height); mapCtx.stroke();
      }
      for (let latitude = -75; latitude <= 75; latitude += 15) {
        const y = ((90 - latitude) / 180) * mapArt.height;
        mapCtx.beginPath(); mapCtx.moveTo(0, y); mapCtx.lineTo(mapArt.width, y); mapCtx.stroke();
      }
      const continentColors = ['#50c7de', '#52d9c3', '#6be0cf', '#5bdbc0', '#8b91ed', '#65d7ad', '#56cce0'];
      continentPolygons.forEach((polygon, index) => {
        mapCtx.beginPath();
        polygon.forEach(([longitude, latitude], pointIndex) => {
          const x = ((longitude + 180) / 360) * mapArt.width;
          const y = ((90 - latitude) / 180) * mapArt.height;
          if (pointIndex === 0) mapCtx.moveTo(x, y); else mapCtx.lineTo(x, y);
        });
        mapCtx.closePath();
        mapCtx.fillStyle = continentColors[index];
        mapCtx.globalAlpha = 0.76;
        mapCtx.fill();
        mapCtx.globalAlpha = 0.95;
        mapCtx.strokeStyle = '#a2f6ff';
        mapCtx.lineWidth = 2;
        mapCtx.stroke();
      });
      mapCtx.globalAlpha = 1;
      const globeTexture = new THREE.CanvasTexture(mapArt);
      globeTexture.mapping = THREE.UVMapping;
      globeTexture.wrapS = THREE.RepeatWrapping;
      if (globeTexture.colorSpace !== undefined && THREE.SRGBColorSpace) globeTexture.colorSpace = THREE.SRGBColorSpace;
      else if (globeTexture.encoding !== undefined && THREE.sRGBEncoding) globeTexture.encoding = THREE.sRGBEncoding;
      globeTexture.needsUpdate = true;
      globe.material.map = globeTexture;
      globe.material.emissiveMap = globeTexture;
      globe.material.emissive.set(0x1189c9);
      globe.material.emissiveIntensity = 0.48;
      globe.material.needsUpdate = true;
      const contains = (longitude, latitude, polygon) => {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
          const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
          if ((yi > latitude) !== (yj > latitude) && longitude < ((xj - xi) * (latitude - yi)) / ((yj - yi) || 1e-9) + xi) inside = !inside;
        }
        return inside;
      };
      const mapNodes = [];
      for (let latitude = -54; latitude <= 78; latitude += 6) {
        for (let longitude = -174; longitude <= 174; longitude += 6) {
          const continent = continentPolygons.findIndex(polygon => contains(longitude, latitude, polygon));
          if (continent >= 0) mapNodes.push({ longitude, latitude, continent });
        }
      }
      const beaconCount = mapNodes.length;
      const beaconGeometry = new THREE.SphereGeometry(1, 6, 5);
      const beaconMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
      const beacons = new THREE.InstancedMesh(beaconGeometry, beaconMaterial, beaconCount);
      const beaconTransform = new THREE.Object3D();
      mapNodes.forEach((node, index) => {
        const latitude = THREE.MathUtils.degToRad(node.latitude);
        const longitude = THREE.MathUtils.degToRad(node.longitude);
        const r = 1.51;
        const scale = 0.027 + (index % 3) * 0.006;
        beaconTransform.position.set(Math.cos(latitude) * Math.sin(longitude) * r, Math.sin(latitude) * r, Math.cos(latitude) * Math.cos(longitude) * r);
        beaconTransform.scale.setScalar(scale);
        beaconTransform.updateMatrix();
        beacons.setMatrixAt(index, beaconTransform.matrix);
        beacons.setColorAt(index, new THREE.Color(node.continent === 4 ? 0x8c86ff : node.continent === 3 ? 0x6af2db : 0x42dfff));
      });
      beacons.instanceMatrix.needsUpdate = true;
      if (beacons.instanceColor) beacons.instanceColor.needsUpdate = true;
      // Some supported Three.js builds do not expose InstancedMesh.computeBoundingSphere().
      // The constellation is tiny (46 points), so keep it visible without version-specific bounds.
      beacons.frustumCulled = false;
      beacons.name = 'Data Hub beacon constellation';
      globeGroup.add(beacons);
      const outlinePositions = [];
      const outlineColors = [];
      continentPolygons.forEach((polygon, index) => {
        const points = polygon.map(([longitude, latitude]) => {
          const lat = THREE.MathUtils.degToRad(latitude), lon = THREE.MathUtils.degToRad(longitude), radius = 1.535;
          return new THREE.Vector3(Math.cos(lat) * Math.sin(lon) * radius, Math.sin(lat) * radius, Math.cos(lat) * Math.cos(lon) * radius);
        });
        const color = new THREE.Color(index === 4 ? 0xb1a1ff : 0x9bfbff);
        points.forEach((point, pointIndex) => {
          outlinePositions.push(...point.toArray(), ...points[(pointIndex + 1) % points.length].toArray());
          outlineColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
        });
      });
      const outlineGeometry = new THREE.BufferGeometry();
      outlineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(outlinePositions, 3));
      outlineGeometry.setAttribute('color', new THREE.Float32BufferAttribute(outlineColors, 3));
      const outlineMesh = new THREE.LineSegments(outlineGeometry, new THREE.LineBasicMaterial({ color: 0xffffff, vertexColors: true, transparent: true, opacity: 0.82 }));
      outlineMesh.userData.zone = 'global';
      outlineMesh.userData.objectId = 'zone:global';
      outlineMesh.userData.objectType = 'zone';
      outlineMesh.userData.objectName = zoneNames.global;
      globeGroup.add(outlineMesh);
      animated.push({ kind: 'globe', object: globeGroup, speed: 0.13 });
      const orbitA = addMesh(globeGroup, new THREE.TorusGeometry(2.05, 0.04, 8, 96), new THREE.MeshBasicMaterial({ color: 0x31e6ff, transparent: true, opacity: 0.76 }), [0, 0, 0], 'global');
      orbitA.rotation.set(0.88, 0.1, 0.14);
      const orbitB = addMesh(globeGroup, new THREE.TorusGeometry(2.25, 0.026, 8, 96), new THREE.MeshBasicMaterial({ color: 0xb16cff, transparent: true, opacity: 0.72 }), [0, 0, 0], 'global');
      orbitB.rotation.set(1.1, -0.6, 0.5);
      animated.push({ kind: 'orbit-ring', object: orbitA, speed: 0.22 }, { kind: 'orbit-ring', object: orbitB, speed: -0.16 });
      const satellitePositions = [[-2.75, 2.1, 1.4], [2.75, 2.1, 1.4], [-2.75, 2.1, -1.4], [2.75, 2.1, -1.4]];
      satellitePositions.forEach((position, index) => {
        addMesh(group, new THREE.CylinderGeometry(0.08, 0.12, 1.9, 8), standard(0x263956, 0x0b486e, 0.4, 0.8, 0.25), [position[0], 2.0, position[2]], 'live');
        addHoloScreen(group, 1.0, 0.63, [position[0], 3.0, position[2] + (position[2] > 0 ? 0.12 : -0.12)], 'live', index % 2 ? 'LIVE FEED' : 'DATA NODE', index % 2 ? 0x9b6cff : 0x29eaff, position[0] < 0 ? 0.22 : -0.22);
      });
      addLabel(group, 'DATA HUB', [0, 1.52, 2.18], 0x76edff, 0.76, 'live');
      addLabel(globeGroup, 'GLOBAL TRAFFIC', [0, 2.42, 0], 0x91ddff, 0.62, 'global');
    }

    function buildAffiliate() {
      const group = registerZone('revenue', zoneOrigins.revenue);
      const frame = standard(0x1e2b4a, 0x6a359f, 0.42, 0.78, 0.22);
      const glass = architecturalGlass(0x121526, 0x221138, 0.15);
      buildDistrictPad(group, 'revenue', 4.5, 0xbd70ff);
      addMesh(group, new THREE.CylinderGeometry(3.45, 3.8, 0.34, 32), frame, [0, 1.22, 0], 'revenue', { castShadow: true });
      addMesh(group, new THREE.CylinderGeometry(3.05, 3.15, 2.75, 24, 1, true, Math.PI / 4, Math.PI * 1.5), glass, [0, 2.76, 0], 'revenue').userData.workstationCutaway = true;
      const openCrown = addMesh(group, new THREE.TorusGeometry(3.58, 0.12, 10, 96), standard(0x1b2946, 0x6740a5, 0.4, 0.74, 0.21), [0, 4.28, 0], 'revenue');
      openCrown.rotation.x = Math.PI / 2;
      openCrown.scale.set(1, 0.82, 1);
      addRing(group, 3.78, 0.06, 4.42, 0xd179ff, 0.8, 'revenue');
      addRing(group, 3.08, 0.035, 1.5, 0x6eeaff, 0.72, 'revenue');
      [2.18, 3.24].forEach((y, index) => addWindowRing(group, 'revenue', 3.12, y, 15, 0.4, 0.42, index ? 0xb46cff : 0x3ddfff, Math.PI / 4, Math.PI * 1.5));
      const affiliateColumnParts = [];
      const affiliateStripParts = [];
      for (let i = 0; i < 10; i += 1) {
        const angle = i * Math.PI / 5;
        const x = Math.sin(angle) * 3.1;
        const z = Math.cos(angle) * 3.1;
        affiliateColumnParts.push({ position: [x, 2.78, z], rotation: [0, 0, -x * 0.02] });
        affiliateStripParts.push({ position: [x, 2.76, z], rotation: [0, 0, -x * 0.02], color: i % 3 ? 0x45dfff : 0xb76cff });
      }
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.1, 0.18, 2.95, 8), frame, affiliateColumnParts, 'revenue');
      addInstancedPrimitives(group, new THREE.CylinderGeometry(0.025, 0.04, 2.45, 6), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.92 }), affiliateStripParts, 'revenue');
      const affiliateBraces = [];
      for (let i = 0; i < 10; i += 1) {
        const a = Math.PI / 4 + i * Math.PI / 5;
        const b = Math.PI / 4 + (i + 1) * Math.PI / 5;
        const point = (angle, y) => [Math.sin(angle) * 3.1, y, Math.cos(angle) * 3.1];
        affiliateBraces.push({ start: point(a, 1.78), end: point(b, 4.12) });
        affiliateBraces.push({ start: point(b, 1.78), end: point(a, 4.12) });
      }
      addInstancedBeams(group, affiliateBraces, 0.048, standard(0x483e67, 0x5c2f91, 0.22, 0.88, 0.2), 'revenue', 6);
      for (let i = 0; i < 5; i += 1) {
        const angle = (i - 2) * Math.PI / 7;
        const x = Math.sin(angle) * 2.3;
        const z = Math.cos(angle) * 2.3 + 0.15;
        addHoloScreen(group, 1.05, 0.72, [x, 3.05, z], 'revenue', i % 2 ? 'PARTNER' : 'REVENUE', i % 2 ? 0x35dcff : 0xd17bff, -angle * 0.36);
      }
      for (let i = 0; i < 3; i += 1) buildWorkstation(group, -1.5 + i * 1.5, 1.0, 1.62, 'revenue', 0xb56cff, 0);
      const funnel = addMesh(group, new THREE.CylinderGeometry(1.55, 0.46, 1.85, 20, 1, true), new THREE.MeshPhysicalMaterial({ color: 0x432e6e, emissive: 0x6b38b7, emissiveIntensity: 0.72, metalness: 0.22, roughness: 0.18, transparent: true, opacity: 0.52, side: THREE.DoubleSide, depthWrite: false }), [0, 3.08, -0.15], 'revenue');
      addRing(group, 1.52, 0.04, 3.97, 0xe3a4ff, 0.74, 'revenue', 64);
      addMesh(group, new THREE.CylinderGeometry(0.3, 0.5, 0.42, 16), standard(0x352958, 0xa24de0, 0.5, 0.68, 0.2), [0, 1.96, -0.15], 'revenue');
      addHoloScreen(group, 2.6, 0.9, [0, 4.92, -1.6], 'revenue', 'AFFILIATE HUB', 0xc17aff, 0);
      const beacon = addMesh(group, new THREE.SphereGeometry(0.17, 12, 8), colored(0xe2a0ff), [0, 5.45, -2.45], 'revenue');
      animated.push({ kind: 'beacon', object: beacon, phase: 0.8 });
      addLabel(group, 'AFFILIATE', [0, 5.05, 2.3], 0xd3a0ff, 0.86, 'revenue');
    }

    function buildEnergyRoutes() {
      const routes = [
        [[0, 0.72, -2.9], [-1.7, 0.8, -5], [-5, 0.82, -6.4], [-8.0, 0.84, -7.1]],
        [[0, 0.72, -2.9], [1.7, 0.8, -5], [5, 0.82, -6.4], [8.0, 0.84, -7.1]],
        [[0, 0.72, -2.5], [-2.5, 0.8, 1.1], [-6.2, 0.82, 4.8], [-8.9, 0.84, 6.5]],
        [[0, 0.72, -2.5], [2.5, 0.8, 1.1], [6.2, 0.82, 4.8], [8.9, 0.84, 6.5]],
        [[0, 0.72, -2.2], [0, 0.8, 2.1], [0, 0.82, 5.8], [0, 0.84, 8.9]]
      ];
      const baseGeometries = [];
      const energyGeometries = [[], []];
      const tracks = [];
      routes.forEach((points, index) => {
        const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(point[0], point[1], point[2])));
        const flowCurve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(point[0], point[1] + 0.12, point[2])));
        baseGeometries.push(new THREE.TubeGeometry(curve, 48, 0.12, 8, false));
        energyGeometries[index % 2].push(new THREE.TubeGeometry(flowCurve, 48, 0.025, 8, false));
        tracks.push({ curve: flowCurve, phase: index * 0.19, direction: index % 2 ? -1 : 1 });
      });
      addMesh(scene, mergeBufferGeometries(baseGeometries), standard(0x07172a, 0x09243b, 0.22, 0.65, 0.24), null);
      energyGeometries.forEach((geometries, index) => {
        addMesh(scene, mergeBufferGeometries(geometries), new THREE.MeshBasicMaterial({ color: index ? 0xa660ff : 0x1adfff, transparent: true, opacity: 0.62 }), null);
      });
      const pulseMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(0.14, 10, 8), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), tracks.length);
      const pulseTransform = new THREE.Object3D();
      pulseMesh.frustumCulled = false;
      tracks.forEach((track, index) => {
        pulseTransform.position.copy(track.curve.getPoint(track.phase));
        pulseTransform.updateMatrix();
        pulseMesh.setMatrixAt(index, pulseTransform.matrix);
        pulseMesh.setColorAt(index, new THREE.Color(index % 2 ? 0xd3a1ff : 0x9af7ff));
      });
      pulseMesh.instanceMatrix.needsUpdate = true;
      if (pulseMesh.instanceColor) pulseMesh.instanceColor.needsUpdate = true;
      scene.add(pulseMesh);
      animated.push({ kind: 'energy-pulses', object: pulseMesh, tracks, transform: pulseTransform });
    }

    function batchHoloScreens() {
      const batches = new Map();
      let sourceCount = 0;
      scene.updateMatrixWorld(true);
      scene.traverse(object => {
        if (!object.isMesh || !object.userData.holoAtlas || !object.geometry || !object.material) return;
        const zone = object.userData.zone;
        const group = zoneGroups.get(zone);
        if (!group) return;
        const key = [zone, object.material.uuid, object.renderOrder, object.layers.mask].join(':');
        let batch = batches.get(key);
        if (!batch) batches.set(key, batch = { zone, group, material: object.material, meshes: [] });
        batch.meshes.push(object);
      });

      let mergedCount = 0;
      batches.forEach(batch => {
        if (batch.meshes.length < 2) return;
        const toZoneLocal = batch.group.matrixWorld.clone().invert();
        const geometries = batch.meshes.map(mesh => {
          const geometry = mesh.geometry.clone();
          geometry.applyMatrix4(toZoneLocal.clone().multiply(mesh.matrixWorld));
          return geometry;
        });
        const merged = new THREE.Mesh(mergeBufferGeometries(geometries), batch.material);
        merged.name = `${batch.zone} holo screen atlas batch`;
        merged.renderOrder = batch.meshes[0].renderOrder;
        merged.layers.mask = batch.meshes[0].layers.mask;
        merged.userData.zone = batch.zone;
        merged.userData.objectId = `zone:${batch.zone}`;
        merged.userData.objectType = 'zone';
        merged.userData.objectName = zoneNames[batch.zone] || batch.zone;
        merged.userData.workstationCutaway = true;
        merged.userData.hologram = true;
        const sources = new Set(batch.meshes);
        const wasPickable = batch.meshes.some(mesh => zonePickTargets.includes(mesh));
        batch.meshes.forEach(mesh => mesh.parent && mesh.parent.remove(mesh));
        for (let index = zonePickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(zonePickTargets[index])) zonePickTargets.splice(index, 1);
        }
        batch.group.add(merged);
        if (wasPickable) zonePickTargets.push(merged);
        sourceCount += batch.meshes.length;
        mergedCount += 1;
      });
      return { sourceMeshes: sourceCount, mergedMeshes: mergedCount };
    }

    function batchStaticMeshes() {
      const animatedObjects = new Set(animated.map(item => item.object).filter(Boolean));
      const batches = new Map();
      const boxBatches = new Map();
      const transparentBatches = new Map();
      let sourceCount = 0;
      scene.updateMatrixWorld(true);
      scene.traverse(object => {
        if (!object.isMesh || object.isInstancedMesh || object.isSkinnedMesh || !object.geometry || !object.material) return;
        if (Array.isArray(object.material) || !object.material.transparent || object.material.depthWrite !== false) return;
        if (object.material.map || object.material.vertexColors || object.material.wireframe) return;
        if (object.userData.workstationCutawayBelowY !== undefined || object.userData.objectType === 'workstation' || object.userData.holoAtlas) return;
        if (pickTargets.includes(object)) return;
        const attributes = Object.keys(object.geometry.attributes || {}).sort();
        if (attributes.join(',') !== 'normal,position,uv') return;
        let ancestor = object;
        while (ancestor && ancestor !== scene) {
          if (animatedObjects.has(ancestor) || ancestor.userData?.objectType === 'workstation') return;
          ancestor = ancestor.parent;
        }
        if (object.userData.objectType && object.userData.objectType !== 'zone') return;
        let zone = object.userData.zone || null;
        if (!zone) {
          let current = object.parent;
          while (current && current !== scene && !zone) {
            zone = current.userData.zone || null;
            current = current.parent;
          }
        }
        const cutaway = !!object.userData.workstationCutaway;
        const inspectionCutaway = !!object.userData.zoneInspectionCutaway;
        const key = [object.material.uuid, zone || '', object.renderOrder, object.layers.mask, cutaway ? 1 : 0, inspectionCutaway ? 1 : 0].join(':');
        let batch = transparentBatches.get(key);
        if (!batch) transparentBatches.set(key, batch = { material: object.material, zone, cutaway, inspectionCutaway, meshes: [] });
        batch.meshes.push(object);
      });

      scene.traverse(object => {
        if (!object.isMesh || object.isInstancedMesh || object.isSkinnedMesh || !object.geometry || object.geometry.type !== 'BoxGeometry' || !object.material) return;
        if (Array.isArray(object.material) || object.material.transparent || object.material.opacity < 0.999 || object.material.depthWrite === false) return;
        if (object.userData.workstationCutaway || object.userData.workstationCutawayBelowY !== undefined || object.userData.objectType === 'workstation') return;
        if (pickTargets.includes(object)) return;
        let ancestor = object;
        while (ancestor && ancestor !== scene) {
          if (animatedObjects.has(ancestor) || ancestor.userData?.objectType === 'workstation') return;
          ancestor = ancestor.parent;
        }
        if (object.userData.objectType && object.userData.objectType !== 'zone') return;
        let zone = object.userData.zone || null;
        if (!zone) {
          let current = object.parent;
          while (current && current !== scene && !zone) {
            zone = current.userData.zone || null;
            current = current.parent;
          }
        }
        const key = [
          object.material.uuid, zone || '', object.renderOrder, object.layers.mask,
          object.castShadow ? 1 : 0, object.receiveShadow ? 1 : 0, object.frustumCulled ? 1 : 0
        ].join(':');
        let batch = boxBatches.get(key);
        if (!batch) boxBatches.set(key, batch = { material: object.material, zone, meshes: [] });
        batch.meshes.push(object);
      });

      let transparentMergedCount = 0;
      let transparentPickMeshCount = 0;
      transparentBatches.forEach(batch => {
        if (batch.meshes.length < 2) return;
        const targetParent = batch.cutaway && batch.zone ? zoneGroups.get(batch.zone) || scene : scene;
        const toParentLocal = targetParent === scene ? null : targetParent.matrixWorld.clone().invert();
        const geometries = batch.meshes.map(mesh => {
          const geometry = mesh.geometry.clone();
          const matrix = toParentLocal ? toParentLocal.clone().multiply(mesh.matrixWorld) : mesh.matrixWorld;
          geometry.applyMatrix4(matrix);
          return geometry;
        });
        const merged = new THREE.Mesh(mergeBufferGeometries(geometries), batch.material);
        merged.name = `${batch.zone || 'scene'} static transparent geometry batch`;
        merged.renderOrder = batch.meshes[0].renderOrder;
        merged.layers.mask = batch.meshes[0].layers.mask;
        if (batch.zone) {
          merged.userData.zone = batch.zone;
          merged.userData.objectId = `zone:${batch.zone}`;
          merged.userData.objectType = 'zone';
          merged.userData.objectName = zoneNames[batch.zone] || batch.zone;
        }
        if (batch.cutaway) merged.userData.workstationCutaway = true;
        if (batch.inspectionCutaway) merged.userData.zoneInspectionCutaway = true;
        const sources = new Set(batch.meshes);
        const wasPickable = batch.meshes.some(mesh => zonePickTargets.includes(mesh));
        batch.meshes.forEach(mesh => mesh.parent && mesh.parent.remove(mesh));
        for (let index = zonePickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(zonePickTargets[index])) zonePickTargets.splice(index, 1);
        }
        targetParent.add(merged);
        if (wasPickable && batch.zone) {
          zonePickTargets.push(merged);
          transparentPickMeshCount += 1;
        }
        sourceCount += batch.meshes.length;
        transparentMergedCount += 1;
      });

      let boxMergedCount = 0;
      let boxPickMeshCount = 0;
      boxBatches.forEach(batch => {
        if (batch.meshes.length < 2) return;
        const geometry = shareGeometry(new THREE.BoxGeometry(1, 1, 1));
        const merged = new THREE.InstancedMesh(geometry, batch.material, batch.meshes.length);
        const scaleMatrix = new THREE.Matrix4();
        batch.meshes.forEach((mesh, index) => {
          const dimensions = mesh.geometry.parameters || {};
          scaleMatrix.makeScale(dimensions.width || 1, dimensions.height || 1, dimensions.depth || 1);
          merged.setMatrixAt(index, mesh.matrixWorld.clone().multiply(scaleMatrix));
        });
        merged.name = `${batch.zone || 'scene'} static box instance batch`;
        merged.renderOrder = batch.meshes[0].renderOrder;
        merged.layers.mask = batch.meshes[0].layers.mask;
        merged.castShadow = batch.meshes[0].castShadow;
        merged.receiveShadow = batch.meshes[0].receiveShadow;
        merged.frustumCulled = false;
        merged.instanceMatrix.needsUpdate = true;
        if (batch.zone) {
          merged.userData.zone = batch.zone;
          merged.userData.objectId = `zone:${batch.zone}`;
          merged.userData.objectType = 'zone';
          merged.userData.objectName = zoneNames[batch.zone] || batch.zone;
        }
        const sources = new Set(batch.meshes);
        const wasPickable = batch.meshes.some(mesh => zonePickTargets.includes(mesh));
        batch.meshes.forEach(mesh => mesh.parent && mesh.parent.remove(mesh));
        for (let index = zonePickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(zonePickTargets[index])) zonePickTargets.splice(index, 1);
        }
        scene.add(merged);
        if (wasPickable && batch.zone) {
          zonePickTargets.push(merged);
          boxPickMeshCount += 1;
        }
        sourceCount += batch.meshes.length;
        boxMergedCount += 1;
      });

      scene.traverse(object => {
        if (!object.isMesh || object.isInstancedMesh || object.isSkinnedMesh || !object.geometry || !object.material) return;
        if (Array.isArray(object.material) || object.material.transparent || object.material.opacity < 0.999 || object.material.depthWrite === false) return;
        if (object.userData.workstationCutaway || object.userData.workstationCutawayBelowY !== undefined || object.userData.objectType === 'workstation') return;
        if (pickTargets.includes(object)) return;
        const attributes = Object.keys(object.geometry.attributes || {}).sort();
        if (attributes.join(',') !== 'normal,position,uv') return;
        let ancestor = object;
        while (ancestor && ancestor !== scene) {
          if (animatedObjects.has(ancestor) || ancestor.userData?.objectType === 'workstation') return;
          ancestor = ancestor.parent;
        }
        if (object.userData.objectType && object.userData.objectType !== 'zone') return;

        if (!object.parent) return;
        let zone = object.userData.zone || null;
        if (!zone) {
          let ancestor = object.parent;
          while (ancestor && ancestor !== scene && !zone) {
            zone = ancestor.userData.zone || null;
            ancestor = ancestor.parent;
          }
        }
        const key = [
          object.material.uuid, zone || '', object.renderOrder, object.layers.mask,
          object.castShadow ? 1 : 0, object.receiveShadow ? 1 : 0, object.frustumCulled ? 1 : 0
        ].join(':');
        let batch = batches.get(key);
        if (!batch) batches.set(key, batch = { material: object.material, zone, meshes: [] });
        batch.meshes.push(object);
        sourceCount += 1;
      });

      let mergedCount = boxMergedCount + transparentMergedCount;
      let pickMeshCount = boxPickMeshCount + transparentPickMeshCount;
      batches.forEach(batch => {
        if (batch.meshes.length < 2) return;
        const geometries = batch.meshes.map(mesh => {
          const geometry = mesh.geometry.clone();
          geometry.applyMatrix4(mesh.matrixWorld);
          return geometry;
        });
        const geometry = mergeBufferGeometries(geometries);
        const merged = new THREE.Mesh(geometry, batch.material);
        merged.name = `${batch.zone || 'scene'} static geometry batch`;
        merged.renderOrder = batch.meshes[0].renderOrder;
        merged.layers.mask = batch.meshes[0].layers.mask;
        merged.castShadow = batch.meshes[0].castShadow;
        merged.receiveShadow = batch.meshes[0].receiveShadow;
        merged.frustumCulled = batch.meshes[0].frustumCulled;
        if (batch.zone) {
          merged.userData.zone = batch.zone;
          merged.userData.objectId = `zone:${batch.zone}`;
          merged.userData.objectType = 'zone';
          merged.userData.objectName = zoneNames[batch.zone] || batch.zone;
        }
        const sources = new Set(batch.meshes);
        const wasPickable = batch.meshes.some(mesh => zonePickTargets.includes(mesh));
        batch.meshes.forEach(mesh => mesh.parent && mesh.parent.remove(mesh));
        for (let index = zonePickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(zonePickTargets[index])) zonePickTargets.splice(index, 1);
        }
        scene.add(merged);
        if (wasPickable && batch.zone) {
          zonePickTargets.push(merged);
          pickMeshCount += 1;
        }
        mergedCount += 1;
      });

      const activeGeometries = new Set();
      scene.traverse(object => { if (object.geometry) activeGeometries.add(object.geometry); });
      geometryCache.forEach((geometry, key) => {
        if (activeGeometries.has(geometry)) return;
        geometry.dispose();
        geometryCache.delete(key);
      });
      return { sourceMeshes: sourceCount, mergedMeshes: mergedCount, pickMeshes: pickMeshCount };
    }

    function batchStaticInstances() {
      const animatedObjects = new Set(animated.map(item => item.object).filter(Boolean));
      const batches = new Map();
      const geometryCandidates = new Set();
      const diagnostics = { candidates: 0, eligible: 0, skippedAnimated: 0, skippedTransparent: 0, skippedAttributes: 0, bakedInstanceColorMeshes: 0 };
      scene.updateMatrixWorld(true);

      scene.traverse(object => {
        if (!object.isInstancedMesh || !object.geometry || !object.material || !object.count || !object.parent) return;
        diagnostics.candidates += 1;
        if (animatedObjects.has(object)) { diagnostics.skippedAnimated += 1; return; }
        // Keep no-depth-write overlays separate because their order depends on
        // the individual object centers. Depth-writing accent meshes can be
        // combined safely with their matching zone/material batch.
        if (Array.isArray(object.material) || object.material.depthWrite === false) {
          diagnostics.skippedTransparent += 1;
          return;
        }
        const attributes = Object.keys(object.geometry.attributes || {}).sort().join(',');
        if (attributes !== 'normal,position,uv') { diagnostics.skippedAttributes += 1; return; }
        if (!object.instanceColor && object.material.vertexColors) { diagnostics.skippedAttributes += 1; return; }
        let zone = object.userData.zone || null;
        let ancestor = object.parent;
        while (ancestor && ancestor !== scene && !zone) {
          zone = ancestor.userData.zone || null;
          ancestor = ancestor.parent;
        }
        const targetParent = zoneGroups.get(zone) || object.parent;
        const cutaway = [
          object.userData.workstationCutaway ? 1 : 0,
          object.userData.workstationCutawayBelowY == null ? '' : object.userData.workstationCutawayBelowY
        ];
        const key = [
          targetParent.uuid, object.material.uuid, zone || '', object.renderOrder, object.layers.mask,
          object.visible ? 1 : 0, object.castShadow ? 1 : 0, object.receiveShadow ? 1 : 0,
          object.frustumCulled ? 1 : 0, object.instanceColor ? 1 : 0, ...cutaway
        ].join(':');
        let batch = batches.get(key);
        if (!batch) {
          batches.set(key, batch = { parent: targetParent, material: object.material, zone, hasInstanceColor: !!object.instanceColor, meshes: [] });
        }
        batch.meshes.push(object);
        diagnostics.eligible += 1;
      });

      let sourceMeshes = 0;
      let mergedMeshes = 0;
      let bakedInstances = 0;
      let pickMeshes = 0;
      batches.forEach(batch => {
        if (batch.meshes.length < 2) return;
        const source = batch.meshes[0];
        const toParent = batch.parent.matrixWorld.clone().invert();
        const geometries = [];
        batch.meshes.forEach(mesh => {
          mesh.updateMatrixWorld(true);
          const sourceToParent = toParent.clone().multiply(mesh.matrixWorld);
          const instanceMatrix = new THREE.Matrix4();
          for (let index = 0; index < mesh.count; index += 1) {
            mesh.getMatrixAt(index, instanceMatrix);
            const geometry = mesh.geometry.clone();
            geometry.applyMatrix4(sourceToParent.clone().multiply(instanceMatrix));
            if (batch.hasInstanceColor) {
              const colors = new Float32Array(geometry.attributes.position.count * 3);
              const red = mesh.instanceColor.getX(index);
              const green = mesh.instanceColor.getY(index);
              const blue = mesh.instanceColor.getZ(index);
              for (let vertex = 0; vertex < geometry.attributes.position.count; vertex += 1) {
                const offset = vertex * 3;
                colors[offset] = red;
                colors[offset + 1] = green;
                colors[offset + 2] = blue;
              }
              geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
            }
            geometries.push(geometry);
            bakedInstances += 1;
          }
          geometryCandidates.add(mesh.geometry);
        });
        let material = batch.material;
        if (batch.hasInstanceColor) {
          material = batch.material.clone();
          material.vertexColors = true;
          material.needsUpdate = true;
          diagnostics.bakedInstanceColorMeshes += batch.meshes.length;
          const group = zoneGroups.get(batch.zone);
          if (group && group.materials.indexOf(material) < 0) group.materials.push(material);
        }
        const merged = new THREE.Mesh(mergeBufferGeometries(geometries), material);
        merged.name = `${batch.zone || 'scene'} baked static instance batch`;
        merged.renderOrder = source.renderOrder;
        merged.layers.mask = source.layers.mask;
        merged.castShadow = source.castShadow;
        merged.receiveShadow = source.receiveShadow;
        merged.frustumCulled = source.frustumCulled;
        merged.visible = source.visible;
        Object.assign(merged.userData, source.userData);
        if (batch.zone) {
          merged.userData.zone = batch.zone;
          merged.userData.objectId = `zone:${batch.zone}`;
          merged.userData.objectType = 'zone';
          merged.userData.objectName = zoneNames[batch.zone] || batch.zone;
        }

        const sources = new Set(batch.meshes);
        const wasPickable = batch.meshes.some(mesh => zonePickTargets.includes(mesh));
        batch.meshes.forEach(mesh => mesh.parent && mesh.parent.remove(mesh));
        for (let index = zonePickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(zonePickTargets[index])) zonePickTargets.splice(index, 1);
        }
        for (let index = pickTargets.length - 1; index >= 0; index -= 1) {
          if (sources.has(pickTargets[index])) pickTargets.splice(index, 1);
        }
        batch.parent.add(merged);
        if (wasPickable && batch.zone) {
          zonePickTargets.push(merged);
          pickMeshes += 1;
        }
        sourceMeshes += batch.meshes.length;
        mergedMeshes += 1;
      });

      const activeGeometries = new Set();
      scene.traverse(object => { if (object.geometry) activeGeometries.add(object.geometry); });
      geometryCandidates.forEach(geometry => {
        if (!activeGeometries.has(geometry)) geometry.dispose();
      });
      geometryCache.forEach((geometry, key) => {
        if (activeGeometries.has(geometry)) return;
        geometry.dispose();
        geometryCache.delete(key);
      });
      return { sourceMeshes, mergedMeshes, bakedInstances, pickMeshes, diagnostics };
    }

    function setInitialCamera() {
      const preset = cameraPresets.panorama;
      controlsTarget.set(preset.target[0], preset.target[1], preset.target[2]);
      spherical.set(panoramaRadius(preset.radius), preset.phi, preset.theta);
      camera.position.setFromSpherical(spherical).add(controlsTarget);
      camera.lookAt(controlsTarget);
    }

    function panoramaRadius(baseRadius) {
      const aspect = Math.max(0.72, host.clientWidth / Math.max(1, host.clientHeight));
      // Keep the model large in the short, wide dashboard viewport while adding
      // only enough distance on ultrawide screens to retain the outer base.
      return clamp(baseRadius * Math.pow(Math.max(1, aspect / 2.55), 0.38), baseRadius, 39);
    }

    function desiredPixelRatio() {
      const deviceRatio = Math.min(window.devicePixelRatio || 1, 1);
      const width = host.clientWidth;
      const panoramaScale = width >= 1000 ? 0.82 : width >= 760 ? 0.86 : 0.92;
      const inspectionScale = spherical.radius < 18 ? Math.max(panoramaScale, 0.94) : panoramaScale;
      return deviceRatio * inspectionScale;
    }

    function resize() {
      if (destroyed) return;
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(1, host.clientHeight);
      renderer.setPixelRatio(desiredPixelRatio());
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    function bindControls() {
      canvas.addEventListener('contextmenu', event => event.preventDefault());
      canvas.addEventListener('pointerdown', event => {
        cameraTransition = false;
        pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (canvas.setPointerCapture) canvas.setPointerCapture(event.pointerId);
        if (pointers.size === 1) {
          const hit = pick(event.clientX, event.clientY);
          dragging = {
            x: event.clientX,
            y: event.clientY,
            moved: false,
            pan: event.button === 2 || event.shiftKey,
            object: hit && hit.zone === 'global' ? globeGroupRef : null,
            hit
          };
        }
        if (pointers.size === 2) pinchDistance = pointerDistance();
        canvas.focus({ preventScroll: true });
      });
      canvas.addEventListener('pointermove', event => {
        const previous = pointers.get(event.pointerId);
        if (previous && dragging) {
          const dx = event.clientX - previous.x;
          const dy = event.clientY - previous.y;
          if (Math.abs(dx) + Math.abs(dy) > 2) dragging.moved = true;
          if (pointers.size > 1) {
            pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
            const distance = pointerDistance();
            if (pinchDistance > 0 && distance > 0) spherical.radius = clamp(spherical.radius * pinchDistance / distance, 6.5, 54);
            pinchDistance = distance;
          } else if (dragging.object) {
            dragging.object.rotation.y -= dx * 0.009;
            dragging.object.rotation.x = clamp(dragging.object.rotation.x + dy * 0.006, -0.72, 0.72);
            dragging.x = event.clientX;
            dragging.y = event.clientY;
          } else if (dragging.moved) {
            if (dragging.pan) panCamera(dx, dy);
            else {
              spherical.theta -= dx * 0.006;
              spherical.phi = clamp(spherical.phi + dy * 0.005, 0.2, 1.49);
            }
            dragging.x = event.clientX;
            dragging.y = event.clientY;
          }
          pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
          return;
        }
        const hit = pick(event.clientX, event.clientY);
        setHover(hit ? hit.zone : null, event.offsetX, event.offsetY, hit && hit.item);
      });
      const endPointer = event => {
        pointers.delete(event.pointerId);
        if (pointers.size < 2) pinchDistance = 0;
        if (pointers.size === 0) {
          if (dragging && !dragging.moved) {
            const hit = dragging.hit || pick(event.clientX, event.clientY);
            if (hit && hit.zone) {
              if (hit.item) focusWorkstation(hit.item);
              else focus(hit.zone);
            }
          }
          dragging = null;
        }
      };
      canvas.addEventListener('pointerup', endPointer);
      canvas.addEventListener('pointercancel', endPointer);
      canvas.addEventListener('wheel', event => {
        event.preventDefault();
        cameraTransition = false;
        spherical.radius = clamp(spherical.radius * Math.exp(event.deltaY * 0.001), 6.5, 54);
      }, { passive: false });
      canvas.addEventListener('dblclick', event => {
        const hit = pick(event.clientX, event.clientY);
        if (hit && hit.zone) {
          if (hit.item) focusWorkstation(hit.item);
          else focus(hit.zone);
        }
      });
      canvas.addEventListener('pointerleave', () => { if (!dragging) setHover(null); });
      canvas.addEventListener('keydown', event => {
        let handled = true;
        if (event.key === 'ArrowLeft') spherical.theta += 0.12;
        else if (event.key === 'ArrowRight') spherical.theta -= 0.12;
        else if (event.key === 'ArrowUp') spherical.phi = clamp(spherical.phi - 0.08, 0.2, 1.49);
        else if (event.key === 'ArrowDown') spherical.phi = clamp(spherical.phi + 0.08, 0.2, 1.49);
        else if (event.key === '+' || event.key === '=') spherical.radius = clamp(spherical.radius * 0.9, 6.5, 54);
        else if (event.key === '-') spherical.radius = clamp(spherical.radius * 1.1, 6.5, 54);
        else if (event.key.toLowerCase() === 'r' || event.key === 'Home') reset();
        else handled = false;
        if (handled) { event.preventDefault(); cameraTransition = false; }
      });
    }

    function pointerDistance() {
      const values = Array.from(pointers.values());
      if (values.length < 2) return 0;
      return Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
    }

    function panCamera(dx, dy) {
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
      const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
      const scale = spherical.radius * 0.00145;
      controlsTarget.addScaledVector(right, -dx * scale).addScaledVector(up, dy * scale);
      targetLookAt.copy(controlsTarget);
    }

    function pick(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return null;
      pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const inspectionActive = inspectionZone && spherical.radius < 18 ? inspectionZone : null;
      const intersections = raycaster.intersectObjects(pickTargets.filter(hasVisibleAncestors), false);
      for (let i = 0; i < intersections.length; i += 1) {
        const hit = intersections[i];
        const data = hit.object.userData;
        if (data.zone && (!inspectionActive || isRelatedInspectionZone(data.zone, inspectionActive)) && (data.objectType === 'workstation' || data.objectType === 'landmark')) {
          return { zone: data.zone, object: hit.object, distance: hit.distance, item: data };
        }
      }
      const structureHits = raycaster.intersectObjects(zonePickTargets.filter(hasVisibleAncestors), false);
      const structureHit = structureHits.find(hit => hit.object.userData.zone && hit.object.userData.objectType === 'zone');
      const globalOrigin = zoneOrigins.live;
      const allowGlobalLandmark = !inspectionActive || isRelatedInspectionZone('global', inspectionActive);
      const globeHit = allowGlobalLandmark && raycaster.ray.intersectSphere(new THREE.Sphere(new THREE.Vector3(globalOrigin[0], globalOrigin[1] + 3.55, globalOrigin[2]), 1.85), new THREE.Vector3());
      if (globeHit) {
        const distance = raycaster.ray.origin.distanceTo(globeHit);
        if (!structureHit || distance < structureHit.distance) return { zone: 'global', object: globeGroupRef, distance, item: null };
      }
      if (structureHit) {
        const zone = structureHit.object.userData.zone;
        return { zone, object: zoneGroups.get(zone), distance: structureHit.distance, item: null };
      }
      const ground = raycaster.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 1.08), new THREE.Vector3());
      if (!ground) return null;
      let best = null;
      let bestDistance = Infinity;
      zonePickAreas.forEach(area => {
        if (inspectionActive && !isRelatedInspectionZone(area.zone, inspectionActive)) return;
        const distanceFromZone = Math.hypot(ground.x - area.x, ground.z - area.z);
        if (distanceFromZone <= area.radius) {
          const distance = raycaster.ray.origin.distanceTo(ground);
          if (distance < bestDistance) {
            bestDistance = distance;
            best = { zone: area.zone, object: zoneGroups.get(area.zone), distance, item: null };
          }
        }
      });
      return best;
    }

    function isVisibleInScene(object) {
      let current = object;
      while (current && current !== scene) {
        if (!current.visible) return false;
        current = current.parent;
      }
      return current === scene;
    }

    function hasVisibleAncestors(object) {
      let current = object && object.parent;
      while (current && current !== scene) {
        if (!current.visible) return false;
        current = current.parent;
      }
      return current === scene;
    }

    function isRelatedInspectionZone(zone, focusedZone) {
      return zone === focusedZone || ((zone === 'live' || zone === 'global') && (focusedZone === 'live' || focusedZone === 'global'));
    }

    function setHover(zone, x, y, item) {
      if (hoveredZone !== zone) {
        const previous = hoveredZone;
        hoveredZone = zone;
        refreshGlow(previous);
        refreshGlow(hoveredZone);
      }
      hoveredObjectId = item && item.objectType === 'workstation' ? item.objectId : null;
      setWorkstationHighlight(hoveredObjectId || (workstations.has(selectedObjectId) ? selectedObjectId : null));
      canvas.style.cursor = zone ? 'pointer' : dragging ? (dragging.pan ? 'move' : 'grabbing') : 'grab';
      options && options.onHover && options.onHover(zone, x, y, item || null);
    }

    function refreshGlow(zone) {
      if (!zone) return;
      const group = zoneGroups.get(zone);
      if (!group) return;
      const factor = selectedZone === zone ? 1.26 : hoveredZone === zone ? 1.12 : 1;
      group.materials.forEach(material => {
        if (!material || material.emissiveIntensity === undefined) return;
        if (material.userData.baseEmissiveIntensity === undefined) material.userData.baseEmissiveIntensity = material.emissiveIntensity;
        material.emissiveIntensity = material.userData.baseEmissiveIntensity * factor;
      });
    }

    function setWorkstationHighlight(objectId) {
      if (highlightedWorkstationId === objectId) return;
      const previous = workstations.get(highlightedWorkstationId);
      if (previous) previous.highlight.visible = false;
      const next = workstations.get(objectId);
      if (next) next.highlight.visible = true;
      highlightedWorkstationId = next ? objectId : null;
    }

    function setWorkstationCutaway(zone, active, item) {
      const group = zoneGroups.get(zone);
      if (!group) return;
      group.traverse(object => {
        if (!object.userData.workstationCutaway && object.userData.workstationCutawayBelowY === undefined) return;
        if (object.userData.workstationCutawayBaseVisible === undefined) object.userData.workstationCutawayBaseVisible = object.visible;
        const lowerFloorCutaway = object.userData.workstationCutawayBelowY === undefined || (item?.worldPosition && item.worldPosition[1] < object.userData.workstationCutawayBelowY);
        object.visible = active && lowerFloorCutaway ? false : object.userData.workstationCutawayBaseVisible;
      });
      group.materials.forEach(material => {
        if (!material || material.userData.baseOpacity === undefined) return;
        material.opacity = active ? material.userData.focusOpacity : material.userData.baseOpacity;
        material.needsUpdate = true;
      });
    }

    function setZoneInspectionCutaway(zone, active) {
      const group = zoneGroups.get(zone);
      if (!group) return;
      group.traverse(object => {
        if (!object.userData.zoneInspectionCutaway || object.userData.hologram || object.userData.holoAtlas) return;
        if (object.userData.inspectionCutawayBaseVisible === undefined) object.userData.inspectionCutawayBaseVisible = object.visible;
        object.visible = active ? false : object.userData.inspectionCutawayBaseVisible;
      });
    }

    function select(zone, item) {
      if (!zoneGroups.has(zone)) return;
      const previous = selectedZone;
      selectedZone = zone;
      const object = item || { objectId: `zone:${zone}`, objectType: 'zone', zone, name: zoneNames[zone] || zone };
      const nextCutawayZone = object.objectType === 'workstation' ? zone : null;
      if (cutawayZone && cutawayZone !== nextCutawayZone) setWorkstationCutaway(cutawayZone, false);
      if (nextCutawayZone) setWorkstationCutaway(nextCutawayZone, true, object);
      cutawayZone = nextCutawayZone;
      selectedObjectId = object.objectId;
      setWorkstationHighlight(object.objectType === 'workstation' ? object.objectId : (workstations.has(hoveredObjectId) ? hoveredObjectId : null));
      refreshGlow(previous);
      refreshGlow(zone);
      options && options.onZoneSelect && options.onZoneSelect(zone, object);
    }

    function focusWorkstation(item) {
      if (!item || !item.worldPosition) return;
      const isWorkstation = item.objectType === 'workstation';
      const isAiCore = item.objectId === 'ai-core';
      if (inspectionCutawayZone) setZoneInspectionCutaway(inspectionCutawayZone, false);
      inspectionCutawayZone = null;
      inspectionZone = item.zone;
      const focusTarget = new THREE.Vector3(
        item.worldPosition[0],
        isAiCore ? 5.45 : item.worldPosition[1] + (isWorkstation ? 1.15 : 0),
        item.worldPosition[2]
      );
      // Frame desks with some room context, but center landmarks on their own
      // world position so tall objects such as the AI Core are not pushed down.
      const viewAngle = Number.isFinite(item.cameraAngle) ? item.cameraAngle : 0;
      const radius = isWorkstation ? 6.9 : item.objectId === 'traffic-globe' ? 8.2 : isAiCore ? 15 : 7.4;
      const theta = viewAngle + (isWorkstation ? 0.32 : 0.18);
      const phi = isWorkstation ? 1.16 : 1.24;
      const offset = new THREE.Vector3().setFromSpherical(new THREE.Spherical(radius, phi, theta));
      targetPosition.copy(focusTarget).add(offset);
      targetLookAt.copy(focusTarget);
      cameraTransition = !reducedMotion;
      if (reducedMotion) {
        controlsTarget.copy(targetLookAt);
        camera.position.copy(targetPosition);
        camera.lookAt(controlsTarget);
        spherical.setFromVector3(new THREE.Vector3().subVectors(camera.position, controlsTarget));
      }
      select(item.zone, item);
    }

    function focus(name) {
      const key = name === 'panorama' || name === '3d' ? 'panorama' : name;
      const preset = cameraPresets[key] || cameraPresets.panorama;
      inspectionZone = key === 'panorama' ? null : (preset.zone || 'command');
      const nextTarget = new THREE.Vector3(preset.target[0], preset.target[1], preset.target[2]);
      const radius = key === 'panorama' ? panoramaRadius(preset.radius) : preset.radius;
      const nextOffset = new THREE.Vector3().setFromSpherical(new THREE.Spherical(radius, preset.phi, preset.theta));
      targetPosition.copy(nextTarget).add(nextOffset);
      targetLookAt.copy(nextTarget);
      cameraTransition = !reducedMotion;
      if (reducedMotion) {
        controlsTarget.copy(targetLookAt);
        camera.position.copy(targetPosition);
        camera.lookAt(controlsTarget);
        spherical.setFromVector3(new THREE.Vector3().subVectors(camera.position, controlsTarget));
      }
      const zone = preset.zone || 'command';
      select(zone);
      const nextCutawayZone = key === 'panorama' ? null : zone;
      if (inspectionCutawayZone && inspectionCutawayZone !== nextCutawayZone) setZoneInspectionCutaway(inspectionCutawayZone, false);
      inspectionCutawayZone = nextCutawayZone;
      if (inspectionCutawayZone && !workstations.has(selectedObjectId)) setZoneInspectionCutaway(inspectionCutawayZone, true);
    }

    function reset() { focus('panorama'); }

    function updateData(data) {
      const agentsMetric = data && data.metrics && data.metrics.active_agents;
      const agents = zoneGroups.get('agents');
      if (!agents) return;
      const hasVerifiedAgents = agentsMetric && agentsMetric.status === 'observed';
      agents.userData.dataStatus = hasVerifiedAgents ? 'observed' : 'unknown';
      agents.userData.activeCount = hasVerifiedAgents ? Number(agentsMetric.value) : null;
      // Geometry remains a design model. No animated person or activity is invented from missing telemetry.
    }

    function render() {
      if (destroyed) return;
      if (document.hidden) { frame = 0; return; }
      frame = requestAnimationFrame(render);
      if (!canvas.clientWidth || !canvas.clientHeight) return;
      const delta = Math.min(clock.getDelta(), 0.045);
      if (cameraTransition) {
        const amount = 1 - Math.exp(-delta * 4.0);
        camera.position.lerp(targetPosition, amount);
        controlsTarget.lerp(targetLookAt, amount);
        camera.lookAt(controlsTarget);
        if (camera.position.distanceTo(targetPosition) < 0.022 && controlsTarget.distanceTo(targetLookAt) < 0.022) cameraTransition = false;
        spherical.setFromVector3(new THREE.Vector3().subVectors(camera.position, controlsTarget));
      } else {
        camera.position.setFromSpherical(spherical).add(controlsTarget);
        camera.lookAt(controlsTarget);
      }
      const desiredRatio = desiredPixelRatio();
      if (Math.abs(renderer.getPixelRatio() - desiredRatio) > 0.01) {
        renderer.setPixelRatio(desiredRatio);
        renderer.setSize(host.clientWidth, host.clientHeight, false);
      }
      const elapsed = clock.elapsedTime;
      // Keep a real 3D city horizon behind focused views instead of an empty sky.
      const showBackdropCity = spherical.radius >= 18;
      backdropCityObjects.forEach(object => {
        if (object.visible !== showBackdropCity) object.visible = showBackdropCity;
      });
      if (duskSunObject) duskSunObject.visible = spherical.radius >= 18;
      const showCommandOrbits = spherical.radius >= 26;
      commandOrbitMeshes.forEach(object => {
        if (object.visible !== showCommandOrbits) object.visible = showCommandOrbits;
      });
      const nextInspectionZone = inspectionZone && spherical.radius < 18 ? inspectionZone : null;
      if (visibleInspectionZone !== nextInspectionZone) {
        zoneGroups.forEach((group, zone) => {
          const visible = !nextInspectionZone || isRelatedInspectionZone(zone, nextInspectionZone);
          if (group.visible !== visible) group.visible = visible;
        });
        visibleInspectionZone = nextInspectionZone;
        renderer.shadowMap.needsUpdate = true;
      }
      if (cutawayZone && spherical.radius >= 18) {
        setWorkstationCutaway(cutawayZone, false);
        cutawayZone = null;
      }
      const nextInspectionCutawayZone = nextInspectionZone && !workstations.has(selectedObjectId) ? nextInspectionZone : null;
      if (inspectionCutawayZone !== nextInspectionCutawayZone) {
        if (inspectionCutawayZone) setZoneInspectionCutaway(inspectionCutawayZone, false);
        inspectionCutawayZone = nextInspectionCutawayZone;
        if (inspectionCutawayZone) setZoneInspectionCutaway(inspectionCutawayZone, true);
        renderer.shadowMap.needsUpdate = true;
      }
      const needsDetailShadows = spherical.radius < 18;
      if (renderer.shadowMap.enabled !== needsDetailShadows) {
        renderer.shadowMap.enabled = needsDetailShadows;
        renderer.shadowMap.needsUpdate = true;
      }
      if (!reducedMotion) {
        animated.forEach(item => {
          if (item.kind === 'ring') item.object.rotation.z += delta * item.speed;
          else if (item.kind === 'orbit-ring') item.object.rotation.y += delta * item.speed;
          else if (item.kind === 'brain') { item.object.rotation.y += delta * 0.075; item.object.position.y = 8.42 + Math.sin(elapsed * 0.8) * 0.08; }
          else if (item.kind === 'globe') item.object.rotation.y += delta * item.speed;
          else if (item.kind === 'beacon') item.object.scale.setScalar(0.78 + (Math.sin(elapsed * 2.2 + item.phase) + 1) * 0.16);
          else if (item.kind === 'energy-pulses') {
            item.tracks.forEach((track, index) => {
              const progress = ((elapsed * 0.12 * track.direction + track.phase) % 1 + 1) % 1;
              item.transform.position.copy(track.curve.getPoint(progress));
              item.transform.updateMatrix();
              item.object.setMatrixAt(index, item.transform.matrix);
            });
            item.object.instanceMatrix.needsUpdate = true;
          }
        });
      }
      try {
        renderer.info.reset();
        renderer.render(scene, camera);
        if (!hasRenderedFrame) {
          hasRenderedFrame = true;
          const draw = renderer.info && renderer.info.render;
          options && options.onStatus && options.onStatus(draw && draw.calls > 0 && draw.triangles > 0 ? 'ready' : 'error');
        }
      } catch (error) {
        if (!renderFailed) {
          renderFailed = true;
          options && options.onStatus && options.onStatus('error');
          console.error('AUTOProfit 3D command center render failed.', error);
        }
        cancelAnimationFrame(frame);
        frame = 0;
      }
    }

    function onVisibility() {
      if (!document.hidden) {
        resize();
        if (!frame && !destroyed) frame = requestAnimationFrame(render);
      }
    }

    return {
      focus,
      reset,
      updateData,
      getDebugState() {
        return {
          camera: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
          target: { x: controlsTarget.x, y: controlsTarget.y, z: controlsTarget.z },
          cameraRadius: spherical.radius,
          visibleCommandOrbits: commandOrbitMeshes.filter(object => object.visible).length,
          selectedZone,
          selectedObjectId,
          inspectionZone,
          inspectionCutawayZone,
          visibleZones: Array.from(zoneGroups.entries()).filter(([, group]) => isVisibleInScene(group)).map(([zone]) => zone),
          highlightedWorkstationId,
          zones: Array.from(zoneGroups.keys()),
          pickableMeshes: pickTargets.length,
          zonePickMeshes: zonePickTargets.length,
          workstations: Array.from(workstations.values(), entry => {
            const meta = entry.metadata;
            const point = new THREE.Vector3(meta.worldPosition[0], meta.worldPosition[1] + 0.72, meta.worldPosition[2] + 0.35).project(camera);
            const rect = canvas.getBoundingClientRect();
            return {
              objectId: meta.objectId,
              name: meta.name,
              zone: meta.zone,
              worldPosition: meta.worldPosition.slice(),
              screenPosition: { x: rect.left + (point.x + 1) * rect.width / 2, y: rect.top + (1 - point.y) * rect.height / 2, inView: point.z >= -1 && point.z <= 1 },
              assignmentStatus: meta.assignmentStatus
            };
          }),
          landmarks: Array.from(landmarks.values(), entry => {
            const meta = entry.metadata;
            const point = entry.object.getWorldPosition(new THREE.Vector3()).project(camera);
            const rect = canvas.getBoundingClientRect();
            return {
              objectId: meta.objectId,
              name: meta.name,
              zone: meta.zone,
              worldPosition: meta.worldPosition.slice(),
              screenPosition: { x: rect.left + (point.x + 1) * rect.width / 2, y: rect.top + (1 - point.y) * rect.height / 2, inView: point.z >= -1 && point.z <= 1 },
              assignmentStatus: meta.assignmentStatus
            };
          }),
          render: renderer.info && renderer.info.render ? {
            calls: renderer.info.render.calls,
            triangles: renderer.info.render.triangles,
            hasRenderedFrame
          } : { hasRenderedFrame },
          staticBatching: staticBatchStats,
          memory: renderer.info && renderer.info.memory ? {
            geometries: renderer.info.memory.geometries,
            textures: renderer.info.memory.textures
          } : null,
          renderer: renderer.isWebGLRenderer,
          projection: camera.isPerspectiveCamera
        };
      },
      destroy() {
        if (destroyed) return;
        destroyed = true;
        cancelAnimationFrame(frame);
        resizeObserver && resizeObserver.disconnect();
        window.removeEventListener('resize', resize);
        document.removeEventListener('visibilitychange', onVisibility);
        scene.traverse(node => {
          if (node.geometry && node.geometry.dispose) node.geometry.dispose();
          if (Array.isArray(node.material)) node.material.forEach(material => material && material.dispose && material.dispose());
          else if (node.material && node.material.dispose) node.material.dispose();
          if (node.material && node.material.map && node.material.map.dispose) node.material.map.dispose();
        });
        renderer.dispose();
      }
    };

    function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
  }

  window.AutoProfitCommandCenter = { create };
})();
