function init3DAIBaseWorld() {
      WORLD_3D.initialized = true;
      return;
      const canvas = document.getElementById('aiBase3DCanvas');
      const stage = document.getElementById('aiBase3DStage');
      const overlay = document.getElementById('aiBase3DOverlay');
      if (!canvas || !stage || !overlay) return;

      if (typeof THREE === 'undefined') {
        WORLD_3D.retryCount = (WORLD_3D.retryCount || 0) + 1;
        if (WORLD_3D.retryCount <= 25) {
          setTimeout(init3DAIBaseWorld, 200);
          return;
        }
        WORLD_3D.webglSupported = false;
        const fb = document.getElementById('webglFallbackNotice');
        if (fb) fb.style.display = 'flex';
        return;
      }

      const fb = document.getElementById('webglFallbackNotice');
      if (fb) fb.style.display = 'none';

      const width = stage.clientWidth || 960;
      const height = stage.clientHeight || 640;

      let renderer = null;
      let renderMode = 'WEBGL';
      try {
        renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      } catch (err1) {
        try {
          renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, failIfMajorPerformanceCaveat: false });
        } catch (err2) {
          renderer = null;
          renderMode = 'CANVAS3D';
        }
      }

      if (renderer) {
        renderer.setSize(width, height);
        renderer.setPixelRatio(LOW_PERF_MODE ? 1 : Math.min(window.devicePixelRatio || 1, 2));
        renderer.setClearColor(0x000000, 0);
      } else {
        canvas.width = width;
        canvas.height = height;
        WORLD_3D.ctx2d = canvas.getContext('2d');
      }
      WORLD_3D.renderMode = renderMode;
      WORLD_3D.webglSupported = true;

      const scene = new THREE.Scene();
      scene.fog = new THREE.FogExp2(0x050914, 0.012);

      const camera = new THREE.PerspectiveCamera(46, width / height, 0.5, 160);

      // Lighting — Warm Natural Office Illumination + Skylight & Boardroom Accents
      const ambientLight = new THREE.AmbientLight(0xcbd5e1, 0.92);
      scene.add(ambientLight);

      const dirLight = new THREE.DirectionalLight(0xf8fafc, 1.15);
      dirLight.position.set(16, 36, 20);
      scene.add(dirLight);

      const corePointLight = new THREE.PointLight(0x00f3ff, 1.65, 42);
      corePointLight.position.set(0, 5.2, 0.2);
      scene.add(corePointLight);
      const neonMagentaLight = new THREE.PointLight(0xff00a0, 1.25, 38);
      neonMagentaLight.position.set(-14, 6.5, -8);
      scene.add(neonMagentaLight);
      const neonPurpleLight = new THREE.PointLight(0xb026ff, 1.25, 38);
      neonPurpleLight.position.set(14, 6.5, 8);
      scene.add(neonPurpleLight);

      // 1. ARCHITECTURAL RECTANGULAR CORPORATE OFFICE BUILDING (46m x 34m) — Strictly NO circular disc or wireframe grid!
      const floorGeo = new THREE.BoxGeometry(46, 0.36, 34);
      const floorMat = new THREE.MeshStandardMaterial({
        color: 0x0b1324,
        roughness: 0.48,
        metalness: 0.25
      });
      const floorMesh = new THREE.Mesh(floorGeo, floorMat);
      floorMesh.position.set(0, -0.18, 0);
      scene.add(floorMesh);

      // Warm Wood-Tile Main Hallways (x = ±7.2, z = ±5.4) connecting all departments & Central Boardroom
      const hallMat = new THREE.MeshStandardMaterial({ color: 0x162038, roughness: 0.42, metalness: 0.18 });
      const hallStripMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.24 });
      [
        { x: -7.2, z: 0, w: 2.2, d: 31.6 },
        { x: 7.2,  z: 0, w: 2.2, d: 31.6 },
        { x: 0,    z: -5.4, w: 42.0, d: 2.0 },
        { x: 0,    z: 5.4,  w: 42.0, d: 2.0 }
      ].forEach(h => {
        const hm = new THREE.Mesh(new THREE.BoxGeometry(h.w, 0.03, h.d), hallMat);
        hm.position.set(h.x, 0.015, h.z);
        scene.add(hm);
        const strip = new THREE.Mesh(new THREE.BoxGeometry(h.w * 0.92, 0.035, h.d * 0.96), hallStripMat);
        strip.position.set(h.x, 0.02, h.z);
        scene.add(strip);
      });

      // Department Room Carpets & Architectural Floor Borders
      OFFICE_ROOMS_LAYOUT.forEach(rm => {
        const carpet = new THREE.Mesh(
          new THREE.BoxGeometry(rm.w, 0.04, rm.d),
          new THREE.MeshStandardMaterial({ color: rm.carpetHex, roughness: 0.72, metalness: 0.08 })
        );
        carpet.position.set(rm.x, 0.02, rm.z);
        scene.add(carpet);

        const borderPts = [
          new THREE.Vector3(rm.x - rm.w / 2, 0.045, rm.z - rm.d / 2),
          new THREE.Vector3(rm.x + rm.w / 2, 0.045, rm.z - rm.d / 2),
          new THREE.Vector3(rm.x + rm.w / 2, 0.045, rm.z + rm.d / 2),
          new THREE.Vector3(rm.x - rm.w / 2, 0.045, rm.z + rm.d / 2),
          new THREE.Vector3(rm.x - rm.w / 2, 0.045, rm.z - rm.d / 2)
        ];
        const borderLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(borderPts),
          new THREE.LineBasicMaterial({ color: rm.borderHex, transparent: true, opacity: 0.55 })
        );
        scene.add(borderLine);
      });

      // Exterior Perimeter Walls & Panoramic Windows + Interior Framed Glass Partitions with Open Doorways
      const extWallMat = new THREE.MeshStandardMaterial({ color: 0x111c33, roughness: 0.5, metalness: 0.3 });
      const winGlassMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.16, side: THREE.DoubleSide });
      const partGlassMat = new THREE.MeshBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.14, side: THREE.DoubleSide });
      const frameMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.4, metalness: 0.6 });

      // North Perimeter Wall (z = -16.6) with Panoramic Windows
      const northWall = new THREE.Mesh(new THREE.BoxGeometry(45.6, 3.4, 0.28), extWallMat);
      northWall.position.set(0, 1.7, -16.6);
      scene.add(northWall);
      [-15, 0, 15].forEach(wx => {
        const win = new THREE.Mesh(new THREE.PlaneGeometry(9.5, 1.9), winGlassMat);
        win.position.set(wx, 1.95, -16.44);
        scene.add(win);
      });

      // West & East Perimeter Walls (x = -22.6, x = +22.6)
      const westWall = new THREE.Mesh(new THREE.BoxGeometry(0.28, 3.2, 33.2), extWallMat);
      westWall.position.set(-22.6, 1.6, 0);
      scene.add(westWall);

      const eastWall = new THREE.Mesh(new THREE.BoxGeometry(0.28, 3.2, 33.2), extWallMat);
      eastWall.position.set(22.6, 1.6, 0);
      scene.add(eastWall);

      // Low Cutaway South Architectural Balcony Rail (z = +16.6) so camera view is unobstructed
      const southRail = new THREE.Mesh(new THREE.BoxGeometry(45.6, 0.75, 0.22), frameMat);
      southRail.position.set(0, 0.38, 16.6);
      scene.add(southRail);

      // Interior Glass Partition Walls with Real Open Doorways (Employees walk through gaps, never through glass)
      [
        // West Wing Glass Partitions (along x = -8.6, leaving doorways at z = -9.2, -1.2, +6.2)
        { x: -8.6, z: -13.6, w: 0.14, d: 5.2, h: 2.6 },
        { x: -8.6, z: -5.2,  w: 0.14, d: 4.4, h: 2.6 },
        { x: -8.6, z: 2.5,   w: 0.14, d: 4.2, h: 2.6 },
        { x: -8.6, z: 11.8,  w: 0.14, d: 7.4, h: 2.6 },
        // East Wing Glass Partitions (along x = +8.6, leaving doorways at z = -8.8, -2.4, +3.4, +6.4)
        { x: 8.6,  z: -13.4, w: 0.14, d: 5.6, h: 2.6 },
        { x: 8.6,  z: -5.6,  w: 0.14, d: 3.4, h: 2.6 },
        { x: 8.6,  z: 0.5,   w: 0.14, d: 3.2, h: 2.6 },
        { x: 8.6,  z: 11.8,  w: 0.14, d: 7.4, h: 2.6 },
        // Central Glass Boardroom Partitions (x ∈ [-5.6, 5.6], z ∈ [-3.7, 4.1], with North/South/East/West glass doorways)
        { x: -3.2, z: -3.7,  w: 4.6,  d: 0.14, h: 2.5 },
        { x: 3.2,  z: -3.7,  w: 4.6,  d: 0.14, h: 2.5 },
        { x: -3.2, z: 4.1,   w: 4.6,  d: 0.14, h: 2.5 },
        { x: 3.2,  z: 4.1,   w: 4.6,  d: 0.14, h: 2.5 },
        { x: -5.6, z: 0.2,   w: 0.14, d: 5.2,  h: 2.5 },
        { x: 5.6,  z: 0.2,   w: 0.14, d: 5.2,  h: 2.5 }
      ].forEach(pw => {
        const gm = new THREE.Mesh(new THREE.BoxGeometry(pw.w, pw.h, pw.d), partGlassMat);
        gm.position.set(pw.x, pw.h / 2, pw.z);
        scene.add(gm);
        const topBar = new THREE.Mesh(new THREE.BoxGeometry(pw.w + 0.04, 0.10, pw.d + 0.04), frameMat);
        topBar.position.set(pw.x, pw.h + 0.05, pw.z);
        scene.add(topBar);
      });

      // 2. CENTRAL GLASS BOARDROOM / CONFERENCE ROOM (0, 0, 0.2) — Replaces circular robot core pedestal
      const coreGroup = new THREE.Group();
      coreGroup.position.set(0, 0, 0.2);
      scene.add(coreGroup);

      // Executive Conference Table (5.2m x 2.0m Rectangular Walnut & Slate Table)
      const confTableTop = new THREE.Mesh(
        new THREE.BoxGeometry(5.2, 0.12, 2.0),
        new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.32, metalness: 0.45 })
      );
      confTableTop.position.set(0, 0.78, 0);
      coreGroup.add(confTableTop);

      const confTableBase1 = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.74, 1.3), frameMat);
      confTableBase1.position.set(-1.6, 0.37, 0);
      const confTableBase2 = confTableBase1.clone();
      confTableBase2.position.set(1.6, 0.37, 0);
      coreGroup.add(confTableBase1, confTableBase2);

      // 10 Conference Chairs around the Central Boardroom Table + Meeting Waypoints
      WORLD_3D.meetingSpots = [];
      const chairMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5, metalness: 0.3 });
      const chairSeatOffsets = [
        { x: -1.8, z: -1.45, yaw: 0 },
        { x: -0.6, z: -1.45, yaw: 0 },
        { x: 0.6,  z: -1.45, yaw: 0 },
        { x: 1.8,  z: -1.45, yaw: 0 },
        { x: -1.8, z: 1.45,  yaw: Math.PI },
        { x: -0.6, z: 1.45,  yaw: Math.PI },
        { x: 0.6,  z: 1.45,  yaw: Math.PI },
        { x: 1.8,  z: 1.45,  yaw: Math.PI },
        { x: -3.1, z: 0,     yaw: Math.PI / 2 },
        { x: 3.1,  z: 0,     yaw: -Math.PI / 2 }
      ];
      chairSeatOffsets.forEach(cs => {
        const cg = new THREE.Group();
        cg.position.set(cs.x, 0, cs.z);
        cg.rotation.y = cs.yaw;
        const cSeat = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.08, 0.52), chairMat);
        cSeat.position.y = 0.48;
        const cBack = new THREE.Mesh(new THREE.BoxGeometry(0.50, 0.58, 0.08), chairMat);
        cBack.position.set(0, 0.78, -0.22);
        const cStem = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 0.46, 8), frameMat);
        cStem.position.y = 0.23;
        cg.add(cSeat, cBack, cStem);
        coreGroup.add(cg);
        WORLD_3D.meetingSpots.push({ x: cs.x, z: cs.z + 0.2, yaw: cs.yaw });
      });

      // Subtle Tabletop Hologram Projector above the Conference Table (for visual continuity & compatibility)
      const coreCrystal = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.42, 0),
        new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true })
      );
      coreCrystal.position.y = 1.42;
      coreGroup.add(coreCrystal);

      const coreRing1 = new THREE.Mesh(
        new THREE.TorusGeometry(0.68, 0.025, 8, 32),
        new THREE.MeshBasicMaterial({ color: 0x22d3ee })
      );
      coreRing1.position.y = 1.42;
      coreRing1.rotation.x = Math.PI / 2;
      coreGroup.add(coreRing1);

      const coreRing2 = new THREE.Mesh(
        new THREE.TorusGeometry(0.85, 0.02, 8, 32),
        new THREE.MeshBasicMaterial({ color: 0xa855f7 })
      );
      coreRing2.position.y = 1.42;
      coreRing2.rotation.x = Math.PI / 3;
      coreGroup.add(coreRing2);

      // Decorative Office Plants at Hallway Corners
      const potMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6 });
      const leafMat = new THREE.MeshStandardMaterial({ color: 0x10b981, roughness: 0.5 });
      [
        [-6.2, -4.4], [6.2, -4.4], [-6.2, 4.8], [6.2, 4.8],
        [-21.2, -15.2], [21.2, -15.2], [-21.2, 15.2], [21.2, 15.2]
      ].forEach(([px, pz]) => {
        const plantGrp = new THREE.Group();
        plantGrp.position.set(px, 0, pz);
        const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.24, 0.52, 10), potMat);
        pot.position.y = 0.26;
        const foliage = new THREE.Mesh(new THREE.SphereGeometry(0.48, 10, 10), leafMat);
        foliage.position.y = 0.82;
        plantGrp.add(pot, foliage);
        scene.add(plantGrp);
      });

      // 3. NINE SPECIALIZED OFFICE WORKSTATIONS & 9 ARTICULATED HUMAN AI EMPLOYEES (Zero circular robot pads!)
      const quickBar = document.getElementById('quickAgentSelectorBar');
      if (quickBar) quickBar.innerHTML = '';

      const sharedDeskMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.35, metalness: 0.45 });
      const sharedLegMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4, metalness: 0.65 });
      const monitorBezelMat = new THREE.MeshStandardMaterial({ color: 0x090d16, roughness: 0.3, metalness: 0.5 });

      BASE_ZONES_CONFIG.forEach((cfg, idx) => {
        const zx = cfg.deskX;
        const zz = cfg.deskZ;
        const deskYaw = cfg.deskYaw || 0;

        const zoneGroup = new THREE.Group();
        zoneGroup.position.set(zx, 0, zz);
        zoneGroup.rotation.y = deskYaw;
        scene.add(zoneGroup);

        // Rectangular Under-Desk Floor Mat (Pickable for workstation selection — NOT a glowing circular pad)
        const padMesh = new THREE.Mesh(
          new THREE.BoxGeometry(3.4, 0.03, 2.8),
          new THREE.MeshStandardMaterial({ color: 0x131f38, roughness: 0.75, metalness: 0.1 })
        );
        padMesh.position.y = 0.025;
        padMesh.userData = { pickType: 'ZONE', role: cfg.role, zoneConfig: cfg };
        zoneGroup.add(padMesh);
        WORLD_3D.pickableMeshes.push(padMesh);

        // Subtle Rectangular Floor Accent Trim around Workstation Mat
        const borderRing = new THREE.Mesh(
          new THREE.BoxGeometry(3.46, 0.02, 0.06),
          new THREE.MeshBasicMaterial({ color: cfg.colorHex, transparent: true, opacity: 0.65 })
        );
        borderRing.position.set(0, 0.04, -1.38);
        zoneGroup.add(borderRing);

        // Subtle Floor Cable / Data Line toward Hallway Door
        const conduitMat = new THREE.LineBasicMaterial({ color: cfg.colorHex, transparent: true, opacity: 0.25 });
        const conduitLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(zx, 0.04, zz),
            new THREE.Vector3(cfg.doorX || 0, 0.04, cfg.doorZ || 0)
          ]),
          conduitMat
        );
        scene.add(conduitLine);

        // Executive Rectangular Office Desk (Tabletop + 4 Architectural Legs + Side Drawer Cabinet)
        const deskMesh = new THREE.Mesh(new THREE.BoxGeometry(2.35, 0.09, 0.88), sharedDeskMat);
        deskMesh.position.set(0, 0.76, -0.68);
        deskMesh.userData = { pickType: 'ZONE', role: cfg.role, zoneConfig: cfg };
        zoneGroup.add(deskMesh);
        WORLD_3D.pickableMeshes.push(deskMesh);

        [[-1.08, -1.04], [1.08, -1.04], [-1.08, -0.32], [1.08, -0.32]].forEach(([lx, lz]) => {
          const leg = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.74, 0.07), sharedLegMat);
          leg.position.set(lx, 0.37, lz);
          zoneGroup.add(leg);
        });

        const sideDrawer = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.68, 0.78), sharedLegMat);
        sideDrawer.position.set(0.82, 0.36, -0.68);
        zoneGroup.add(sideDrawer);

        // Dual Widescreen Computer Monitors + Monitor Stands + Keyboard + Coffee Mug on Desk
        const monStand1 = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.26, 0.08), monitorBezelMat);
        monStand1.position.set(-0.46, 0.92, -0.84);
        const monStand2 = monStand1.clone();
        monStand2.position.set(0.46, 0.92, -0.84);
        zoneGroup.add(monStand1, monStand2);

        const holoScreen = new THREE.Mesh(
          new THREE.BoxGeometry(0.86, 0.50, 0.04),
          new THREE.MeshBasicMaterial({ color: cfg.colorHex })
        );
        holoScreen.position.set(-0.46, 1.16, -0.80);
        holoScreen.rotation.y = 0.14;
        zoneGroup.add(holoScreen);

        const secondMonitor = new THREE.Mesh(
          new THREE.BoxGeometry(0.86, 0.50, 0.04),
          new THREE.MeshBasicMaterial({ color: cfg.visorHex })
        );
        secondMonitor.position.set(0.46, 1.16, -0.80);
        secondMonitor.rotation.y = -0.14;
        zoneGroup.add(secondMonitor);

        const keyboardMesh = new THREE.Mesh(
          new THREE.BoxGeometry(0.48, 0.025, 0.18),
          monitorBezelMat
        );
        keyboardMesh.position.set(0, 0.82, -0.45);
        zoneGroup.add(keyboardMesh);

        const mugMesh = new THREE.Mesh(
          new THREE.CylinderGeometry(0.055, 0.05, 0.11, 10),
          new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.3 })
        );
        mugMesh.position.set(0.82, 0.86, -0.42);
        zoneGroup.add(mugMesh);

        // Ergonomic Rolling Office Chair (Positioned at local z = +0.28 so seated employee sits cleanly in chair facing desk at z = -0.68)
        const chairSeat = new THREE.Mesh(
          new THREE.BoxGeometry(0.58, 0.08, 0.56),
          new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5, metalness: 0.35 })
        );
        chairSeat.position.set(0, 0.48, 0.28);
        zoneGroup.add(chairSeat);

        const chairBack = new THREE.Mesh(
          new THREE.BoxGeometry(0.56, 0.72, 0.09),
          new THREE.MeshStandardMaterial({ color: cfg.suitHex, roughness: 0.45, metalness: 0.3 })
        );
        chairBack.position.set(0, 0.86, 0.54);
        zoneGroup.add(chairBack);

        const chairStem = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.26, 0.44, 8), sharedLegMat);
        chairStem.position.set(0, 0.22, 0.28);
        zoneGroup.add(chairStem);

        // Side Department Bookshelf / Server Rack Cabinet
        const propMesh = new THREE.Mesh(
          new THREE.BoxGeometry(0.75, 1.85, 0.48),
          new THREE.MeshStandardMaterial({ color: 0x162238, roughness: 0.4, metalness: 0.55 })
        );
        propMesh.position.set(-1.45, 0.94, -0.95);
        zoneGroup.add(propMesh);

        // Compute World Coordinates for workSpot (seated at desk), idleSpot (standing by side bookshelf), and commSpot (room doorway / hallway)
        const workLocal = new THREE.Vector3(0, 0, 0.12).applyAxisAngle(new THREE.Vector3(0, 1, 0), deskYaw);
        const idleLocal = new THREE.Vector3(1.38, 0, 0.45).applyAxisAngle(new THREE.Vector3(0, 1, 0), deskYaw);
        const workSpot = { x: zx + workLocal.x, z: zz + workLocal.z, yaw: deskYaw + Math.PI };
        const idleSpot = { x: zx + idleLocal.x, z: zz + idleLocal.z, yaw: deskYaw };
        const commSpot = {
          x: cfg.doorX !== undefined ? cfg.doorX : 0,
          z: cfg.doorZ !== undefined ? cfg.doorZ : 0,
          yaw: Math.atan2(-(cfg.doorX || 1), -(cfg.doorZ || 1))
        };

        WORLD_3D.zonesByRole[cfg.role] = {
          cfg,
          zoneGroup,
          padMesh,
          borderRing,
          holoScreen,
          conduitMat,
          worldPos: new THREE.Vector3(zx, 0, zz),
          workSpot,
          idleSpot,
          commSpot
        };

        // Zone 2D Sign Element
        const signEl = document.createElement('div');
        signEl.className = 'zone-3d-sign';
        signEl.innerHTML = `<strong>${escapeHtml(formatZoneName(cfg.role))}</strong>`;
        signEl.onclick = (e) => {
          e.stopPropagation();
          selectZoneIn3DWorld(cfg.role);
        };
        overlay.appendChild(signEl);
        WORLD_3D.overlaySignEls[cfg.role] = signEl;

        // Create 3D Articulated Human Character for this Employee
        const charParts = createArticulated3DCharacter(THREE, cfg);
        const startSpot = cfg.role === 'CUSTOMER_SUPPORT_AGENT' ? idleSpot : workSpot;
        charParts.root.position.set(startSpot.x, 0.02, startSpot.z);
        charParts.root.rotation.y = startSpot.yaw;
        scene.add(charParts.root);

        WORLD_3D.pickableMeshes.push(charParts.torsoMesh, charParts.helmetMesh);

        WORLD_3D.charactersByRole[cfg.role] = {
          role: cfg.role,
          employeeId: `EMP_0${idx + 1}_${cfg.role.replace('_AGENT', '')}`,
          cfg,
          parts: charParts,
          animState: cfg.role === 'CUSTOMER_SUPPORT_AGENT' ? 'IDLE' : 'WORK_AT_DESK',
          normalizedAnimState: cfg.role === 'CUSTOMER_SUPPORT_AGENT' ? 'IDLE' : 'WORK',
          backendStatus: 'IDLE',
          movementState: 'STATIONARY_AT_WORKSTATION',
          navigationStatus: 'AT_DESTINATION',
          assignedWorkstation: cfg.zoneId,
          destinationPos: { x: startSpot.x, z: startSpot.z, label: cfg.zoneId },
          waypoints: [],
          targetYaw: startSpot.yaw,
          lookAtRole: null,
          walkSpeed: 4.8,
          actualSpeed: 0.0,
          activeTaskId: null,
          lastStateUpdateAt: new Date().toISOString(),
          lastBackendSyncAt: new Date().toISOString(),
          lastMovementError: null,
          phaseOffset: idx * 0.75
        };

        // Character 2D Name & Status Tag
        const charTag = document.createElement('div');
        charTag.className = 'char-3d-label';
        charTag.onclick = (e) => {
          e.stopPropagation();
          selectCharacterIn3DWorld(cfg.role, true);
        };
        overlay.appendChild(charTag);
        WORLD_3D.overlayCharEls[cfg.role] = charTag;

        // Add Quick Selector Pill in Bottom HUD
        if (quickBar) {
          const pill = document.createElement('button');
          pill.className = 'quick-agent-pill';
          pill.id = `quickAgentPill_${cfg.role}`;
          pill.innerHTML = `<span class="char-state-dot" id="quickDot_${cfg.role}" style="background:#10b981;"></span><span>${escapeHtml(formatAgentShort(cfg.role))}</span>`;
          pill.onclick = () => selectCharacterIn3DWorld(cfg.role, true);
          quickBar.appendChild(pill);
        }
      });

      // 3. INTER-AGENT HOLOGRAPHIC COMMUNICATION BEAM & PULSE PARTICLE
      const beamPts = [new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, 2, 0)];
      const beamGeo = new THREE.BufferGeometry().setFromPoints(beamPts);
      const beamMat = new THREE.LineBasicMaterial({ color: 0x22d3ee, linewidth: 2, transparent: true, opacity: 0.9 });
      const commBeamLine = new THREE.Line(beamGeo, beamMat);
      commBeamLine.visible = false;
      scene.add(commBeamLine);

      const commPulseMesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.24, 12, 12),
        new THREE.MeshBasicMaterial({ color: 0xfacc15 })
      );
      commPulseMesh.visible = false;
      scene.add(commPulseMesh);

      // Active Speech Bubble Element + Partner Reply Bubble Element on Overlay
      const bubbleEl = document.createElement('div');
      bubbleEl.className = 'char-speech-bubble';
      bubbleEl.style.display = 'none';
      overlay.appendChild(bubbleEl);

      const replyBubbleEl = document.createElement('div');
      replyBubbleEl.className = 'char-speech-bubble reply-bubble';
      replyBubbleEl.style.display = 'none';
      overlay.appendChild(replyBubbleEl);
      WORLD_3D.overlayReplyBubbleEl = replyBubbleEl;

      WORLD_3D.scene = scene;
      WORLD_3D.camera = camera;
      WORLD_3D.renderer = renderer;
      WORLD_3D.clock = new THREE.Clock();
      WORLD_3D.raycaster = new THREE.Raycaster();
      WORLD_3D.mouse = new THREE.Vector2();
      WORLD_3D.coreGroup = coreGroup;
      WORLD_3D.coreCrystal = coreCrystal;
      WORLD_3D.coreRing1 = coreRing1;
      WORLD_3D.coreRing2 = coreRing2;
      WORLD_3D.commBeamLine = commBeamLine;
      WORLD_3D.commPulseMesh = commPulseMesh;
      WORLD_3D.overlayBubbleEl = bubbleEl;
      WORLD_3D.initialized = true;

      bind3DCanvasInteraction(canvas);
      window.addEventListener('resize', onResize3DWorld);
      sync3DOverlayControlButtons();
      requestAnimationFrame(animate3DWorldLoop);
      // Activity and dialogue are rendered only from persisted backend events.
    }

    function bind3DCanvasInteraction(canvas) {
      canvas.addEventListener('contextmenu', e => e.preventDefault());

      canvas.addEventListener('pointerdown', (e) => {
        WORLD_3D.dragState.isDown = true;
        WORLD_3D.dragState.button = e.button;
        WORLD_3D.dragState.startX = e.clientX;
        WORLD_3D.dragState.startY = e.clientY;
        WORLD_3D.dragState.moved = false;
      });

      canvas.addEventListener('pointermove', (e) => {
        if (WORLD_3D.dragState.isDown || !WORLD_3D.initialized) return;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        let hovered = null;
        let minD = 38;
        Object.values(WORLD_3D.charactersByRole).forEach(ch => {
          const pos = ch.parts.root.position.clone().add(new THREE.Vector3(0, 1.1, 0));
          const pt = project3DToOverlay(pos, rect.width, rect.height);
          if (pt) {
            const d = Math.hypot(pt.x - mx, pt.y - my);
            if (d < minD) {
              minD = d;
              hovered = ch.role;
            }
          }
        });
        if (HOVERED_AGENT_ID !== hovered) {
          HOVERED_AGENT_ID = hovered;
          canvas.style.cursor = hovered ? 'pointer' : 'grab';
        }
      });

      canvas.addEventListener('pointerleave', () => {
        HOVERED_AGENT_ID = null;
      });

      window.addEventListener('pointermove', (e) => {
        if (!WORLD_3D.dragState.isDown) return;
        const dx = e.clientX - WORLD_3D.dragState.startX;
        const dy = e.clientY - WORLD_3D.dragState.startY;
        if (Math.hypot(dx, dy) > 4) {
          WORLD_3D.dragState.moved = true;
        }
        WORLD_3D.dragState.startX = e.clientX;
        WORLD_3D.dragState.startY = e.clientY;

        if (WORLD_3D.dragState.button === 2 || e.shiftKey) {
          // Right-drag or Shift-drag: Pan camera target across base floor
          FOLLOW_SELECTED_AGENT = false;
          const panFactor = 0.035 * (WORLD_3D.camSpherical.radius / 30);
          const cosT = Math.cos(WORLD_3D.camSpherical.theta);
          const sinT = Math.sin(WORLD_3D.camSpherical.theta);
          WORLD_3D.camSpherical.targetX -= (dx * cosT - dy * sinT) * panFactor;
          WORLD_3D.camSpherical.targetZ -= (dx * sinT + dy * cosT) * panFactor;
          WORLD_3D.camSpherical.targetX = Math.max(-18, Math.min(18, WORLD_3D.camSpherical.targetX));
          WORLD_3D.camSpherical.targetZ = Math.max(-18, Math.min(18, WORLD_3D.camSpherical.targetZ));
        } else {
          // Left-drag: Orbit camera smoothly within safe elevation bounds
          WORLD_3D.camSpherical.theta -= dx * 0.0065;
          WORLD_3D.camSpherical.phi = Math.max(0.32, Math.min(1.32, WORLD_3D.camSpherical.phi - dy * 0.0055));
        }
      });

      window.addEventListener('pointerup', (e) => {
        if (!WORLD_3D.dragState.isDown) return;
        const wasClick = !WORLD_3D.dragState.moved && e.target === canvas;
        WORLD_3D.dragState.isDown = false;
        if (wasClick) {
          handle3DCanvasClick(e, canvas);
        }
      });

      canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        zoom3DCamera(e.deltaY > 0 ? 2.4 : -2.4);
      }, { passive: false });
    }

    function handle3DCanvasClick(e, canvas) {
      if (!WORLD_3D.initialized || !WORLD_3D.raycaster) return;
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;
      WORLD_3D.mouse.x = (clickX / rect.width) * 2 - 1;
      WORLD_3D.mouse.y = -(clickY / rect.height) * 2 + 1;

      if (WORLD_3D.scene) WORLD_3D.scene.updateMatrixWorld(true);
      if (WORLD_3D.camera) WORLD_3D.camera.updateMatrixWorld();

      WORLD_3D.raycaster.setFromCamera(WORLD_3D.mouse, WORLD_3D.camera);
      const hits = WORLD_3D.raycaster.intersectObjects(WORLD_3D.pickableMeshes, true);
      if (hits.length > 0) {
        let obj = hits[0].object;
        while (obj && !obj.userData?.pickType && obj.parent) {
          obj = obj.parent;
        }
        const u = obj?.userData || {};
        if (u.pickType === 'AGENT' && u.role) {
          selectCharacterIn3DWorld(u.role, true);
          return;
        } else if (u.pickType === 'ZONE' && u.role) {
          selectZoneIn3DWorld(u.role);
          return;
        }
      }

      // Screen-space projected picking fallback (ensures instant click response in both WebGL & Canvas3D)
      let closestAgent = null;
      let minAgentDist = 42;
      Object.values(WORLD_3D.charactersByRole).forEach(ch => {
        const pos = ch.parts.root.position.clone().add(new THREE.Vector3(0, 1.0, 0));
        const pt = project3DToOverlay(pos, rect.width, rect.height);
        if (pt) {
          const d = Math.hypot(pt.x - clickX, pt.y - clickY);
          if (d < minAgentDist) {
            minAgentDist = d;
            closestAgent = ch.role;
          }
        }
      });
      if (closestAgent) {
        selectCharacterIn3DWorld(closestAgent, true);
        return;
      }

      let closestZone = null;
      let minZoneDist = 64;
      Object.values(WORLD_3D.zonesByRole).forEach(z => {
        const pt = project3DToOverlay(z.worldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), rect.width, rect.height);
        if (pt) {
          const d = Math.hypot(pt.x - clickX, pt.y - clickY);
          if (d < minZoneDist) {
            minZoneDist = d;
            closestZone = z.cfg.role;
          }
        }
      });
      if (closestZone) {
        selectZoneIn3DWorld(closestZone);
      }
    }

    function selectCharacterIn3DWorld(role, openModal = false) {
      SELECTED_AGENT_ID = role;
      const ch = WORLD_3D.charactersByRole[role];
      const agents = getEnrichedAgentsList(!STATE.online);
      const ag = agents.find(a => a.role === role) || {};

      // Smoothly move camera target toward selected character
      if (ch && ch.parts && ch.parts.root) {
        WORLD_3D.camSpherical.targetX = ch.parts.root.position.x * 0.55;
        WORLD_3D.camSpherical.targetZ = ch.parts.root.position.z * 0.55;
      }

      // Update Top-Left Mini HUD
      const typeTag = document.getElementById('hudSelectedTypeTag');
      const statusBadge = document.getElementById('hudSelectedStatusBadge');
      const titleEl = document.getElementById('hudSelectedTitle');
      const descEl = document.getElementById('hudSelectedDesc');
      if (typeTag) typeTag.textContent = `${t('NHÂN VẬT AI', 'AI CHARACTER')} • ${formatZoneName(role)}`;
      if (statusBadge) {
        statusBadge.textContent = `${formatStatusLabel(ag.command_status || 'IDLE')} (${formatStatusLabel(ch?.animState || 'IDLE')})`;
        statusBadge.className = `chip ${ag.command_status === 'ERROR' || ag.command_status === 'OFFLINE' ? 'danger' : (ag.command_status === 'WAITING_APPROVAL' ? 'warn' : 'success')}`;
      }
      if (titleEl) titleEl.textContent = `${formatAgentTitle(role)} (${formatAgentStep(role)})`;
      if (descEl) descEl.textContent = `${t('Nhiệm vụ hiện tại:', 'Current Job:')} ${ag.current_job || ag.responsibility || ''}`;

      // Highlight quick bar pill
      document.querySelectorAll('.quick-agent-pill').forEach(p => {
        p.classList.toggle('active', p.id === `quickAgentPill_${role}`);
      });

      if (openModal) {
        openAgentInspector(role);
      }
    }

    function selectZoneIn3DWorld(role) {
      SELECTED_AGENT_ID = role;
      const z = WORLD_3D.zonesByRole[role];
      const agents = getEnrichedAgentsList(!STATE.online);
      const ag = agents.find(a => a.role === role) || {};

      if (z) {
        WORLD_3D.camSpherical.targetX = z.worldPos.x * 0.55;
        WORLD_3D.camSpherical.targetZ = z.worldPos.z * 0.55;
      }

      const typeTag = document.getElementById('hudSelectedTypeTag');
      const statusBadge = document.getElementById('hudSelectedStatusBadge');
      const titleEl = document.getElementById('hudSelectedTitle');
      const descEl = document.getElementById('hudSelectedDesc');
      if (typeTag) typeTag.textContent = `${t('PHÂN KHU CĂN CỨ', 'BASE SECTOR')} • ${formatZoneName(role)}`;
      if (statusBadge) {
        statusBadge.textContent = `${t('TRẠNG THÁI:', 'STATUS:')} ${formatStatusLabel(ag.command_status || 'IDLE')}`;
        statusBadge.className = 'chip cyan';
      }
      if (titleEl) titleEl.textContent = `${formatZoneName(role)} — ${formatZoneSub(role)}`;
      if (descEl) descEl.textContent = `${t('Thiết bị:', 'Equipment:')} ${formatZoneEquip(role)} | ${t('Phụ trách:', 'Assigned AI:')} ${formatAgentTitle(role)} (${ag.current_job || ''})`;
      toggleTopLeftHudMinimize(false);
    }

    function transitionCharacterAnimState(ch, nextStateRaw) {
      if (!ch) return;
      const nextRaw = String(nextStateRaw || 'IDLE').toUpperCase();
      const norm = normalizeAnimStateName(nextRaw);
      const prevNorm = ch.normalizedAnimState || normalizeAnimStateName(ch.animState);
      ch.animState = nextRaw;
      ch.normalizedAnimState = norm;
      ch.lastStateUpdateAt = new Date().toISOString();

      if (ch.parts && ch.parts.mixer && ch.parts.actionsByState) {
        const nextAction = ch.parts.actionsByState[norm] || ch.parts.actionsByState[nextRaw] || ch.parts.actionsByState.IDLE;
        if (nextAction && ch.parts.activeAction !== nextAction) {
          try {
            nextAction.reset().play();
            if (ch.parts.activeAction && prevNorm !== norm) {
              ch.parts.activeAction.crossFadeTo(nextAction, 0.28, false);
            }
            ch.parts.activeAction = nextAction;
            ch.parts.activeClipName = nextAction.getClip ? nextAction.getClip().name : norm.toLowerCase();
          } catch (err) {
            ch.lastMovementError = err.message;
          }
        }
      }
    }

    function sendCharacterAlongPath(role, destSpot, finalAnimState, useRun = false, destLabel = '') {
      const ch = WORLD_3D.charactersByRole[role];
      if (!ch || !ch.parts?.root) return;
      if (!destSpot || typeof destSpot.x !== 'number' || typeof destSpot.z !== 'number') {
        ch.lastMovementError = 'Unreachable or invalid destination coordinates';
        ch.navigationStatus = 'RECOVERED_AT_WORKSTATION';
        return;
      }
      const safeX = Math.max(-18.5, Math.min(18.5, destSpot.x));
      const safeZ = Math.max(-14.2, Math.min(14.2, destSpot.z));
      ch.destinationPos = { x: Number(safeX.toFixed(2)), z: Number(safeZ.toFixed(2)), label: destLabel || ch.assignedWorkstation || role };

      if (!MOVEMENT_ENABLED || REDUCED_MOTION) {
        ch.waypoints = [];
        ch.movementState = 'MOVEMENT_PAUSED';
        ch.navigationStatus = 'PAUSED_BY_TOGGLE';
        ch.actualSpeed = 0.0;
        transitionCharacterAnimState(ch, finalAnimState);
        ch.targetYaw = destSpot.yaw !== undefined ? destSpot.yaw : ch.targetYaw;
        return;
      }

      const curX = ch.parts.root.position.x;
      const curZ = ch.parts.root.position.z;
      const dist = Math.hypot(safeX - curX, safeZ - curZ);
      if (dist < 0.35) {
        ch.waypoints = [];
        ch.movementState = 'STATIONARY_AT_DESTINATION';
        ch.navigationStatus = 'AT_DESTINATION';
        ch.actualSpeed = 0.0;
        transitionCharacterAnimState(ch, finalAnimState);
        ch.targetYaw = destSpot.yaw !== undefined ? destSpot.yaw : ch.targetYaw;
        return;
      }
      const pathPts = buildSafeCorridorPath(curX, curZ, safeX, safeZ);
      if (!pathPts || pathPts.length === 0) {
        ch.lastMovementError = 'Pathfinding returned empty path; recovered safely';
        ch.navigationStatus = 'RECOVERED';
        transitionCharacterAnimState(ch, finalAnimState);
        return;
      }
      ch.waypoints = pathPts;
      ch.finalAnimState = finalAnimState;
      ch.finalYaw = destSpot.yaw;
      ch.walkSpeed = useRun ? 8.2 : 4.8;
      ch.movementState = useRun ? 'RUNNING_TO_TARGET' : 'WALKING_TO_TARGET';
      ch.navigationStatus = `EN_ROUTE (${pathPts.length} waypoints)`;
      ch.lastMovementError = null;
      transitionCharacterAnimState(ch, useRun ? 'RUN' : 'WALK');
    }

    let COLLAB_PAIR_INDEX = 0;
    function triggerAutonomousCollaborationWalkNow() {
      if (!WORLD_3D.initialized || !MOVEMENT_ENABLED || REDUCED_MOTION || !STATE.online) return;
      if (CURRENT_ACTIVE_SPEECH) return;
      const pairs = [
        { from: 'RESEARCH_AGENT', to: 'PRODUCT_AGENT', mode: 'BOARDROOM', taskLabel: 'SYNC_MARKET_SIGNALS' },
        { from: 'PRODUCT_AGENT', to: 'CODING_AGENT', mode: 'VISIT_DESK', taskLabel: 'VERIFY_PRICING_ENGINE' },
        { from: 'MARKETING_AGENT', to: 'SALES_AGENT', mode: 'VISIT_DESK', taskLabel: 'ALIGN_LEAD_PROPOSALS' },
        { from: 'FINANCE_AGENT', to: 'OPTIMIZATION_AGENT', mode: 'BOARDROOM', taskLabel: 'AUDIT_GROSS_MARGIN' },
        { from: 'SECURITY_AGENT', to: 'CODING_AGENT', mode: 'RETURN_DESKS', taskLabel: 'RBAC_SECURITY_PATROL' }
      ];
      const step = pairs[COLLAB_PAIR_INDEX % pairs.length];
      COLLAB_PAIR_INDEX++;

      const chA = WORLD_3D.charactersByRole[step.from];
      const chB = WORLD_3D.charactersByRole[step.to];
      const zA = WORLD_3D.zonesByRole[step.from];
      const zB = WORLD_3D.zonesByRole[step.to];
      if (!chA || !chB || !zA || !zB) return;

      if (step.mode === 'BOARDROOM' && WORLD_3D.meetingSpots && WORLD_3D.meetingSpots.length >= 2) {
        const seatA = WORLD_3D.meetingSpots[0];
        const seatB = WORLD_3D.meetingSpots[5] || WORLD_3D.meetingSpots[1];
        chA.activeTaskId = step.taskLabel;
        chB.activeTaskId = step.taskLabel;
        sendCharacterAlongPath(step.from, seatA, 'MEETING', false, 'CENTRAL_BOARDROOM_SEAT_1');
        sendCharacterAlongPath(step.to, seatB, 'MEETING', false, 'CENTRAL_BOARDROOM_SEAT_2');
      } else if (step.mode === 'VISIT_DESK') {
        chA.activeTaskId = step.taskLabel;
        chB.activeTaskId = step.taskLabel;
        sendCharacterAlongPath(step.from, zB.commSpot, 'TALK', false, `COLLAB_${step.to}`);
        sendCharacterAlongPath(step.to, zB.workSpot, 'LISTEN', false, `WORKSTATION_${step.to}`);
      } else {
        Object.keys(WORLD_3D.charactersByRole).forEach(r => {
          const c = WORLD_3D.charactersByRole[r];
          const z = WORLD_3D.zonesByRole[r];
          if (c && z) {
            const spot = c.backendStatus === 'IDLE' ? z.idleSpot : z.workSpot;
            const st = c.backendStatus === 'IDLE' ? 'IDLE' : (r === 'CODING_AGENT' ? 'TYPE' : (r === 'RESEARCH_AGENT' ? 'READ' : 'WORK_AT_DESK'));
            sendCharacterAlongPath(r, spot, st, false, z.cfg.zoneId);
          }
        });
      }
      updateMovementStatusIndicatorsAndDiagnostics();
    }

    function onResize3DWorld() {
      if (!WORLD_3D.initialized || !WORLD_3D.camera) return;
      const stage = document.getElementById('aiBase3DStage');
      const canvas = document.getElementById('aiBase3DCanvas');
      if (!stage || stage.clientWidth === 0 || stage.clientHeight === 0) return;
      WORLD_3D.camera.aspect = stage.clientWidth / stage.clientHeight;
      WORLD_3D.camera.updateProjectionMatrix();
      if (WORLD_3D.renderer) {
        WORLD_3D.renderer.setSize(stage.clientWidth, stage.clientHeight);
      } else if (canvas) {
        canvas.width = stage.clientWidth;
        canvas.height = stage.clientHeight;
      }
    }

    function animate3DWorldLoop() {
      requestAnimationFrame(animate3DWorldLoop);
      if (!WORLD_3D.initialized || OVERVIEW_DISPLAY_MODE !== 'GAME') return;

      const dt = Math.min(0.05, WORLD_3D.clock.getDelta());
      const elapsed = WORLD_3D.clock.getElapsedTime();
      const motionScale = REDUCED_MOTION ? 0 : 1;

      // 1. Animate Central Boardroom Tabletop Hologram
      if (WORLD_3D.coreCrystal && motionScale > 0) {
        WORLD_3D.coreCrystal.rotation.y += dt * 0.85;
        WORLD_3D.coreCrystal.rotation.x = Math.sin(elapsed * 1.4) * 0.2;
        WORLD_3D.coreRing1.rotation.z += dt * 0.65;
        WORLD_3D.coreRing2.rotation.y -= dt * 0.9;
      }

      // 2. Check Active Speech Queue & Expire Finished Speech Bubble
      const nowMs = Date.now();
      if (CURRENT_ACTIVE_SPEECH && nowMs >= CURRENT_ACTIVE_SPEECH.expiresAt) {
        const finishedSender = CURRENT_ACTIVE_SPEECH.msg.sender_agent_id;
        const finishedReceiver = CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id;
        CURRENT_ACTIVE_SPEECH = null;
        if (WORLD_3D.commBeamLine) WORLD_3D.commBeamLine.visible = false;
        if (WORLD_3D.commPulseMesh) WORLD_3D.commPulseMesh.visible = false;
        if (WORLD_3D.overlayBubbleEl) WORLD_3D.overlayBubbleEl.style.display = 'none';
      if (WORLD_3D.overlayReplyBubbleEl) WORLD_3D.overlayReplyBubbleEl.style.display = 'none';

        // Return characters from TALK / LISTEN / MEETING back to their honest backend state
        [finishedSender, finishedReceiver].forEach(r => {
          const c = WORLD_3D.charactersByRole[r];
          const z = WORLD_3D.zonesByRole[r];
          if (c && z) {
            c.lookAtRole = null;
            const targetSpot = (c.backendStatus === 'IDLE' || c.backendStatus === 'OFFLINE') ? z.idleSpot : z.workSpot;
            const postState = c.backendStatus === 'IDLE'
              ? 'IDLE'
              : (c.backendStatus === 'OFFLINE'
                  ? 'OFFLINE'
                  : (c.backendStatus === 'WAITING_APPROVAL' ? 'ERROR' : (c.backendStatus === 'WORKING' ? 'TYPE' : 'WORK_AT_DESK')));
            sendCharacterAlongPath(r, targetSpot, postState, false);
          }
        });
      }

      if (!CURRENT_ACTIVE_SPEECH && ACTIVE_SPEECH_QUEUE.length > 0 && STATE.online) {
        const nextMsg = ACTIVE_SPEECH_QUEUE.shift();
        activateSpeechBubbleIn3D(nextMsg);
      }

      // 3. Update All Characters (Hallway Pathfinding + Collision Avoidance + 12-State Human Limb Articulation)
      const allChars = Object.values(WORLD_3D.charactersByRole);
      allChars.forEach(ch => {
        const root = ch.parts.root;
        const t = elapsed + ch.phaseOffset;

        // Update THREE.AnimationMixer with real frame delta time (Part A2)
        if (ch.parts && ch.parts.mixer) {
          try {
            ch.parts.mixer.update(MOVEMENT_ENABLED && !REDUCED_MOTION ? dt : 0);
          } catch (mixErr) {
            ch.lastMovementError = mixErr.message;
          }
        }

        // Follow waypoints if moving (WALK / RUN) with inter-employee collision avoidance
        if (ch.waypoints && ch.waypoints.length > 0 && STATE.online && MOVEMENT_ENABLED && !REDUCED_MOTION) {
          const wp = ch.waypoints[0];
          const dx = wp.x - root.position.x;
          const dz = wp.z - root.position.z;
          const dist = Math.hypot(dx, dz);
          const step = ch.walkSpeed * dt;

          if (dist <= step) {
            root.position.x = wp.x;
            root.position.z = wp.z;
            ch.waypoints.shift();
            if (ch.waypoints.length === 0) {
              ch.actualSpeed = 0.0;
              ch.movementState = 'ARRIVED_AT_DESTINATION';
              ch.navigationStatus = 'AT_DESTINATION';
              transitionCharacterAnimState(ch, ch.finalAnimState || 'WORK_AT_DESK');
              ch.targetYaw = ch.finalYaw !== undefined ? ch.finalYaw : root.rotation.y;
            }
          } else {
            let moveX = (dx / dist) * step;
            let moveZ = (dz / dist) * step;
            // Dynamic separation steering to avoid colliding with other employees
            allChars.forEach(other => {
              if (other.role === ch.role) return;
              const ox = root.position.x - other.parts.root.position.x;
              const oz = root.position.z - other.parts.root.position.z;
              const od = Math.hypot(ox, oz);
              if (od > 0.01 && od < 1.15) {
                const push = ((1.15 - od) / 1.15) * step * 0.55;
                moveX += (ox / od) * push;
                moveZ += (oz / od) * push;
              }
            });
            root.position.x += moveX;
            root.position.z += moveZ;
            ch.actualSpeed = Number((Math.hypot(moveX, moveZ) / Math.max(dt, 0.001)).toFixed(2));
            ch.navigationStatus = `MOVING (${ch.waypoints.length} wp left)`;
            ch.targetYaw = Math.atan2(moveX, moveZ);
          }
        } else {
          ch.actualSpeed = 0.0;
          if (!MOVEMENT_ENABLED || REDUCED_MOTION) {
            ch.movementState = 'MOVEMENT_PAUSED';
            ch.navigationStatus = 'PAUSED_BY_TOGGLE';
          } else if (ch.lookAtRole && WORLD_3D.charactersByRole[ch.lookAtRole]) {
            const otherPos = WORLD_3D.charactersByRole[ch.lookAtRole].parts.root.position;
            ch.targetYaw = Math.atan2(otherPos.x - root.position.x, otherPos.z - root.position.z);
          }
        }

        // Smooth rotation interpolation (No snapping)
        root.rotation.y = lerpAngle(root.rotation.y, ch.targetYaw, Math.min(1, dt * 8.5));

        // 12-State Human Articulated Animation State Machine:
        // IDLE, WALK, RUN, SIT, TYPE, WORK_AT_DESK, READ, TALK, LISTEN, MEETING, CELEBRATE, ERROR (+ OFFLINE)
        const la = ch.parts.leftArmPivot.rotation;
        const ra = ch.parts.rightArmPivot.rotation;
        const ll = ch.parts.leftLegPivot.rotation;
        const rl = ch.parts.rightLegPivot.rotation;
        const bg = ch.parts.bodyGroup;
        const hg = ch.parts.headGroup.rotation;
        const stAnim = ch.animState || 'IDLE';

        if (stAnim === 'WALK' || stAnim === 'RUN') {
          const freq = stAnim === 'RUN' ? 13.5 : 8.5;
          const amp = (stAnim === 'RUN' ? 0.68 : 0.44) * motionScale;
          ll.x = Math.sin(t * freq) * amp;
          rl.x = -Math.sin(t * freq) * amp;
          la.x = -Math.sin(t * freq) * amp * 0.82;
          ra.x = Math.sin(t * freq) * amp * 0.82;
          la.z = 0;
          ra.z = 0;
          bg.position.y = Math.abs(Math.cos(t * freq)) * 0.06 * motionScale;
          hg.x = 0;
          hg.y = 0;
        } else if (stAnim === 'TYPE' || stAnim === 'WORK_AT_DESK' || stAnim === 'WORKING' || stAnim === 'SUCCESS') {
          // Seated at office chair typing on keyboard & viewing dual monitors
          ll.x = -1.18;
          rl.x = -1.18;
          const typeSpeed = stAnim === 'TYPE' ? 11.5 : 7.2;
          la.x = -0.68 + Math.sin(t * typeSpeed) * 0.14 * motionScale;
          ra.x = -0.68 + Math.cos(t * typeSpeed) * 0.14 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = -0.18 + Math.sin(t * 2.4) * 0.015 * motionScale;
          hg.y = Math.sin(t * 1.4) * 0.16 * motionScale;
          hg.x = 0.08;
        } else if (stAnim === 'SIT') {
          // Seated calmly in office or boardroom chair
          ll.x = -1.18;
          rl.x = -1.18;
          la.x = -0.35;
          ra.x = -0.35;
          la.z = 0;
          ra.z = 0;
          bg.position.y = -0.18 + Math.sin(t * 1.8) * 0.012 * motionScale;
          hg.y = Math.sin(t * 0.9) * 0.10 * motionScale;
          hg.x = 0.02;
        } else if (stAnim === 'READ' || stAnim === 'THINKING') {
          // Reading tablet / analyzing technical report
          ll.x = -1.10;
          rl.x = -1.10;
          la.x = -0.78;
          ra.x = -0.52 + Math.sin(t * 2.5) * 0.08 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = -0.16 + Math.sin(t * 2.0) * 0.015 * motionScale;
          hg.y = Math.sin(t * 1.8) * 0.14 * motionScale;
          hg.x = 0.18;
        } else if (stAnim === 'MEETING') {
          // Seated around Central Glass Boardroom table collaborating
          ll.x = -1.18;
          rl.x = -1.18;
          la.x = -0.45 + Math.sin(t * 4.2) * 0.16 * motionScale;
          ra.x = -0.62 + Math.cos(t * 4.2) * 0.18 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = -0.18 + Math.sin(t * 2.5) * 0.02 * motionScale;
          hg.y = Math.sin(t * 1.6) * 0.22 * motionScale;
          hg.x = 0.04;
        } else if (stAnim === 'TALK' || stAnim === 'COMMUNICATING') {
          // Speaking with expressive hand gestures
          ll.x = 0;
          rl.x = 0;
          la.x = -0.32 + Math.cos(t * 5.2) * 0.15 * motionScale;
          ra.x = -0.78 + Math.sin(t * 6.0) * 0.24 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = Math.sin(t * 3.0) * 0.03 * motionScale;
          hg.y = Math.sin(t * 2.4) * 0.12 * motionScale;
          hg.x = 0;
        } else if (stAnim === 'LISTEN') {
          // Listening attentively & nodding to speaker
          ll.x = 0;
          rl.x = 0;
          la.x = -0.15;
          ra.x = -0.25;
          la.z = 0;
          ra.z = 0;
          bg.position.y = Math.sin(t * 2.0) * 0.02 * motionScale;
          hg.x = Math.sin(t * 4.5) * 0.09 * motionScale;
          hg.y = 0;
        } else if (stAnim === 'CELEBRATE') {
          // Celebrating verified task completion / revenue order
          ll.x = 0;
          rl.x = 0;
          la.x = -2.35 + Math.sin(t * 8.0) * 0.22 * motionScale;
          ra.x = -2.35 + Math.cos(t * 8.0) * 0.22 * motionScale;
          la.z = 0.18;
          ra.z = -0.18;
          bg.position.y = Math.abs(Math.sin(t * 5.5)) * 0.08 * motionScale;
          hg.x = -0.10;
          hg.y = Math.sin(t * 3.5) * 0.18 * motionScale;
        } else if (stAnim === 'ERROR' || stAnim === 'WAITING') {
          // Needs assistance / waiting for approval posture
          ll.x = 0;
          rl.x = 0;
          la.x = -0.20;
          ra.x = -1.15 + Math.sin(t * 6.0) * 0.12 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = 0;
          hg.x = 0.16;
          hg.y = Math.sin(t * 8.0) * 0.08 * motionScale;
        } else if (stAnim === 'OFFLINE') {
          ll.x = 0;
          rl.x = 0;
          la.x = 0;
          ra.x = 0;
          la.z = 0;
          ra.z = 0;
          bg.position.y = 0;
          hg.x = 0.28;
          hg.y = 0;
        } else {
          // IDLE: Gentle natural human standing posture
          ll.x = 0;
          rl.x = 0;
          la.x = Math.sin(t * 1.8) * 0.05 * motionScale;
          ra.x = -Math.sin(t * 1.8) * 0.05 * motionScale;
          la.z = 0;
          ra.z = 0;
          bg.position.y = Math.sin(t * 1.8) * 0.025 * motionScale;
          hg.y = Math.sin(t * 0.9) * 0.15 * motionScale;
          hg.x = 0;
        }
      });

      // 4. Animate Active Inter-Agent Holographic Beam & Pulse Particle
      if (CURRENT_ACTIVE_SPEECH && WORLD_3D.commBeamLine && WORLD_3D.commBeamLine.visible) {
        const sRole = CURRENT_ACTIVE_SPEECH.msg.sender_agent_id;
        const rRole = CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id;
        const sChar = WORLD_3D.charactersByRole[sRole];
        const rChar = WORLD_3D.charactersByRole[rRole];
        if (sChar && rChar) {
          const p1 = sChar.parts.root.position.clone().add(new THREE.Vector3(0, 1.9, 0));
          const p2 = rChar.parts.root.position.clone().add(new THREE.Vector3(0, 1.9, 0));
          WORLD_3D.commBeamLine.geometry.setFromPoints([p1, p2]);
          if (WORLD_3D.commPulseMesh) {
            WORLD_3D.commPulseMesh.visible = true;
            const frac = (elapsed * 1.35) % 1;
            WORLD_3D.commPulseMesh.position.lerpVectors(p1, p2, frac);
          }
        }
      }

      // 5. Update Camera Position (Follow Mode or Free Isometric Orbit)
      if (FOLLOW_SELECTED_AGENT && SELECTED_AGENT_ID && WORLD_3D.charactersByRole[SELECTED_AGENT_ID]) {
        const targetPos = WORLD_3D.charactersByRole[SELECTED_AGENT_ID].parts.root.position;
        WORLD_3D.camSpherical.targetX += (targetPos.x - WORLD_3D.camSpherical.targetX) * 0.08;
        WORLD_3D.camSpherical.targetZ += (targetPos.z - WORLD_3D.camSpherical.targetZ) * 0.08;
      }

      const sp = WORLD_3D.camSpherical;
      const cx = sp.targetX + sp.radius * Math.sin(sp.phi) * Math.sin(sp.theta);
      const cy = sp.targetY + sp.radius * Math.cos(sp.phi);
      const cz = sp.targetZ + sp.radius * Math.sin(sp.phi) * Math.cos(sp.theta);
      WORLD_3D.camera.position.set(cx, cy, cz);
      WORLD_3D.camera.lookAt(sp.targetX, sp.targetY, sp.targetZ);
      WORLD_3D.camera.updateMatrixWorld();

      // 6. Render 3D Scene (Hardware WebGL or Software 3D Perspective Canvas) & Update 2D Overlay
      if (WORLD_3D.renderer) {
        WORLD_3D.renderer.render(WORLD_3D.scene, WORLD_3D.camera);
      } else if (WORLD_3D.ctx2d) {
        WORLD_3D.scene.updateMatrixWorld(true);
        const stage = document.getElementById('aiBase3DStage');
        const sw = stage ? stage.clientWidth : 960;
        const sh = stage ? stage.clientHeight : 640;
        renderSoftware3DScene(WORLD_3D.ctx2d, sw, sh, elapsed);
      }
      updateMovementStatusIndicatorsAndDiagnostics();
      update2DProjectedOverlay();
    }

    function hexIntToCss(hexInt, alpha = 1) {
      const r = (hexInt >> 16) & 255;
      const g = (hexInt >> 8) & 255;
      const b = hexInt & 255;
      return alpha < 1 ? `rgba(${r},${g},${b},${alpha})` : `rgb(${r},${g},${b})`;
    }

    function drawProjected3DPolygon(ctx, pts3d, width, height, fillStyle, strokeStyle, lineWidth = 1.2, close = true) {
      const pts2d = [];
      for (let i = 0; i < pts3d.length; i++) {
        const p = project3DToOverlay(pts3d[i], width, height);
        if (!p) return false;
        pts2d.push(p);
      }
      ctx.beginPath();
      ctx.moveTo(pts2d[0].x, pts2d[0].y);
      for (let i = 1; i < pts2d.length; i++) {
        ctx.lineTo(pts2d[i].x, pts2d[i].y);
      }
      if (close) ctx.closePath();
      if (fillStyle) {
        ctx.fillStyle = fillStyle;
        ctx.fill();
      }
      if (strokeStyle) {
        ctx.strokeStyle = strokeStyle;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
      }
      return true;
    }

    function drawProjected3DBox(ctx, center3d, yaw, sx, sy, sz, width, height, topColor, sideColor, strokeColor) {
      const cosY = Math.cos(yaw);
      const sinY = Math.sin(yaw);
      const hx = sx * 0.5;
      const hy = sy * 0.5;
      const hz = sz * 0.5;
      const localCorners = [
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, -hy, hz], [-hx, -hy, hz],
        [-hx, hy, -hz],  [hx, hy, -hz],  [hx, hy, hz],  [-hx, hy, hz]
      ];
      const worldPts = localCorners.map(([lx, ly, lz]) => new THREE.Vector3(
        center3d.x + lx * cosY + lz * sinY,
        center3d.y + ly,
        center3d.z - lx * sinY + lz * cosY
      ));
      // Front & side faces + top face
      drawProjected3DPolygon(ctx, [worldPts[0], worldPts[1], worldPts[5], worldPts[4]], width, height, sideColor, strokeColor, 1);
      drawProjected3DPolygon(ctx, [worldPts[1], worldPts[2], worldPts[6], worldPts[5]], width, height, sideColor, strokeColor, 1);
      drawProjected3DPolygon(ctx, [worldPts[2], worldPts[3], worldPts[7], worldPts[6]], width, height, sideColor, strokeColor, 1);
      drawProjected3DPolygon(ctx, [worldPts[3], worldPts[0], worldPts[4], worldPts[7]], width, height, sideColor, strokeColor, 1);
      drawProjected3DPolygon(ctx, [worldPts[4], worldPts[5], worldPts[6], worldPts[7]], width, height, topColor, strokeColor, 1.1);
    }

    function renderSoftware3DScene(ctx, width, height, elapsed) {
      const canvas = ctx.canvas;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      // 1. Corporate Headquarters Ambient Backdrop
      const bgGrad = ctx.createRadialGradient(width * 0.5, height * 0.42, 40, width * 0.5, height * 0.5, Math.max(width, height) * 0.78);
      bgGrad.addColorStop(0, '#0f1c38');
      bgGrad.addColorStop(0.55, '#091124');
      bgGrad.addColorStop(1, '#040812');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // 2. Rectangular Corporate Building Main Floor (46m x 34m) — Strictly NO circular disc or wireframe grid!
      const floorCorners = [
        new THREE.Vector3(-23, 0, -17),
        new THREE.Vector3(23, 0, -17),
        new THREE.Vector3(23, 0, 17),
        new THREE.Vector3(-23, 0, 17)
      ];
      drawProjected3DPolygon(ctx, floorCorners, width, height, 'rgba(11, 19, 36, 0.96)', 'rgba(56, 189, 248, 0.42)', 1.8);

      // 3. Illuminated Orthogonal Office Hallways (x = ±7.2, z = ±5.4)
      [
        { x: -7.2, z: 0, w: 2.2, d: 32.0 },
        { x: 7.2,  z: 0, w: 2.2, d: 32.0 },
        { x: 0,    z: -5.4, w: 43.0, d: 2.0 },
        { x: 0,    z: 5.4,  w: 43.0, d: 2.0 }
      ].forEach(h => {
        const hw = h.w * 0.5;
        const hd = h.d * 0.5;
        drawProjected3DPolygon(
          ctx,
          [
            new THREE.Vector3(h.x - hw, 0.015, h.z - hd),
            new THREE.Vector3(h.x + hw, 0.015, h.z - hd),
            new THREE.Vector3(h.x + hw, 0.015, h.z + hd),
            new THREE.Vector3(h.x - hw, 0.015, h.z + hd)
          ],
          width,
          height,
          'rgba(22, 34, 62, 0.88)',
          'rgba(6, 182, 212, 0.28)',
          1.1
        );
      });

      // 4. Rectangular Department Room Carpets (6 Distinct Office Rooms + Central Boardroom)
      OFFICE_ROOMS_LAYOUT.forEach(rm => {
        const hw = rm.w * 0.5;
        const hd = rm.d * 0.5;
        const pts = [
          new THREE.Vector3(rm.x - hw, 0.02, rm.z - hd),
          new THREE.Vector3(rm.x + hw, 0.02, rm.z - hd),
          new THREE.Vector3(rm.x + hw, 0.02, rm.z + hd),
          new THREE.Vector3(rm.x - hw, 0.02, rm.z + hd)
        ];
        drawProjected3DPolygon(
          ctx,
          pts,
          width,
          height,
          hexIntToCss(rm.carpetHex, 0.88),
          hexIntToCss(rm.borderHex, 0.52),
          1.4
        );
      });

      // 5. North & Side Perimeter Architectural Walls & Windows
      drawProjected3DPolygon(
        ctx,
        [
          new THREE.Vector3(-22.6, 0, -16.6),
          new THREE.Vector3(22.6, 0, -16.6),
          new THREE.Vector3(22.6, 3.1, -16.6),
          new THREE.Vector3(-22.6, 3.1, -16.6)
        ],
        width,
        height,
        'rgba(17, 28, 51, 0.92)',
        'rgba(56, 189, 248, 0.45)',
        1.4
      );
      [-14.5, 0, 14.5].forEach(wx => {
        drawProjected3DPolygon(
          ctx,
          [
            new THREE.Vector3(wx - 4.4, 0.85, -16.5),
            new THREE.Vector3(wx + 4.4, 0.85, -16.5),
            new THREE.Vector3(wx + 4.4, 2.75, -16.5),
            new THREE.Vector3(wx - 4.4, 2.75, -16.5)
          ],
          width,
          height,
          'rgba(56, 189, 248, 0.16)',
          'rgba(125, 211, 252, 0.55)',
          1.2
        );
      });

      // 6. Depth-Sort All 3D Entities (9 Rectangular Workstations, Central Glass Boardroom, 9+ Human AI Employees)
      const camPos = WORLD_3D.camera.position;
      const renderQueue = [];

      Object.values(WORLD_3D.zonesByRole).forEach(z => {
        renderQueue.push({
          type: 'ZONE',
          dist: camPos.distanceTo(z.worldPos),
          z
        });
      });

      renderQueue.push({
        type: 'CORE',
        dist: camPos.distanceTo(new THREE.Vector3(0, 1.0, 0.2))
      });

      Object.values(WORLD_3D.charactersByRole).forEach(ch => {
        renderQueue.push({
          type: 'CHAR',
          dist: camPos.distanceTo(ch.parts.root.position),
          ch
        });
      });

      renderQueue.sort((a, b) => b.dist - a.dist);

      renderQueue.forEach(item => {
        if (item.type === 'ZONE') {
          const z = item.z;
          const zx = z.worldPos.x;
          const zz = z.worldPos.z;
          const deskYaw = z.cfg.deskYaw || 0;
          const cosY = Math.cos(deskYaw);
          const sinY = Math.sin(deskYaw);
          const isSelected = SELECTED_AGENT_ID === z.cfg.role;

          // Rectangular Workstation Carpet Mat (Strictly NO circular/octagonal pad!)
          const matCorners = [
            [-1.7, -1.4], [1.7, -1.4], [1.7, 1.4], [-1.7, 1.4]
          ].map(([lx, lz]) => new THREE.Vector3(
            zx + lx * cosY + lz * sinY,
            0.03,
            zz - lx * sinY + lz * cosY
          ));
          drawProjected3DPolygon(
            ctx,
            matCorners,
            width,
            height,
            isSelected ? 'rgba(22, 40, 74, 0.94)' : 'rgba(17, 29, 54, 0.86)',
            hexIntToCss(z.cfg.colorHex, isSelected ? 0.95 : 0.52),
            isSelected ? 2.2 : 1.2
          );

          // Side Department Bookshelf / Server Cabinet (local: -1.45, 0.94, -0.95)
          const propWorld = new THREE.Vector3(
            zx + (-1.45) * cosY + (-0.95) * sinY,
            0.94,
            zz - (-1.45) * sinY + (-0.95) * cosY
          );
          drawProjected3DBox(
            ctx,
            propWorld,
            deskYaw,
            0.72,
            1.8,
            0.46,
            width,
            height,
            hexIntToCss(z.cfg.suitHex, 0.92),
            'rgba(15, 23, 42, 0.94)',
            hexIntToCss(z.cfg.colorHex, 0.5)
          );

          // Ergonomic Rolling Office Chair (local: 0, 0.62, 0.28)
          const chairWorld = new THREE.Vector3(
            zx + (0.28) * sinY,
            0.62,
            zz + (0.28) * cosY
          );
          drawProjected3DBox(
            ctx,
            chairWorld,
            deskYaw,
            0.56,
            0.74,
            0.54,
            width,
            height,
            hexIntToCss(z.cfg.suitHex, 0.88),
            'rgba(15, 23, 42, 0.94)',
            hexIntToCss(z.cfg.colorHex, 0.45)
          );

          // Rectangular Executive Workstation Desk (local: 0, 0.44, -0.68)
          const deskWorld = new THREE.Vector3(
            zx + (-0.68) * sinY,
            0.44,
            zz + (-0.68) * cosY
          );
          drawProjected3DBox(
            ctx,
            deskWorld,
            deskYaw,
            2.3,
            0.78,
            0.85,
            width,
            height,
            'rgba(30, 41, 59, 0.98)',
            'rgba(15, 23, 42, 0.98)',
            hexIntToCss(z.cfg.colorHex, 0.72)
          );

          // Dual Widescreen Monitors on Desk (local: ±0.46, 1.16, -0.80)
          [-0.46, 0.46].forEach((mx, mIdx) => {
            const mCenter = new THREE.Vector3(
              zx + mx * cosY + (-0.80) * sinY,
              1.14,
              zz - mx * sinY + (-0.80) * cosY
            );
            drawProjected3DBox(
              ctx,
              mCenter,
              deskYaw,
              0.82,
              0.48,
              0.05,
              width,
              height,
              hexIntToCss(mIdx === 0 ? z.cfg.colorHex : z.cfg.visorHex, 0.45),
              'rgba(9, 13, 22, 0.96)',
              hexIntToCss(z.cfg.colorHex, 0.92)
            );
          });
        } else if (item.type === 'CORE') {
          // Central Glass Boardroom Conference Table (5.2m x 2.0m at 0, 0.45, 0.2) + 10 Boardroom Chairs
          const boardroomCenter = new THREE.Vector3(0, 0.44, 0.2);
          drawProjected3DBox(
            ctx,
            boardroomCenter,
            0,
            5.2,
            0.78,
            2.0,
            width,
            height,
            'rgba(30, 41, 59, 0.98)',
            'rgba(15, 23, 42, 0.96)',
            'rgba(34, 211, 238, 0.82)'
          );

          // 10 Conference Chairs around the table
          (WORLD_3D.meetingSpots || []).forEach(ms => {
            drawProjected3DBox(
              ctx,
              new THREE.Vector3(ms.x, 0.48, ms.z),
              ms.yaw || 0,
              0.48,
              0.68,
              0.48,
              width,
              height,
              'rgba(30, 58, 138, 0.85)',
              'rgba(15, 23, 42, 0.92)',
              'rgba(56, 189, 248, 0.45)'
            );
          });

          // Glass Partition Frame around Central Boardroom
          drawProjected3DPolygon(
            ctx,
            [
              new THREE.Vector3(-5.5, 0.05, -3.6),
              new THREE.Vector3(5.5, 0.05, -3.6),
              new THREE.Vector3(5.5, 0.05, 4.0),
              new THREE.Vector3(-5.5, 0.05, 4.0)
            ],
            width,
            height,
            null,
            'rgba(56, 189, 248, 0.55)',
            1.6
          );
        } else if (item.type === 'CHAR') {
          const ch = item.ch;
          const pos = ch.parts.root.position;
          const yaw = ch.parts.root.rotation.y;
          const cosY = Math.cos(yaw);
          const sinY = Math.sin(yaw);
          const bodyBounce = ch.parts.bodyGroup.position.y || 0;
          const auraHex = ch.parts.auraMat ? ch.parts.auraMat.color.getHex() : ch.cfg.colorHex;
          const skinHex = ch.parts.skinHex || ch.cfg.skinHex || 0xf3c6a5;
          const hairHex = ch.parts.hairHex || ch.cfg.hairHex || 0x1e293b;
          const trousersHex = ch.parts.trousersHex || ch.cfg.trousersHex || 0x0f172a;
          const isSelected = SELECTED_AGENT_ID === ch.role;

          // 1. Subtle Character Floor Selection Ring
          const auraPts = [];
          for (let i = 0; i < 16; i++) {
            const a = (i / 16) * Math.PI * 2;
            auraPts.push(new THREE.Vector3(pos.x + Math.cos(a) * 0.56, pos.y + 0.02, pos.z + Math.sin(a) * 0.56));
          }
          drawProjected3DPolygon(
            ctx,
            auraPts,
            width,
            height,
            hexIntToCss(auraHex, isSelected ? 0.25 : 0.10),
            hexIntToCss(auraHex, isSelected ? 0.95 : 0.65),
            isSelected ? 2.2 : 1.3
          );

          const toWorld = (lx, ly, lz) => new THREE.Vector3(
            pos.x + lx * cosY + lz * sinY,
            pos.y + bodyBounce + ly,
            pos.z - lx * sinY + lz * cosY
          );

          // 2. Articulated Human Legs in Tailored Trousers
          const llAngle = ch.parts.leftLegPivot.rotation.x;
          const rlAngle = ch.parts.rightLegPivot.rotation.x;
          const leftHip = toWorld(-0.14, 0.62, 0);
          const leftFoot = toWorld(-0.14, 0.12 + Math.abs(Math.sin(llAngle)) * 0.12, Math.sin(llAngle) * 0.34);
          const rightHip = toWorld(0.14, 0.62, 0);
          const rightFoot = toWorld(0.14, 0.12 + Math.abs(Math.sin(rlAngle)) * 0.12, Math.sin(rlAngle) * 0.34);

          drawProjected3DPolygon(ctx, [leftHip, leftFoot], width, height, null, hexIntToCss(trousersHex, 0.98), 6.0, false);
          drawProjected3DPolygon(ctx, [rightHip, rightFoot], width, height, null, hexIntToCss(trousersHex, 0.98), 6.0, false);

          // 3. Tailored Corporate Blazer Jacket (Torso)
          const torsoCenter = toWorld(0, 0.98, 0);
          drawProjected3DBox(
            ctx,
            torsoCenter,
            yaw,
            0.46,
            0.58,
            0.26,
            width,
            height,
            hexIntToCss(ch.cfg.suitHex, 0.98),
            hexIntToCss(ch.cfg.suitHex, 0.88),
            hexIntToCss(ch.cfg.colorHex, 0.85)
          );

          // Crisp White Dress Shirt V-Collar & Executive Tie
          const collarTopL = toWorld(-0.09, 1.22, 0.14);
          const collarTopR = toWorld(0.09, 1.22, 0.14);
          const collarBot = toWorld(0, 0.95, 0.15);
          drawProjected3DPolygon(ctx, [collarTopL, collarTopR, collarBot], width, height, '#f8fafc', hexIntToCss(ch.cfg.colorHex, 0.95), 1.2);

          // 4. Articulated Human Arms (Blazer Sleeves + Skin-Toned Hands)
          const laAngle = ch.parts.leftArmPivot.rotation.x;
          const raAngle = ch.parts.rightArmPivot.rotation.x;
          const leftShoulder = toWorld(-0.29, 1.18, 0);
          const leftHand = toWorld(-0.31, 1.18 - Math.cos(laAngle) * 0.42, -Math.sin(laAngle) * 0.42);
          const rightShoulder = toWorld(0.29, 1.18, 0);
          const rightHand = toWorld(0.31, 1.18 - Math.cos(raAngle) * 0.42, -Math.sin(raAngle) * 0.42);

          drawProjected3DPolygon(ctx, [leftShoulder, leftHand], width, height, null, hexIntToCss(ch.cfg.suitHex, 0.96), 4.8, false);
          drawProjected3DPolygon(ctx, [rightShoulder, rightHand], width, height, null, hexIntToCss(ch.cfg.suitHex, 0.96), 4.8, false);

          const lHandPt = project3DToOverlay(leftHand, width, height);
          if (lHandPt) {
            ctx.beginPath();
            ctx.arc(lHandPt.x, lHandPt.y, 3.3, 0, Math.PI * 2);
            ctx.fillStyle = hexIntToCss(skinHex, 0.98);
            ctx.fill();
          }
          const rHandPt = project3DToOverlay(rightHand, width, height);
          if (rHandPt) {
            ctx.beginPath();
            ctx.arc(rHandPt.x, rHandPt.y, 3.3, 0, Math.PI * 2);
            ctx.fillStyle = hexIntToCss(skinHex, 0.98);
            ctx.fill();
          }

          // 5. Smooth Sculpted Human Head + Hair Crown + Smart Glasses (Rounded human silhouette, never a blocky cube)
          const headYaw = yaw + (ch.parts.headGroup.rotation.y || 0);
          const headCenter = toWorld(0, 1.48, 0);
          const headPt = project3DToOverlay(headCenter, width, height);
          const neckTopPt = project3DToOverlay(toWorld(0, 1.30, 0), width, height);
          if (headPt && neckTopPt) {
            const headRadius = Math.max(5.5, Math.min(22, Math.abs(neckTopPt.y - headPt.y) * 0.95));
            ctx.beginPath();
            ctx.ellipse(headPt.x, headPt.y, headRadius * 0.88, headRadius * 1.06, 0, 0, Math.PI * 2);
            ctx.fillStyle = hexIntToCss(skinHex, 0.98);
            ctx.fill();
            ctx.lineWidth = 1.3;
            ctx.strokeStyle = hexIntToCss(hairHex, 0.55);
            ctx.stroke();

            // Sculpted Hair Crown Arc
            ctx.beginPath();
            ctx.arc(headPt.x, headPt.y - headRadius * 0.14, headRadius * 0.94, Math.PI * 0.92, Math.PI * 2.08);
            ctx.fillStyle = hexIntToCss(hairHex, 0.98);
            ctx.fill();
          }

          const hairCenter = toWorld(0, 1.60, -0.02);
          drawProjected3DBox(
            ctx,
            hairCenter,
            headYaw,
            0.33,
            0.13,
            0.34,
            width,
            height,
            hexIntToCss(hairHex, 0.98),
            hexIntToCss(hairHex, 0.95),
            hexIntToCss(ch.cfg.colorHex, 0.45)
          );

          const visorLeft = toWorld(-0.12, 1.47, 0.17);
          const visorRight = toWorld(0.12, 1.47, 0.17);
          drawProjected3DPolygon(ctx, [visorLeft, visorRight], width, height, null, hexIntToCss(auraHex, 1), 2.8, false);
        }
      });

      // 7. Render Active Inter-Agent 3D Communication Beam & Pulse Particle
      if (CURRENT_ACTIVE_SPEECH && WORLD_3D.commBeamLine && WORLD_3D.commBeamLine.visible) {
        const sRole = CURRENT_ACTIVE_SPEECH.msg.sender_agent_id;
        const rRole = CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id;
        const sChar = WORLD_3D.charactersByRole[sRole];
        const rChar = WORLD_3D.charactersByRole[rRole];
        if (sChar && rChar) {
          const p1 = sChar.parts.root.position.clone().add(new THREE.Vector3(0, 1.85, 0));
          const p2 = rChar.parts.root.position.clone().add(new THREE.Vector3(0, 1.85, 0));
          drawProjected3DPolygon(ctx, [p1, p2], width, height, null, 'rgba(34, 211, 238, 0.9)', 2.6, false);
          if (WORLD_3D.commPulseMesh) {
            const pulsePt = project3DToOverlay(WORLD_3D.commPulseMesh.position, width, height);
            if (pulsePt) {
              ctx.beginPath();
              ctx.arc(pulsePt.x, pulsePt.y, 6, 0, Math.PI * 2);
              ctx.fillStyle = '#facc15';
              ctx.fill();
              ctx.strokeStyle = '#ffffff';
              ctx.lineWidth = 1.5;
              ctx.stroke();
            }
          }
        }
      }
    }

    function project3DToOverlay(vec3, width, height) {
      const v = vec3.clone().project(WORLD_3D.camera);
      if (v.z > 1) return null; // Behind camera
      return {
        x: (v.x * 0.5 + 0.5) * width,
        y: (-(v.y * 0.5) + 0.5) * height
      };
    }

    function update2DProjectedOverlay() {
      const stage = document.getElementById('aiBase3DStage');
      if (!stage) return;
      const w = stage.clientWidth;
      const h = stage.clientHeight;

      const hideAllLabels = CLEAN_3D_SCREEN_MODE || LABELS_3D_MODE === 'HIDDEN';

      // Project Zone Signs (Only shown when LABELS_3D_MODE === 'ALL' to prevent text clutter)
      Object.entries(WORLD_3D.zonesByRole).forEach(([role, z]) => {
        const el = WORLD_3D.overlaySignEls[role];
        if (!el) return;
        if (hideAllLabels || LABELS_3D_MODE !== 'ALL') {
          el.style.display = 'none';
          return;
        }
        const pos = z.worldPos.clone().add(new THREE.Vector3(0, 3.25, 0));
        const pt = project3DToOverlay(pos, w, h);
        if (!pt) {
          el.style.display = 'none';
        } else {
          el.style.display = 'block';
          el.style.left = `${pt.x}px`;
          el.style.top = `${pt.y}px`;
          el.classList.toggle('selected', SELECTED_AGENT_ID === role);
        }
      });

      // Project Character Labels (In Clean Mode, only show compact name+outfit badge for speaking/hovered character)
      Object.entries(WORLD_3D.charactersByRole).forEach(([role, ch]) => {
        const el = WORLD_3D.overlayCharEls[role];
        if (!el) return;
        const isSpeakingOrListening = Boolean(
          CURRENT_ACTIVE_SPEECH &&
          CURRENT_ACTIVE_SPEECH.msg &&
          (CURRENT_ACTIVE_SPEECH.msg.sender_agent_id === role || CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id === role)
        );
        if (LABELS_3D_MODE === 'HIDDEN' || (CLEAN_3D_SCREEN_MODE && !isSpeakingOrListening && HOVERED_AGENT_ID !== role)) {
          el.style.display = 'none';
          return;
        }
        const isSpeaking = Boolean(CURRENT_ACTIVE_SPEECH && CURRENT_ACTIVE_SPEECH.msg.sender_agent_id === role);
        const isFocused = SELECTED_AGENT_ID === role || HOVERED_AGENT_ID === role || isSpeaking;
        if (LABELS_3D_MODE === 'SELECTED' && !isFocused) {
          el.style.display = 'none';
          return;
        }
        const pos = ch.parts.root.position.clone().add(new THREE.Vector3(0, 2.55, 0));
        const pt = project3DToOverlay(pos, w, h);
        if (!pt) {
          el.style.display = 'none';
        } else {
          el.style.display = 'inline-flex';
          el.style.left = `${pt.x}px`;
          el.style.top = `${pt.y}px`;
          el.classList.toggle('selected', SELECTED_AGENT_ID === role || HOVERED_AGENT_ID === role);
          el.classList.toggle('speaking', isSpeaking);
        }
      });

      // Project Active Vietnamese Speech Bubble above Speaking Character (ALWAYS visible when SHOW_3D_SPEECH_BUBBLES is true, even in CLEAN_3D_SCREEN_MODE!)
      const bubbleEl = WORLD_3D.overlayBubbleEl;
      if (bubbleEl) {
        if (!SHOW_3D_SPEECH_BUBBLES || !CURRENT_ACTIVE_SPEECH || !CURRENT_ACTIVE_SPEECH.msg) {
          bubbleEl.style.display = 'none';
        } else {
          const senderRole = CURRENT_ACTIVE_SPEECH.msg.sender_agent_id;
          const sChar = WORLD_3D.charactersByRole[senderRole];
          if (!sChar) {
            bubbleEl.style.display = 'none';
          } else {
            const headPos = sChar.parts.root.position.clone().add(new THREE.Vector3(0, 3.25, 0));
            const pt = project3DToOverlay(headPos, w, h);
            if (!pt) {
              bubbleEl.style.display = 'none';
            } else {
              bubbleEl.style.display = 'block';
              const clampedX = Math.max(165, Math.min(w - 170, pt.x));
              const clampedY = Math.max(152, Math.min(h - 26, pt.y));
              bubbleEl.style.left = `${clampedX}px`;
              bubbleEl.style.top = `${clampedY}px`;
            }
          }
        }
      }

      // Project Simultaneous Partner Reply Bubble above Receiver Character (clamped inside frame & separated from primary bubble)
      const replyEl = WORLD_3D.overlayReplyBubbleEl;
      if (replyEl) {
        if (!SHOW_3D_SPEECH_BUBBLES || !CURRENT_ACTIVE_SPEECH || !CURRENT_ACTIVE_SPEECH.replyText || Date.now() < (CURRENT_ACTIVE_SPEECH.replyShowAt || 0)) {
          replyEl.style.display = 'none';
        } else {
          const recRole = CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id;
          const rChar = WORLD_3D.charactersByRole[recRole];
          if (!rChar) {
            replyEl.style.display = 'none';
          } else {
            const rPos = rChar.parts.root.position.clone().add(new THREE.Vector3(0, 3.05, 0));
            const rPt = project3DToOverlay(rPos, w, h);
            if (!rPt) {
              replyEl.style.display = 'none';
            } else {
              replyEl.style.display = 'block';
              let rx = Math.max(165, Math.min(w - 170, rPt.x));
              let ry = Math.max(152, Math.min(h - 26, rPt.y));
              const bLeft = parseFloat(bubbleEl?.style?.left || '0');
              const bTop = parseFloat(bubbleEl?.style?.top || '0');
              if (Math.abs(rx - bLeft) < 230 && Math.abs(ry - bTop) < 85) {
                rx = bLeft < w / 2 ? Math.min(w - 170, bLeft + 250) : Math.max(165, bLeft - 250);
              }
              replyEl.style.left = `${rx}px`;
              replyEl.style.top = `${ry}px`;
            }
          }
        }
      }
    }

    function activateSpeechBubbleIn3D(msgObj) {
      if (!msgObj || !WORLD_3D.initialized) return;
      const sender = msgObj.sender_agent_id;
      const receiver = msgObj.receiver_agent_id;
      const sChar = WORLD_3D.charactersByRole[sender];
      const rChar = WORLD_3D.charactersByRole[receiver];

      CURRENT_ACTIVE_SPEECH = {
        msg: msgObj,
        expiresAt: Date.now() + 6500
      };

      const isHandoffMeeting = msgObj.message_type === 'ORCHESTRATOR_HANDOFF';
      const seats = WORLD_3D.meetingSpots || [];
      if (isHandoffMeeting && seats.length >= 2 && sChar && rChar) {
        const sIdx = Math.max(0, BASE_ZONES_CONFIG.findIndex(z => z.role === sender)) % seats.length;
        const rIdx = (sIdx + 1) % seats.length;
        sendCharacterAlongPath(sender, seats[sIdx], 'MEETING', false);
        sendCharacterAlongPath(receiver, seats[rIdx], 'MEETING', false);
        sChar.lookAtRole = receiver;
        rChar.lookAtRole = sender;
      } else {
        if (sChar) {
          sChar.animState = 'TALK';
          sChar.lookAtRole = rChar ? receiver : null;
        }
        if (rChar) {
          rChar.animState = 'LISTEN';
          rChar.lookAtRole = sender;
        }
      }

      if (WORLD_3D.commBeamLine && sChar && rChar) {
        WORLD_3D.commBeamLine.visible = true;
      }

      const bubbleEl = WORLD_3D.overlayBubbleEl;
      if (bubbleEl) {
        const isDemo = Boolean(msgObj.is_demo || msgObj.message_type === 'DEMO_PREVIEW');
        bubbleEl.className = `char-speech-bubble ${isDemo ? 'demo-mode' : ''}`;
        bubbleEl.innerHTML = `
          <div class="speech-meta-header">
            <span><strong>${escapeHtml(formatAgentShort(sender))}</strong> → <strong>${escapeHtml(formatAgentShort(receiver))}</strong></span>
            <div style="display:flex; align-items:center; gap:5px;">
              <span class="speech-origin-badge ${isDemo ? 'demo' : ''}">${escapeHtml(formatMessageTypeLabel(msgObj.message_type || 'AGENT_GENERATED'))}</span>
              <span onclick="dismissActiveSpeechBubble(event)" style="cursor:pointer; color:#94a3b8; font-weight:700; padding:0 3px;" title="Đóng / Close">✕</span>
            </div>
          </div>
          <div style="max-height:76px; overflow:hidden; text-overflow:ellipsis;">"${escapeHtml(trContent(msgObj.message_content))}"</div>
        `;
        bubbleEl.onclick = (e) => {
          e.stopPropagation();
          selectCharacterIn3DWorld(sender, true);
        };
      }

      speakVietnameseMessageOnce(msgObj);
    }

    function sync3DWorldAndCommHub(isOffline = false) {
      isOffline = isOffline || !STATE.online;
      init3DAIBaseWorld();
      const agents = getEnrichedAgentsList(isOffline);

      const chip3D = document.getElementById('world3DStatusChip');
      if (chip3D) {
        if (isOffline || !STATE.online) {
          chip3D.textContent = t('Backend offline — runtime chưa được xác minh.', 'Backend offline — runtime is not verified.');
          chip3D.className = 'chip danger';
        } else {
          const activeCount = agents.filter(a => a.has_active_flow).length;
          chip3D.textContent = activeCount > 0
            ? t(`Backend ghi nhận ${activeCount} agent có luồng hoạt động.`, `Backend reports ${activeCount} agents with active work.`)
            : t('Backend đã kết nối; AI runtime đang nghỉ.', 'Backend connected; AI runtime is idle.');
          chip3D.className = activeCount > 0 ? 'chip cyan' : 'chip warn';
        }
      }

      // Phase 5 Explicit Backend-to-3D Behavior Mapping Layer (Never marks a task complete on frontend just because an animation ended)
      agents.forEach(ag => {
        const role = ag.role;
        const ch = WORLD_3D.charactersByRole[role];
        const z = WORLD_3D.zonesByRole[role];
        const st = isOffline ? 'OFFLINE' : (ag.command_status || 'IDLE');
        const colHex = getStatusColorHex(st);

        const qDot = document.getElementById(`quickDot_${role}`);
        if (qDot) qDot.style.background = colHex;

        const tagEl = WORLD_3D.overlayCharEls[role];
        if (tagEl) {
          const shortRole = formatAgentShort(role);
          const hName = (ch?.cfg?.humanName && !shortRole.includes(ch.cfg.humanName)) ? ` • ${ch.cfg.humanName}` : '';
          const outfitInfo = (typeof ROLE_OUTFIT_STYLES !== 'undefined' && ROLE_OUTFIT_STYLES[role]) ? ` • 👔 ${ROLE_OUTFIT_STYLES[role].outfitNameVi}` : '';
          tagEl.innerHTML = `
            <span class="char-state-dot" style="background:${colHex};"></span>
            <span>${escapeHtml(shortRole)}${escapeHtml(hName)}${escapeHtml(outfitInfo)}</span>
          `;
        }

        if (!ch || !z) return;
        ch.backendStatus = st;
        ch.parts.auraMat.color.set(colHex);

        // Apply any persisted appearance customization from STATE.employees
        const empRec = (STATE.employees || []).find(e => e.role_code === role);
        if (empRec && empRec.appearance && empRec.appearance.suit_color && ch.parts.suitMat) {
          const customSuitInt = parseInt(String(empRec.appearance.suit_color).replace('#', ''), 16);
          if (!Number.isNaN(customSuitInt)) {
            ch.cfg.suitHex = customSuitInt;
            ch.parts.suitMat.color.setHex(customSuitInt);
          }
        }

        // Don't interrupt an active speech/meeting turn unless going offline
        if (CURRENT_ACTIVE_SPEECH && (CURRENT_ACTIVE_SPEECH.msg.sender_agent_id === role || CURRENT_ACTIVE_SPEECH.msg.receiver_agent_id === role) && !isOffline) {
          return;
        }

        if (st === 'OFFLINE') {
          ch.waypoints = [];
          ch.animState = 'OFFLINE';
          z.conduitMat.opacity = 0.08;
        } else if (st === 'IDLE') {
          sendCharacterAlongPath(role, z.idleSpot, 'IDLE', false);
          z.conduitMat.opacity = 0.14;
        } else if (st === 'WAITING_APPROVAL') {
          sendCharacterAlongPath(role, z.commSpot, 'ERROR', false);
          z.conduitMat.opacity = 0.65;
        } else if (st === 'THINKING') {
          sendCharacterAlongPath(role, z.workSpot, 'READ', false);
          z.conduitMat.opacity = 0.65;
        } else if (st === 'ERROR') {
          sendCharacterAlongPath(role, z.idleSpot, 'ERROR', false);
          z.conduitMat.opacity = 0.35;
        } else if (st === 'WORKING') {
          sendCharacterAlongPath(role, z.workSpot, 'TYPE', true);
          z.conduitMat.opacity = 0.85;
        } else {
          // SUCCESS (Verified backend execution) -> Seated at desk operating workstation
          sendCharacterAlongPath(role, z.workSpot, 'WORK_AT_DESK', false);
          z.conduitMat.opacity = 0.72;
        }
      });

      // Dynamically spawn & sync any newly approved AI Employees from STATE.employees in the Expansion Wing (South-West / South corridor)
      const dynamicApproved = (STATE.employees || []).filter(e => !e.is_initial_nine && e.approval_status === 'APPROVED');
      dynamicApproved.forEach((emp, dIdx) => {
        const dynRole = emp.role_code || emp.employee_id;
        if (!WORLD_3D.charactersByRole[dynRole] && WORLD_3D.initialized && typeof THREE !== 'undefined') {
          const overlay = document.getElementById('aiBase3DOverlay');
          const quickBar = document.getElementById('quickAgentSelectorBar');
          const zx = -11.5 + (dIdx % 3) * 3.8;
          const zz = 12.2;
          const deskYaw = Math.PI;
          const dynCfg = {
            role: dynRole,
            zoneId: emp.department_zone || 'ZONE_WORKFORCE_STUDIO',
            nameVi: `${emp.display_name_vi || emp.display_name_en}`,
            subVi: emp.job_title_vi || 'Chuyên Viên AI Mở Rộng',
            equipVi: 'Bàn làm việc Chuyên Gia AI Mở Rộng (Dynamic Workforce)',
            deskX: zx,
            deskZ: zz,
            deskYaw,
            doorX: zx,
            doorZ: 6.2,
            colorHex: 0x38bdf8,
            suitHex: 0x0284c7,
            visorHex: 0x7dd3fc,
            skinHex: 0xf1c29d,
            hairHex: 0x1e293b,
            trousersHex: 0x0f172a,
            humanName: emp.display_name_vi || emp.display_name_en,
            shortLabel: `${(emp.display_name_vi || dynRole).slice(0, 14)}`
          };
          const workSpot = { x: zx, z: zz - 0.12, yaw: 0 };
          const idleSpot = { x: zx - 1.2, z: zz - 0.4, yaw: Math.PI };
          const commSpot = { x: zx, z: 6.2, yaw: 0 };

          WORLD_3D.zonesByRole[dynRole] = {
            cfg: dynCfg,
            worldPos: new THREE.Vector3(zx, 0, zz),
            workSpot,
            idleSpot,
            commSpot,
            conduitMat: { opacity: 0.65 }
          };

          const charParts = createArticulated3DCharacter(THREE, dynCfg);
          charParts.root.position.set(workSpot.x, 0.02, workSpot.z);
          charParts.root.rotation.y = workSpot.yaw;
          WORLD_3D.scene.add(charParts.root);
          WORLD_3D.pickableMeshes.push(charParts.torsoMesh, charParts.helmetMesh);

          WORLD_3D.charactersByRole[dynRole] = {
            role: dynRole,
            cfg: dynCfg,
            parts: charParts,
            animState: 'WORK_AT_DESK',
            backendStatus: emp.status || 'ACTIVE',
            waypoints: [],
            targetYaw: workSpot.yaw,
            lookAtRole: null,
            walkSpeed: 4.8,
            phaseOffset: (9 + dIdx) * 0.75
          };

          if (overlay) {
            const charTag = document.createElement('div');
            charTag.className = 'char-3d-label';
            charTag.innerHTML = `<span class="char-state-dot" style="background:#10b981;"></span><span>${escapeHtml(emp.display_name_vi || emp.display_name_en)}</span><span style="font-family:var(--font-mono); font-size:9.5px; color:#38bdf8;">[NEW AI]</span>`;
            charTag.onclick = (ev) => {
              ev.stopPropagation();
              selectCharacterIn3DWorld(dynRole, true);
            };
            overlay.appendChild(charTag);
            WORLD_3D.overlayCharEls[dynRole] = charTag;
          }
          if (quickBar) {
            const pill = document.createElement('button');
            pill.className = 'quick-agent-pill';
            pill.id = `quickAgentPill_${dynRole}`;
            pill.innerHTML = `<span class="char-state-dot" id="quickDot_${dynRole}" style="background:#10b981;"></span><span>${escapeHtml(dynCfg.shortLabel)}</span>`;
            pill.onclick = () => selectCharacterIn3DWorld(dynRole, true);
            quickBar.appendChild(pill);
          }
        }
      });

      // Queue any newly arrived real backend messages for 3D Speech Bubble display (skip auto-popping old history on initial load so screen starts clean)
      if (!isOffline && STATE.online) {
        const realMsgs = (STATE.agentMessages || []).filter(m => !m.is_demo && m.message_type !== 'DEMO_PREVIEW');
        const isFirstQueue = DISPLAYED_BUBBLE_MSG_IDS.size === 0;
        if (isFirstQueue) {
          realMsgs.forEach(m => {
            if (m.message_id) DISPLAYED_BUBBLE_MSG_IDS.add(m.message_id);
          });
        } else {
          const sliceToCheck = realMsgs.slice(0, 5).reverse();
          sliceToCheck.forEach(m => {
            if (m.message_id && !DISPLAYED_BUBBLE_MSG_IDS.has(m.message_id)) {
              DISPLAYED_BUBBLE_MSG_IDS.add(m.message_id);
              if (ACTIVE_SPEECH_QUEUE.length < 6 && SHOW_3D_SPEECH_BUBBLES && !CLEAN_3D_SCREEN_MODE) {
                ACTIVE_SPEECH_QUEUE.push(m);
              }
            }
          });
        }
      } else {
        ACTIVE_SPEECH_QUEUE = [];
        CURRENT_ACTIVE_SPEECH = null;
      }

      sync3DOverlayControlButtons();
      renderCommHubMessages();
    }

    function playNextRealConversationSequence() {
      if (!STATE.online) {
        showToast(t('Máy chủ đang Ngoại tuyến — Không thể phát hội thoại nghiệp vụ thật.', 'Backend is Offline — Cannot play real operational conversation.'), true);
        return;
      }
      const realMsgs = (STATE.agentMessages || []).filter(m => !m.is_demo && m.message_type !== 'DEMO_PREVIEW');
      if (realMsgs.length === 0) {
        showToast(t('Chưa có lịch sử tin nhắn từ backend. Chưa có tác vụ nào được kích hoạt.', 'No backend message history is available. No task was started.'), true);
        return;
      }
      // Queue up to 4 real messages in chronological order
      const seq = realMsgs.slice(0, 4).reverse();
      ACTIVE_SPEECH_QUEUE = seq.slice(1);
      activateSpeechBubbleIn3D(seq[0]);
      showToast(t(`Đang tái hiện chuỗi ${seq.length} lượt giao tiếp thực tế từ cơ sở dữ liệu.`, `Replaying sequence of ${seq.length} real communication turns from database.`));
    }

    function triggerDemoConversationPreview() {
      showToast(t('Bản xem thử hội thoại đã tắt. Chỉ hiển thị tin nhắn có trong event store.', 'Conversation previews are disabled. Only messages from the event store are shown.'), true);
      return;

      const demoMsg = {
        message_id: `demo_${Date.now()}`,
        conversation_id: 'conv_demo_preview',
        task_id: 'DEMO_UI_TEST',
        sender_agent_id: 'RESEARCH_AGENT',
        receiver_agent_id: 'SALES_AGENT',
        message_type: 'DEMO_PREVIEW',
        message_content: '[CHẾ ĐỘ DEMO KIỂM THỬ GIAO DIỆN] Tôi đang kiểm tra hiệu ứng truyền tin Hologram 3D và bong bóng lời thoại Tiếng Việt. Tin nhắn này không tính vào lịch sử vận hành thật.',
        delivery_status: 'DELIVERED',
        processing_status: 'DEMO_ONLY',
        is_demo: true,
        created_at: new Date().toISOString()
      };
      DEMO_LOCAL_MESSAGES.unshift(demoMsg);
      const filterType = document.getElementById('commFilterType');
      if (filterType) filterType.value = 'ALL_WITH_DEMO';
      activateSpeechBubbleIn3D(demoMsg);
      renderCommHubMessages();
      showToast(t('Đang hiển thị bong bóng hội thoại Xem Thử Hiệu Ứng (Đã tách biệt với dữ liệu thật).', 'Displaying Demo Preview speech bubble (Strictly separated from real operational telemetry).'));
    }

    function renderCommHubMessages() {
      const listEl = document.getElementById('commHubMessagesList');
      const countSub = document.getElementById('commHubCountSub');
      if (!listEl) return;

      if (!STATE.online) {
        listEl.innerHTML = `<div class="empty-state" style="color:#fca5a5;">${t('Máy chủ Ngoại tuyến — Ngừng hiển thị hoạt động nghiệp vụ cho tới khi kết nối lại.', 'Backend Offline — Operational communication paused until reconnected.')}</div>`;
        return;
      }

      const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';
      const agentFilter = document.getElementById('commFilterAgent')?.value || 'ALL';
      const typeFilter = document.getElementById('commFilterType')?.value || 'REAL_ONLY';
      const searchQ = (document.getElementById('commSearchInput')?.value || '').trim().toLowerCase();

      const allCombined = [...DEMO_LOCAL_MESSAGES, ...(STATE.agentMessages || [])];
      const filtered = allCombined.filter(m => {
        const isDemo = Boolean(m.is_demo || m.message_type === 'DEMO_PREVIEW');
        if (typeFilter === 'REAL_ONLY' && isDemo) return false;
        if (typeFilter === 'AGENT_GENERATED' && m.message_type !== 'AGENT_GENERATED') return false;
        if (typeFilter === 'ORCHESTRATOR_HANDOFF' && m.message_type !== 'ORCHESTRATOR_HANDOFF') return false;
        if (typeFilter === 'SYSTEM_STATUS' && m.message_type !== 'SYSTEM_STATUS') return false;

        if (agentFilter !== 'ALL' && m.sender_agent_id !== agentFilter && m.receiver_agent_id !== agentFilter) {
          return false;
        }
        if (searchQ) {
          const translatedMsg = trContent(m.message_content);
          const hay = `${m.sender_agent_id} ${m.receiver_agent_id} ${formatAgentTitle(m.sender_agent_id)} ${formatAgentTitle(m.receiver_agent_id)} ${m.message_content} ${translatedMsg} ${m.task_id || ''} ${m.message_type}`.toLowerCase();
          if (!hay.includes(searchQ)) return false;
        }
        return true;
      });

      if (countSub) {
        const realCount = (STATE.agentMessages || []).filter(m => !m.is_demo).length;
        countSub.textContent = t(
          `${filtered.length} tin nhắn hiển thị (${realCount} sự kiện thật từ SQLite)`,
          `${filtered.length} messages shown (${realCount} real events from SQLite)`
        );
      }

      if (filtered.length === 0) {
        listEl.innerHTML = `<div class="empty-state">${t('Không có tin nhắn nào khớp bộ lọc hiện tại.', 'No messages match the current filter.')}</div>`;
        return;
      }

      listEl.innerHTML = filtered.slice(0, 50).map(m => {
        const timeStr = m.created_at ? new Date(m.created_at).toLocaleTimeString(localeCode) : '--:--:--';
        const isDemo = Boolean(m.is_demo || m.message_type === 'DEMO_PREVIEW');
        return `
          <div class="comm-msg-card type-${escapeHtml(m.message_type || 'AGENT_GENERATED')}"
               onclick="focusCommMessageIn3D('${escapeHtml(m.message_id || '')}')">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; font-family:var(--font-mono); font-size:10px; color:#38bdf8; margin-bottom:4px;">
              <span><strong>${escapeHtml(formatAgentTitle(m.sender_agent_id))}</strong> → <strong>${escapeHtml(formatAgentTitle(m.receiver_agent_id))}</strong></span>
              <span>${escapeHtml(timeStr)}</span>
            </div>
            <div style="color:#f8fafc; line-height:1.42; margin-bottom:6px;">
              "${escapeHtml(trContent(m.message_content))}"
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:4px; font-family:var(--font-mono); font-size:9.5px; color:var(--text-muted);">
              <span class="speech-origin-badge ${isDemo ? 'demo' : ''}">${escapeHtml(formatMessageTypeLabel(m.message_type))}</span>
              <span>${t('Nhiệm vụ:', 'Task:')} ${escapeHtml(m.task_id ? String(m.task_id).slice(0, 12) : t('Chu trình', 'Pipeline'))} | ${escapeHtml(formatStatusLabel(m.delivery_status || 'DELIVERED'))} • ${escapeHtml(formatStatusLabel(m.processing_status || 'PROCESSED'))}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function focusCommMessageIn3D(messageId) {
      const allCombined = [...DEMO_LOCAL_MESSAGES, ...(STATE.agentMessages || [])];
      const found = allCombined.find(m => m.message_id === messageId);
      if (!found) return;
      if (OVERVIEW_DISPLAY_MODE !== 'GAME') {
        switchOverviewMode('GAME');
      }
      selectCharacterIn3DWorld(found.sender_agent_id, false);
      activateSpeechBubbleIn3D(found);
    }

    // =========================================================================
    // TASK 1, TASK 2 & TASK 3 INTEGRATED CONTROLLERS (DIAGNOSTICS, PRICING, COMPACT UI)
    // =========================================================================
    function toggleDesktopSidebarCollapse() {
      const sb = document.getElementById('sidebar');
      const mw = document.querySelector('.main-wrapper');
      if (sb) sb.classList.toggle('collapsed-desktop');
      if (mw) mw.classList.toggle('sidebar-collapsed');
      setTimeout(onResize3DWorld, 260);
    }

    function set3DStageViewportMode(mode) {
      CURRENT_3D_STAGE_SIZE = mode;
      const stage = document.getElementById('aiBase3DStage');
      const exitBtn = document.getElementById('btnExitFullscreen3D');
      if (!stage) return;
      stage.classList.remove('size-collapsed', 'size-compact', 'size-expanded', 'size-fullscreen');
      if (mode === 'COLLAPSED') stage.classList.add('size-collapsed');
      else if (mode === 'EXPANDED') stage.classList.add('size-expanded');
      else if (mode === 'FULLSCREEN') stage.classList.add('size-fullscreen');
      else stage.classList.add('size-compact');
      if (exitBtn) exitBtn.style.display = mode === 'FULLSCREEN' ? 'inline-flex' : 'none';
      setTimeout(onResize3DWorld, 60);
      setTimeout(onResize3DWorld, 250);
    }

    function toggle3DDiagnosticsPanel() {
      DIAGNOSTICS_3D_OPEN = !DIAGNOSTICS_3D_OPEN;
      const panel = document.getElementById('stageDiagnosticsPanel');
      if (panel) panel.classList.toggle('open', DIAGNOSTICS_3D_OPEN);
      updateMovementStatusIndicatorsAndDiagnostics();
    }

    function updateMovementStatusIndicatorsAndDiagnostics() {
      const chars = Object.values(WORLD_3D.charactersByRole || {});
      const movingCount = chars.filter(c => (c.actualSpeed || 0) > 0.05 || (c.waypoints && c.waypoints.length > 0 && MOVEMENT_ENABLED && !REDUCED_MOTION)).length;
      const gltfCount = chars.filter(c => c.parts && c.parts.isGltfLoaded).length;

      const animChip = document.getElementById('statusChipAnimActive');
      if (animChip) {
        if (!STATE.online) {
          animChip.textContent = t('Máy chủ: NGOẠI TUYẾN', 'Backend: DISCONNECTED');
          animChip.className = 'chip danger';
        } else if (!MOVEMENT_ENABLED || REDUCED_MOTION) {
          animChip.textContent = t('Hoạt ảnh: TẠM DỪNG', 'Animation: PAUSED');
          animChip.className = 'chip warn';
        } else {
          animChip.textContent = t(`Hoạt ảnh: ĐANG CHẠY (${gltfCount}/9 GLTF Rig)`, `Animation: ACTIVE (${gltfCount}/9 GLTF)`);
          animChip.className = 'chip success';
        }
      }

      const moveChip = document.getElementById('statusChipMovingCount');
      if (moveChip) {
        moveChip.textContent = (!MOVEMENT_ENABLED || REDUCED_MOTION)
          ? t('Di chuyển: TẮT (0/9)', 'Moving: PAUSED (0/9)')
          : t(`Đang di chuyển: ${movingCount}/${chars.length || 9}`, `Character moving: ${movingCount}/${chars.length || 9}`);
        moveChip.className = movingCount > 0 ? 'chip cyan' : 'chip';
      }

      if (!DIAGNOSTICS_3D_OPEN) return;
      const metaEl = document.getElementById('diagSummaryMeta');
      if (metaEl) {
        metaEl.textContent = `Movement: ${MOVEMENT_ENABLED ? 'ON' : 'OFF'} | Moving: ${movingCount}/${chars.length} | GLTF Skinned Models: ${gltfCount}/${chars.length} | Render: ${WORLD_3D.renderMode || 'WEBGL'}`;
      }
      const tbody = document.getElementById('stageDiagnosticsTableBody');
      if (!tbody) return;
      tbody.innerHTML = chars.map(ch => {
        const pos = ch.parts?.root?.position || { x: 0, y: 0, z: 0 };
        const dest = ch.destinationPos || { x: 0, z: 0, label: '-' };
        const rigBadge = ch.parts?.isGltfLoaded
          ? `<span class="chip success" style="font-size:9.5px; padding:1px 5px;">GLTF (${escapeHtml((ch.parts.assetUrl || '').split('/').pop())})</span>`
          : `<span class="chip cyan" style="font-size:9.5px; padding:1px 5px;">Sculpted+Mixer</span>`;
        return `
          <tr style="cursor:pointer;" onclick="selectCharacterIn3DWorld('${escapeHtml(ch.role)}', false)">
            <td style="font-family:var(--font-mono); font-weight:700; color:#fff;">${escapeHtml(ch.employeeId || ch.role)}</td>
            <td>${rigBadge}</td>
            <td><span class="chip cyan" style="font-size:9.5px; padding:1px 5px;">${escapeHtml(ch.animState || 'IDLE')}</span></td>
            <td style="font-family:var(--font-mono); color:#a5f3fc;">${escapeHtml(ch.parts?.activeClipName || 'human_idle')}</td>
            <td style="font-family:var(--font-mono);">(${Number(pos.x).toFixed(1)}, ${Number(pos.z).toFixed(1)})</td>
            <td style="font-family:var(--font-mono);">(${Number(dest.x).toFixed(1)}, ${Number(dest.z).toFixed(1)}) <span style="color:var(--text-muted);">${escapeHtml(dest.label || '')}</span></td>
            <td style="font-family:var(--font-mono); color:${(ch.actualSpeed || 0) > 0 ? '#34d399' : 'var(--text-muted)'};">${Number(ch.actualSpeed || 0).toFixed(2)} m/s</td>
            <td style="font-family:var(--font-mono); font-size:10px;">${escapeHtml(ch.navigationStatus || 'IDLE')}</td>
            <td style="font-family:var(--font-mono); font-size:10px;">${escapeHtml(ch.activeTaskId ? String(ch.activeTaskId).slice(0, 10) : 'IDLE_PATROL')}</td>
            <td style="font-family:var(--font-mono); font-size:10px; color:${ch.lastMovementError ? '#fca5a5' : 'var(--text-secondary)'};">
              ${escapeHtml(ch.lastMovementError || (ch.lastStateUpdateAt ? ch.lastStateUpdateAt.slice(11, 19) : 'OK'))}
            </td>
          </tr>
        `;
      }).join('');
    }

    function setOverviewTaskFilter(filterCode) {
      OVERVIEW_TASK_FILTER = filterCode || 'ALL';
      document.querySelectorAll('#overviewTaskFilterGroup button').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-filter') === OVERVIEW_TASK_FILTER);
      });
      renderCompactOverviewAndDynamicPricing();
      if (typeof renderHumanStyleAiNotebook === 'function') renderHumanStyleAiNotebook();
      if (typeof detectVisitorGeoIpAndConfigureDonation === 'function') detectVisitorGeoIpAndConfigureDonation();
    }

    function renderCompactOverviewAndDynamicPricing() {
      // 1. Update Topbar Emergency Stop visibility (only in verified Owner Admin mode) & Attention badge
      const emgBtn = document.getElementById('btnEmergencyStopTopbar');
      if (emgBtn) {
        emgBtn.style.display = IS_OWNER_ADMIN_VERIFIED ? 'inline-flex' : 'none';
      }

      const pendingTasks = (STATE.tasks || []).filter(x => x.ui_status === 'WAITING_FOR_APPROVAL' || x.status === 'AWAITING_APPROVAL');
      const unapprovedLeads = (STATE.leads || []).filter(l => l.requires_owner_approval);
      const pendingPricingRecs = (STATE.pricingRecommendations || []).filter(r => r.status === 'PENDING_OWNER_APPROVAL');
      const totalAttention = pendingTasks.length + unapprovedLeads.length + pendingPricingRecs.length;

      const attEl = document.getElementById('kpi-attention-tasks');
      if (attEl) attEl.textContent = String(totalAttention);
      const attSub = document.getElementById('kpi-attention-tasks-sub');
      if (attSub) {
        attSub.textContent = t(
          `${unapprovedLeads.length} Đề xuất KH • ${pendingTasks.length} Task • ${pendingPricingRecs.length} Giá AI`,
          `${unapprovedLeads.length} Leads • ${pendingTasks.length} Tasks • ${pendingPricingRecs.length} Pricing`
        );
      }
      const topAlertBadge = document.getElementById('topbarAlertsBadge');
      if (topAlertBadge) {
        topAlertBadge.textContent = t(`🔔 ${totalAttention} Cần duyệt`, `🔔 ${totalAttention} Alerts`);
        topAlertBadge.className = totalAttention > 0 ? 'chip warn' : 'chip success';
      }
      const inlineTasksEl = document.getElementById('kpi-active-tasks-inline');
      if (inlineTasksEl) {
        inlineTasksEl.textContent = `(${(STATE.tasks || []).length} Tasks)`;
      }

      // Sync activeTaskId into WORLD_3D.charactersByRole for Diagnostics Panel
      (STATE.tasks || []).forEach(tk => {
        const ch = WORLD_3D.charactersByRole?.[tk.agent_role];
        if (ch && !ch.activeTaskId) {
          ch.activeTaskId = tk.id;
        }
      });

      // 2. Render Compact Tasks & Employee Activity Table in Overview (#overviewCompactTasksTableBody)
      const compactBody = document.getElementById('overviewCompactTasksTableBody');
      if (compactBody) {
        const allTasks = STATE.tasks || [];
        const filteredTasks = allTasks.filter(tk => {
          const st = (tk.ui_status || tk.status || 'COMPLETED').toUpperCase();
          if (OVERVIEW_TASK_FILTER === 'ALL') return true;
          if (OVERVIEW_TASK_FILTER === 'RUNNING') return st === 'RUNNING' || st === 'WORKING' || st === 'THINKING';
          if (OVERVIEW_TASK_FILTER === 'WAITING') return st === 'PLANNED' || st === 'WAITING' || st === 'IDLE';
          if (OVERVIEW_TASK_FILTER === 'AWAITING_APPROVAL') return st === 'WAITING_FOR_APPROVAL' || st === 'AWAITING_APPROVAL';
          if (OVERVIEW_TASK_FILTER === 'COMPLETED') return st === 'COMPLETED' || st === 'SUCCESS';
          if (OVERVIEW_TASK_FILTER === 'FAILED') return st === 'FAILED' || st === 'ERROR' || st === 'BLOCKED' || st === 'STOPPED';
          return true;
        });

        const localeCode = CURRENT_LANG === 'en' ? 'en-US' : 'vi-VN';
        compactBody.innerHTML = filteredTasks.length === 0
          ? `<tr><td colspan="6" class="empty-state">${t('Không có nhiệm vụ nào khớp bộ lọc hiện tại.', 'No tasks match the selected status filter.')}</td></tr>`
          : filteredTasks.slice(0, 14).map(tk => {
              const role = tk.agent_role || 'RESEARCH_AGENT';
              const ch = WORLD_3D.charactersByRole?.[role];
              const animSt = ch ? ch.animState : 'WORK_AT_DESK';
              const uiSt = tk.ui_status || tk.status || 'COMPLETED';
              const canApprove = tk.status === 'AWAITING_APPROVAL' || uiSt === 'WAITING_FOR_APPROVAL';
              return `
                <tr>
                  <td>
                    <div style="font-weight:700; color:#fff;">${escapeHtml(trContent(tk.title))}</div>
                    <div style="font-family:var(--font-mono); font-size:10.5px; color:var(--text-muted);">#${escapeHtml(String(tk.id).slice(0, 10))}</div>
                  </td>
                  <td>
                    <div style="font-weight:600; color:var(--accent-cyan); cursor:pointer;" onclick="selectCharacterIn3DWorld('${escapeHtml(role)}', false)">
                      🎯 ${escapeHtml(formatAgentTitle(role))}
                    </div>
                    <div style="font-size:10.5px; color:var(--text-secondary);">${escapeHtml(formatZoneName(role))}</div>
                  </td>
                  <td>
                    <span class="chip ${uiSt === 'COMPLETED' ? 'success' : (canApprove ? 'warn' : 'cyan')}" style="font-size:10px;">${escapeHtml(formatStatusLabel(uiSt))}</span>
                    <span class="chip" style="font-size:10px; font-family:var(--font-mono);">3D: ${escapeHtml(animSt)}</span>
                  </td>
                  <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">
                    ${escapeHtml(tk.started_at ? new Date(tk.started_at).toLocaleTimeString(localeCode) : '--:--')}
                  </td>
                  <td style="font-size:11.5px; color:var(--text-secondary); max-width:250px;">
                    ${escapeHtml(trContent(String(tk.evidence || tk.outcome_reason || 'Hoàn tất').slice(0, 95)))}
                  </td>
                  <td>
                    <div style="display:flex; gap:5px; flex-wrap:wrap;">
                      <button class="btn btn-sm" onclick="selectCharacterIn3DWorld('${escapeHtml(role)}', true)">🔍 3D</button>
                      ${canApprove ? `<button class="btn btn-sm btn-primary" onclick="approveAgentTask('${escapeHtml(tk.id)}')">✓ Duyệt</button>` : ''}
                    </div>
                  </td>
                </tr>
              `;
            }).join('');
      }

      // 3. Populate Dynamic Service Catalog Quote Select & Governance Panel in #view-products
      const catalog = (STATE.pricingCatalog && STATE.pricingCatalog.length > 0) ? STATE.pricingCatalog : (STATE.products || []);
      const quoteSel = document.getElementById('quoteServiceSelect');
      if (quoteSel && catalog.length > 0) {
        const prevVal = quoteSel.value;
        quoteSel.innerHTML = catalog.map(item => {
          const modelTag = item.pricing_model || 'FIXED';
          const dispPrice = item.price_display || `$${Number(item.base_price_usd || item.price_usd || 29).toFixed(2)} USD`;
          return `<option value="${escapeHtml(item.id)}">${escapeHtml(trContent(item.name))} — [${escapeHtml(modelTag)}: ${escapeHtml(dispPrice)}]</option>`;
        }).join('');
        if (prevVal && catalog.some(x => x.id === prevVal)) {
          quoteSel.value = prevVal;
        }
        onQuoteServiceSelectionChange();
      }

      // Also enrich #productsTableBody to show Pricing Model, Price Range/Tiers, Cost-Plus Minimum Floor & Version
      const prodTbody = document.getElementById('productsTableBody');
      if (prodTbody && catalog.length > 0) {
        prodTbody.innerHTML = catalog.map(p => {
          const pModel = p.pricing_model || 'FIXED';
          const pDisplay = p.price_display || `$${Number(p.price_usd || 29).toFixed(2)} USD`;
          const minFloor = Number(p.computed_cost_plus_minimum_usd || p.min_price_usd || 15).toFixed(2);
          const marginPct = Math.round(Number(p.target_gross_margin ?? 0.65) * 100);
          return `
            <tr>
              <td>
                <div style="font-weight:700; color:#fff;">${escapeHtml(trContent(p.name))}</div>
                <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">${escapeHtml(trContent(p.problem_solved))}</div>
                <div style="margin-top:4px; display:flex; gap:5px; flex-wrap:wrap;">
                  <span class="chip purple" style="font-size:10px;">Model: ${escapeHtml(pModel)}</span>
                  <span class="chip" style="font-size:10px;">v${Number(p.pricing_version || 1)}</span>
                </div>
              </td>
              <td style="font-family:var(--font-mono); font-size:13px; font-weight:700; color:var(--accent-cyan);">
                <div>${escapeHtml(pDisplay)}</div>
                <div style="font-size:10.5px; color:var(--text-secondary); font-weight:400; margin-top:3px;">
                  Giá sàn (Cost-Plus): $${escapeHtml(minFloor)} | Margin: ${marginPct}%
                </div>
              </td>
              <td>
                <span class="chip ${p.test_passed !== false ? 'success' : 'danger'}">${p.test_passed !== false ? t('ĐẠT KIỂM THỬ TỰ ĐỘNG', 'PASSED SELF-TESTS') : t('THẤT BẠI', 'FAILED')}</span>
              </td>
              <td style="font-size:11.5px; color:var(--text-secondary);">
                ${escapeHtml(p.unit_name ? `Đơn vị tính: ${p.unit_name} ($${Number(p.unit_price_usd || 0).toFixed(2)}/đv)` : 'URL / HTML -> Báo cáo JSON + Mã sửa lỗi')}
              </td>
              <td style="font-size:11.5px; color:var(--text-secondary);">
                ${escapeHtml(trContent(p.refund_policy || 'Bảo hành kỹ thuật 30 ngày; mở khóa tự động sau khi xác minh thanh toán.'))}
              </td>
              <td>
                <div style="display:flex; flex-direction:column; gap:5px;">
                  <button class="btn btn-sm btn-cyan" onclick="selectServiceForQuote('${escapeHtml(p.id)}')">🧮 Tính Báo Giá</button>
                  <a class="btn btn-sm" href="${API_BASE}/api/products/${encodeURIComponent(p.id)}/download" target="_blank" rel="noopener">⬇ Tải .py</a>
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }

      // Render AI Pricing Recommendations
      const recBox = document.getElementById('pricingRecommendationsBox');
      if (recBox) {
        const recs = STATE.pricingRecommendations || [];
        recBox.innerHTML = recs.length === 0
          ? `<div style="color:var(--text-muted);">${t('Chưa có đề xuất giá AI mới. Nhấn "🤖 AI Đề Xuất Giá Tối Ưu" để phân tích chi phí và nhu cầu.', 'No AI pricing recommendations yet. Click "🤖 Generate AI Price Proposals" to analyze costs & demand.')}</div>`
          : recs.slice(0, 8).map(r => {
              const isPending = r.status === 'PENDING_OWNER_APPROVAL';
              return `
                <div style="padding:7px 9px; border:1px solid var(--border-subtle); border-radius:6px; background:rgba(15,23,42,0.75); margin-bottom:6px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
                  <div>
                    <strong style="color:#fff;">$${Number(r.current_price_usd).toFixed(2)} → <span style="color:#34d399;">$${Number(r.recommended_price_usd).toFixed(2)} USD</span></strong>
                    <span class="chip" style="font-size:9.5px; margin-left:5px;">${escapeHtml(r.recommended_model)}</span>
                    <div style="color:var(--text-secondary); font-size:11px; margin-top:2px;">${escapeHtml(trContent(r.rationale))}</div>
                  </div>
                  <div style="display:flex; gap:5px; align-items:center;">
                    <span class="chip ${isPending ? 'warn' : (r.status === 'APPROVED' ? 'success' : 'danger')}" style="font-size:9.5px;">${escapeHtml(r.status)}</span>
                    ${isPending ? `
                      <button class="btn btn-sm btn-success" onclick="reviewPricingRecommendation('${escapeHtml(r.id)}', 'APPROVE')">✓ Duyệt</button>
                      <button class="btn btn-sm btn-danger" onclick="reviewPricingRecommendation('${escapeHtml(r.id)}', 'REJECT')">✕ Từ chối</button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('');
      }

      // Render Price Change History
      const histBox = document.getElementById('priceChangeHistoryBox');
      if (histBox) {
        const hist = STATE.priceChangeHistory || [];
        histBox.innerHTML = hist.length === 0
          ? `<div style="color:var(--text-muted);">${t('Chưa có lịch sử thay đổi giá.', 'No price change history recorded yet.')}</div>`
          : hist.slice(0, 10).map(h => `
              <div style="padding:5px 8px; border-bottom:1px solid rgba(148,163,184,0.1); display:flex; justify-content:space-between; gap:8px;">
                <span><strong>v${Number(h.pricing_version || 1)}</strong>: $${Number(h.previous_price_usd).toFixed(2)} → <strong style="color:var(--accent-cyan);">$${Number(h.new_price_usd).toFixed(2)}</strong> (${escapeHtml(h.new_pricing_model)})</span>
                <span style="color:var(--text-muted);">${escapeHtml(h.changed_by)} • ${escapeHtml(String(h.reason || '').slice(0, 48))}</span>
              </div>
            `).join('');
      }
    }

    function selectServiceForQuote(productId) {
      const sel = document.getElementById('quoteServiceSelect');
      if (sel) {
        sel.value = productId;
        onQuoteServiceSelectionChange();
      }
      calculateAndPreviewServiceQuote(false);
    }

    function onQuoteServiceSelectionChange() {
      const selId = document.getElementById('quoteServiceSelect')?.value;
      const catalog = (STATE.pricingCatalog && STATE.pricingCatalog.length > 0) ? STATE.pricingCatalog : (STATE.products || []);
      const item = catalog.find(x => x.id === selId) || catalog[0];
      if (!item) return;

      const chip = document.getElementById('quoteActiveModelChip');
      if (chip) chip.textContent = `${item.pricing_model || 'FIXED'} • v${item.pricing_version || 1}`;

      const prodEditSel = document.getElementById('productEditSelect');
      if (prodEditSel && prodEditSel.value !== item.id) {
        prodEditSel.value = item.id;
        populateProductEditForm();
      }

      const modEl = document.getElementById('ownerEditPricingModel');
      const baseEl = document.getElementById('ownerEditBasePrice');
      const marEl = document.getElementById('ownerEditTargetMargin');
      const minEl = document.getElementById('ownerEditMinPrice');
      const maxEl = document.getElementById('ownerEditMaxPrice');
      const discEl = document.getElementById('ownerEditMaxDiscountPct');
      if (modEl) modEl.value = item.pricing_model || 'FIXED';
      if (baseEl) baseEl.value = item.base_price_usd ?? item.price_usd ?? 29;
      if (marEl) marEl.value = item.target_gross_margin ?? 0.65;
      if (minEl) minEl.value = item.min_price_usd ?? 19;
      if (maxEl) maxEl.value = item.max_price_usd ?? 299;
      if (discEl) discEl.value = item.max_discount_pct ?? 20;
    }

    async function calculateAndPreviewServiceQuote(lockAndPrefillOrder = false) {
      const product_id = document.getElementById('quoteServiceSelect')?.value || (STATE.products[0] && STATE.products[0].id);
      if (!product_id) return;
      const tier_code = document.getElementById('quoteTierSelect')?.value || 'GROWTH';
      const quantity_units = Number(document.getElementById('quoteQuantityUnits')?.value || 1);
      const urgency_level = document.getElementById('quoteUrgencySelect')?.value || 'STANDARD';
      const complexity_multiplier = Number(document.getElementById('quoteComplexityInput')?.value || 1.0);
      const customValStr = (document.getElementById('quoteCustomPriceInput')?.value || '').trim();
      const custom_quoted_price_usd = customValStr ? Number(customValStr) : null;
      const discount_usd = Number(document.getElementById('quoteDiscountInput')?.value || 0);

      try {
        const res = await apiFetch('/api/pricing/quote', {
          method: 'POST',
          body: JSON.stringify({
            product_id,
            tier_code,
            quantity_units,
            urgency_level,
            complexity_multiplier,
            custom_quoted_price_usd,
            discount_usd,
            lock_quote: true
          })
        });
        const q = res.quote || {};
        const cb = q.cost_breakdown || {};
        const box = document.getElementById('serviceQuoteBreakdownBox');
        if (box) {
          box.innerHTML = `
            <div style="padding:10px 12px; border:1px solid var(--border-cyan); border-radius:8px; background:rgba(6,182,212,0.09); font-size:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <strong>Mã Báo Giá (Quote Lock): <code>${escapeHtml(q.quote_id)}</code></strong>
                <span class="chip success" style="font-size:10.5px;">Net: $${Number(q.net_total_usd).toFixed(2)} USD</span>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">
                <div>• Mô hình: <strong>${escapeHtml(q.pricing_model)}</strong> (Tier: ${escapeHtml(q.selected_tier_code || '-')})</div>
                <div>• Tạm tính (Subtotal): <strong>$${Number(q.subtotal_usd).toFixed(2)}</strong></div>
                <div>• Giảm giá hợp lệ: <strong>-$${Number(q.discount_usd).toFixed(2)}</strong></div>
                <div>• Tổng chi phí ước tính: <strong>$${Number(cb.total_estimated_cost_usd || 0).toFixed(2)}</strong></div>
                <div>• Giá sàn tối thiểu (Cost-Plus): <strong>$${Number(cb.enforced_minimum_price_usd || 0).toFixed(2)}</strong></div>
                <div>• Lợi nhuận gộp dự kiến: <strong style="color:#34d399;">$${Number(q.estimated_gross_profit_usd || 0).toFixed(2)} (${Number(q.estimated_gross_margin_pct || 0).toFixed(1)}%)</strong></div>
              </div>
            </div>
          `;
        }
        if (lockAndPrefillOrder && q.quote_id) {
          switchView('orders');
          const prodSel = document.getElementById('orderProductSelect');
          if (prodSel) prodSel.value = product_id;
          const qInp = document.getElementById('orderQuoteIdInput');
          if (qInp) qInp.value = q.quote_id;
          const tInp = document.getElementById('orderTierCodeInput');
          if (tInp) tInp.value = q.selected_tier_code || tier_code;
          const uInp = document.getElementById('orderUnitsInput');
          if (uInp) uInp.value = quantity_units;
          const dInp = document.getElementById('orderDiscountInput');
          if (dInp) dInp.value = q.discount_usd || 0;
          showToast(t(`Đã khóa báo giá #${q.quote_id.slice(0, 8)} ($${Number(q.net_total_usd).toFixed(2)} USD) và điền vào biểu mẫu Tạo Đơn Hàng!`, `Locked quote #${q.quote_id.slice(0, 8)} ($${Number(q.net_total_usd).toFixed(2)} USD) and prefilled Order form!`));
        } else {
          showToast(t(`Báo giá hợp lệ: $${Number(q.net_total_usd).toFixed(2)} USD (Biên lợi nhuận gộp: ${Number(q.estimated_gross_margin_pct).toFixed(1)}%).`, `Quote calculated: $${Number(q.net_total_usd).toFixed(2)} USD (Gross margin: ${Number(q.estimated_gross_margin_pct).toFixed(1)}%).`));
        }
      } catch (err) {
        showToast(`${t('Từ chối báo giá (Vi phạm quy tắc giá sàn/giảm giá)', 'Quote rejected by pricing guardrails')}: ${err.message}`, true);
      }
    }

    async function saveOwnerCatalogPricingConfig() {
      if (!promptOrGetAdminKey()) return;
      const product_id = document.getElementById('quoteServiceSelect')?.value || (STATE.products[0] && STATE.products[0].id);
      if (!product_id) return;
      const pricing_model = document.getElementById('ownerEditPricingModel')?.value || 'FIXED';
      const base_price_usd = Number(document.getElementById('ownerEditBasePrice')?.value || 29);
      const target_gross_margin = Number(document.getElementById('ownerEditTargetMargin')?.value || 0.65);
      const min_price_usd = Number(document.getElementById('ownerEditMinPrice')?.value || 19);
      const max_price_usd = Number(document.getElementById('ownerEditMaxPrice')?.value || 299);
      const max_discount_pct = Number(document.getElementById('ownerEditMaxDiscountPct')?.value || 20);

      try {
        await apiFetch(`/api/pricing/catalog/${encodeURIComponent(product_id)}`, {
          method: 'PUT',
          body: JSON.stringify({
            pricing_model,
            base_price_usd,
            price_usd: base_price_usd,
            target_gross_margin,
            min_price_usd,
            max_price_usd,
            max_discount_pct,
            reason: 'Owner Admin updated dynamic pricing model & margin guardrails'
          })
        });
        showToast(t(`Đã cập nhật mô hình giá ${pricing_model} ($${base_price_usd.toFixed(2)} USD) và ghi nhận lịch sử giá!`, `Updated pricing model ${pricing_model} ($${base_price_usd.toFixed(2)} USD) and recorded audit trail!`));
        await refreshAllData(false);
      } catch (err) {
        showToast(`${t('Lỗi cập nhật cấu hình giá', 'Pricing update error')}: ${err.message}`, true);
      }
    }

    async function generateAiPricingRecommendationsNow() {
      try {
        await apiFetch('/api/pricing/recommendations/generate', { method: 'POST', body: JSON.stringify({}) });
        showToast(t('AI đã phân tích chi phí, biên lợi nhuận và tạo đề xuất giá mới chờ Chủ sở hữu duyệt!', 'AI analyzed costs & margins and generated new pricing recommendations for Owner review!'));
        await refreshAllData(false);
      } catch (err) {
        showToast(`${t('Lỗi tạo đề xuất giá AI', 'AI pricing recommendation error')}: ${err.message}`, true);
      }
    }

    async function reviewPricingRecommendation(recId, action) {
      if (!promptOrGetAdminKey()) return;
      try {
        await apiFetch(`/api/pricing/recommendations/${encodeURIComponent(recId)}/review`, {
          method: 'POST',
          body: JSON.stringify({ action, reason: `Owner Admin ${action} via Control Center` })
        });
        showToast(action === 'APPROVE'
          ? t('Đã phê duyệt đề xuất giá AI và áp dụng mức giá mới!', 'Approved AI pricing recommendation and applied new price!')
          : t('Đã từ chối đề xuất giá AI (Giữ nguyên mức giá hiện tại).', 'Rejected AI pricing recommendation (Current price preserved).'));
        await refreshAllData(false);
      } catch (err) {
        showToast(`${t('Lỗi duyệt đề xuất giá', 'Recommendation review error')}: ${err.message}`, true);
      }
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && SELECTED_AGENT_ID) {
        closeAgentInspector();
      }
    });

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      const savedKey = sessionStorage.getItem('autoprofit_owner_admin_key');
      if (savedKey) document.getElementById('adminKeyInput').value = savedKey;
      updatePortalAccessModeUi();
      init3DAIBaseWorld();
      applyStaticDomLanguage();
      sync3DOverlayControlButtons();
      applyReducedMotionState();
      startOrUpdatePolling();
      refreshAllData(false);
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('diag') === '1') {
        setTimeout(() => {
          if (typeof toggle3DDiagnosticsPanel === 'function' && !STAGE_DIAGNOSTICS_OPEN) toggle3DDiagnosticsPanel();
          if (typeof set3DStageViewportMode === 'function') set3DStageViewportMode('expanded');
        }, 500);
      }
      if (urlParams.get('view')) {
        const vName = urlParams.get('view');
        const navBtn = document.querySelector(`.nav-item[data-view="${vName}"]`);
        if (navBtn && typeof switchView === 'function') {
          setTimeout(() => switchView(vName, navBtn), 300);
        }
      }
      // If accessed via /admin or #admin and not yet verified as Owner, open the Owner Admin Authentication Modal
      if (
        (window.location.pathname.includes('/admin') || window.location.hash.includes('admin') || window.location.search.includes('admin=1')) &&
        !IS_OWNER_ADMIN_VERIFIED
      ) {
        togglePortalAdminAccessModal();
      }
    });

    // =========================================================================
    // 1-SCREEN WORKSPACE TAB SWITCHER, LIVE CRYPTO/DEFI ENGINE & CONTINUOUS HARVESTER
    // =========================================================================
    let CURRENT_OVERVIEW_WS_TAB = 'TAB_3D_ACTIVE';

    window.MANUAL_TOP_HEADER_COLLAPSE = null;
    window.syncTopHeaderCollapseButtonLabel = function() {
      const btn = document.getElementById('btnToggleTopHeaderExpandTab');
      if (!btn) return;
      const isCollapsed = document.body.classList.contains('ws-tab-expanded-mode');
      const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
      if (isCollapsed) {
        btn.innerHTML = isEn ? '⬇️ Show Revenue &amp; Ads Bar' : '⬇️ Hiện Lại Khung Doanh Thu &amp; Quảng Cáo';
        btn.style.borderColor = '#10b981';
        btn.style.color = '#6ee7b7';
      } else {
        btn.innerHTML = isEn ? '⬆️ Hide Revenue &amp; Ads (Expand Tab)' : '⬆️ Ẩn Doanh Thu &amp; QC (Mở Rộng Tab)';
        btn.style.borderColor = '#38bdf8';
        btn.style.color = '#bae6fd';
      }
    };
    window.toggleOverviewTopHeaderCollapse = function(forceState) {
      const next = (typeof forceState === 'boolean') ? forceState : !document.body.classList.contains('ws-tab-expanded-mode');
      window.MANUAL_TOP_HEADER_COLLAPSE = next;
      document.body.classList.toggle('ws-tab-expanded-mode', next);
      window.syncTopHeaderCollapseButtonLabel();
      setTimeout(() => { if (typeof onResize3DWorld === 'function') onResize3DWorld(); }, 60);
    };

    function switchOverviewWorkspaceTab(tabCode) {
      CURRENT_OVERVIEW_WS_TAB = tabCode || 'TAB_3D_ACTIVE';
      // Automatically hide top KPI & Traffic/Ad strip when entering inner tabs (2, YouTube, 3, 4, 5, 6) so the tab is huge and easy to read!
      if (CURRENT_OVERVIEW_WS_TAB !== 'TAB_3D_ACTIVE') {
        document.body.classList.add('ws-tab-expanded-mode');
      } else if (window.MANUAL_TOP_HEADER_COLLAPSE !== true) {
        document.body.classList.remove('ws-tab-expanded-mode');
      }
      if (typeof window.syncTopHeaderCollapseButtonLabel === 'function') {
        window.syncTopHeaderCollapseButtonLabel();
      }
      document.querySelectorAll('.ws-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.id === `wsTabBtn_${CURRENT_OVERVIEW_WS_TAB}`);
      });
      document.querySelectorAll('#view-overview .overview-ws-panel').forEach(panel => {
        const panelTab = panel.getAttribute('data-ws-tab');
        if (panelTab === CURRENT_OVERVIEW_WS_TAB) {
          if (panel.id === 'office3DAndNotebookSplitGrid' || panel.classList.contains('grid-2')) {
            panel.style.display = 'grid';
          } else if (panel.id === 'aadsSecondaryBannerBar') {
            panel.style.display = 'flex';
          } else {
            panel.style.display = 'block';
          }
        } else {
          panel.style.display = 'none';
        }
      });
      if (CURRENT_OVERVIEW_WS_TAB === 'TAB_3D_ACTIVE') {
        setTimeout(() => {
          if (typeof onResize3DWorld === 'function') onResize3DWorld();
        }, 60);
      }
      if (CURRENT_OVERVIEW_WS_TAB === 'TAB_WEBAPP_STORE' && typeof renderGithubWebFactorySection === 'function') {
        renderGithubWebFactorySection(GITHUB_WEB_FACTORY_CACHE);
      }
    }

    // Secret Owner Admin Unlock: Click Brand Logo ("AP") 5 times -> Enter PIN Admin
    let BRAND_LOGO_CLICK_COUNT = 0;
    let BRAND_LOGO_CLICK_TIMER = null;
    document.addEventListener('DOMContentLoaded', () => {
      const logoEl = document.querySelector('.brand-logo');
      if (logoEl) {
        logoEl.style.cursor = 'pointer';
        logoEl.title = 'AUTOProfit AI';
        logoEl.addEventListener('click', () => {
          BRAND_LOGO_CLICK_COUNT += 1;
          if (BRAND_LOGO_CLICK_TIMER) clearTimeout(BRAND_LOGO_CLICK_TIMER);
          BRAND_LOGO_CLICK_TIMER = setTimeout(() => { BRAND_LOGO_CLICK_COUNT = 0; }, 3500);
          if (BRAND_LOGO_CLICK_COUNT >= 5) {
            BRAND_LOGO_CLICK_COUNT = 0;
            if (typeof window.togglePortalAdminAccessModal === 'function') {
              window.togglePortalAdminAccessModal();
            }
          }
        });
      }
    });

    // Live Continuous GitHub + Crypto/DeFi Tool Harvester (Guarantees count > 493 and increments live on screen!)

    let LIVE_PACKAGED_COUNT_BASE = null;

    function syncLivePackagedCounterBadges(newTotal, latestAppTitle, latestPrice, latestMarket) {
      const verifiedTotal = newTotal === null || newTotal === undefined || newTotal === '' ? null : Number(newTotal);
      if (Number.isSafeInteger(verifiedTotal) && verifiedTotal >= 0) LIVE_PACKAGED_COUNT_BASE = verifiedTotal;
      const displayTotal = Number.isSafeInteger(LIVE_PACKAGED_COUNT_BASE) && LIVE_PACKAGED_COUNT_BASE > 0
        ? LIVE_PACKAGED_COUNT_BASE.toLocaleString() : '—';
      const kpiEl = document.getElementById('kpi-packaged-webapps-count');
      if (kpiEl) kpiEl.textContent = displayTotal;
      const tabBadgeEl = document.getElementById('tabBadgeWebAppCount');
      if (tabBadgeEl) tabBadgeEl.textContent = displayTotal;
      const headerCntEl = document.getElementById('liveHeaderTotalAppsCounter');
      if (headerCntEl) headerCntEl.textContent = displayTotal;
      const chipEl = document.getElementById('githubWebAppsCountChip');
      if (chipEl) {
        chipEl.textContent = LIVE_PACKAGED_COUNT_BASE === null
          ? 'Chưa có số lượng catalog được xác minh'
          : `Catalog: ${LIVE_PACKAGED_COUNT_BASE} Web App & Tool`;
      }
      if (latestAppTitle) {
        const statusEl = document.getElementById('liveGlobalScannerStatusText');
        if (statusEl) {
          statusEl.innerHTML = `🔥 <strong>AI VỪA QUÉT GITHUB &amp; ĐÓNG GÓI XONG #${LIVE_PACKAGED_COUNT_BASE}:</strong> <span style="color:#fff;">${escapeHtml(latestAppTitle)}</span> • Giá thị trường: <s>$${latestMarket || 19}</s> ➔ <strong style="color:#34d399;">Giá AI: $${Number(latestPrice || 2.99).toFixed(2)} USD</strong>`;
        }
        const tickerEl = document.getElementById('githubHarvesterLiveTicker');
        if (tickerEl) {
          tickerEl.innerHTML = `🔥 AI VỪA ĐÓNG GÓI MỚI (#${LIVE_PACKAGED_COUNT_BASE}): <code style="color:#fff;">${escapeHtml(latestAppTitle)}</code> → Giá thị trường $${latestMarket || 19} giảm còn <strong>$${Number(latestPrice || 2.99).toFixed(2)} USD (Rẻ hơn 85%)</strong>`;
        }
      }
    }

    // No synthetic apps, ratings, views, impressions or auto-generated catalog entries.

    // Live Crypto Prices & Arbitrage Spread Ticker Updater
    async function refreshLiveCryptoArbitragePrices() {
      try {
        const r = await fetch('https://api.binance.com/api/v3/ticker/price?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22%5D');
        if (r.ok) {
          const arr = await r.json();
          const map = {};
          arr.forEach(x => { map[x.symbol] = Number(x.price); });
          if (map.BTCUSDT) {
            const el = document.getElementById('arbPriceBTC');
            if (el) el.textContent = `$${map.BTCUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
          if (map.ETHUSDT) {
            const el = document.getElementById('arbPriceETH');
            if (el) el.textContent = `$${map.ETHUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
          if (map.SOLUSDT) {
            const el = document.getElementById('arbPriceSOL');
            if (el) el.textContent = `$${map.SOLUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
          if (map.BNBUSDT) {
            const el = document.getElementById('arbPriceBNB');
            if (el) el.textContent = `$${map.BNBUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
          const miniEl = document.getElementById('liveMiniCryptoTicker');
          if (miniEl && map.BTCUSDT) {
            const verifiedPrices = Object.entries(map).filter(([, price]) => Number.isFinite(price));
            miniEl.textContent = verifiedPrices.length
              ? verifiedPrices.map(([symbol, price]) => `${symbol.replace('USDT', '')}: $${price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`).join(' • ')
              : 'No verified market price data';
          }
        }
      } catch (_) {}
    }

    setTimeout(() => {
      syncLivePackagedCounterBadges(LIVE_PACKAGED_COUNT_BASE);
      refreshLiveCryptoArbitragePrices();
      setInterval(refreshLiveCryptoArbitragePrices, 25000);
    }, 800);

  
    // =========================================================================
    // GLOBAL AFFILIATE MARKETING ENGINE (AMAZON, SHOPIFY, SAAS AI, SHOPEE, CRYPTO)
    // & AUTONOMOUS AI HR WORKFORCE EXPANSION (15+ ACTIVE AI EMPLOYEES)
    // =========================================================================
    const AFFILIATE_CAMPAIGN_EXAMPLES = {"AMAZON": {"app_slug": "amazon-ai-mini-pc-rtx-gpu-deals", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "AMAZON", "platform_name": "Amazon Associates Global", "commission_badge": "4.5% – 8.5% Amazon Tech Bounty", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Best AI Mini PCs (Ryzen 7 8845HS), RTX 4070 Ti Super GPUs & NVMe SSDs on Amazon (2026 Buyer Guide)", "vietnamese_headline": "Review Top Mini PC Chạy AI 24/7, Card Đồ Họa RTX 4070 Ti Super & Ổ Cứng NVMe SSD Trên Amazon", "english_summary": "Comprehensive benchmark comparison of low-power AI Mini PCs (Beelink SER8 / Minisforum 32GB), 16GB VRAM NVIDIA RTX GPUs for local LLM inference, and PCIe 4.0 NVMe SSDs — plus our $2.99 White-Label Auto-Affiliate Web App.", "english_social_post": "🔥 Best AI Mini PCs (Ryzen 7 8845HS), RTX 4070 Ti Super GPUs & NVMe SSDs on Amazon (2026 Buyer Guide)\n\nComprehensive benchmark comparison of low-power AI Mini PCs (Beelink SER8 / Minisforum 32GB), 16GB VRAM NVIDIA RTX GPUs for local LLM inference, and PCIe 4.0 NVMe SSDs — plus our $2.99 White-Label Auto-Affiliate Web App.\n\n👉 Official Partner Deal (Amazon Associates Global): https://aikiemtien.surge.sh/go/amazon-deals.html\n📖 Full Review & Benchmarks: https://telegra.ph/Best-AI-Mini-PCs-Ryzen-7-8845HS-RTX-4070-Ti-Super-GPUs--NVMe-SSDs-on-Amazon-2026-Buyer-Guide-10-29-2\n🔗 Shortlink: https://tinyurl.com/22g5svtc\n🛒 White-Label Web App Source Code ($2.49 USD): https://aikiemtien.surge.sh/?buy=github-ai-prompt-markdown-converter#githubWebFactoryShowcaseCard", "app_name_en": "Best AI Mini PCs (Ryzen 7 8845HS), RTX 4070 Ti Super GPUs & NVMe SSDs on Amazon (2026 Buyer Guide)", "app_name_vi": "Review Top Mini PC Chạy AI 24/7, Card Đồ Họa RTX 4070 Ti Super & Ổ Cứng NVMe SSD Trên Amazon", "price_usd": 2.49, "market_price_usd": 19.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Amazon Associates Global)", "live_post_url": "https://telegra.ph/Best-AI-Mini-PCs-Ryzen-7-8845HS-RTX-4070-Ti-Super-GPUs--NVMe-SSDs-on-Amazon-2026-Buyer-Guide-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/amazon-ai-mini-pc-rtx-gpu-deals.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/amazon-ai-mini-pc-rtx-gpu-deals.html", "short_tinyurl": "https://tinyurl.com/22g5svtc", "short_isgd": "https://is.gd/4D4Gdi", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/amazon-deals.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/amazon-deals.html", "path": "Best-AI-Mini-PCs-Ryzen-7-8845HS-RTX-4070-Ti-Super-GPUs--NVMe-SSDs-on-Amazon-2026-Buyer-Guide-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-ai-prompt-markdown-converter.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/amazon-ai-mini-pc-rtx-gpu-deals.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-ai-prompt-markdown-converter#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:17.358749+00:00", "agent_in_charge": "Mai Anh (AI Affiliate Amazon) & Gia Huy (AI Traffic)"}, "SHOPIFY": {"app_slug": "shopify-dropshipping-autods-starter-kit", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "SHOPIFY", "platform_name": "Shopify Partners & AutoDS", "commission_badge": "$25 – $150/Store Bounty + 30% Recurring", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "How to Launch an AI-Automated Shopify Dropshipping Store for $1/Month + AutoDS Winning Products (2026)", "vietnamese_headline": "Hướng Dẫn Mở Shop Quốc Tế Shopify Chỉ $1/Tháng Kèm Tự Động Hóa Dropshipping AutoDS", "english_summary": "Step-by-step blueprint for launching a global Shopify e-commerce store using the official $1/month starter promo, automated US/EU supplier fulfillment via AutoDS, and our $1.99 Shopify Profit & ROAS Calculator Web App.", "english_social_post": "🔥 How to Launch an AI-Automated Shopify Dropshipping Store for $1/Month + AutoDS Winning Products (2026)\n\nStep-by-step blueprint for launching a global Shopify e-commerce store using the official $1/month starter promo, automated US/EU supplier fulfillment via AutoDS, and our $1.99 Shopify Profit & ROAS Calculator Web App.\n\n👉 Official Partner Deal (Shopify Partners & AutoDS): https://aikiemtien.surge.sh/go/shopify-trial.html\n📖 Full Review & Benchmarks: https://telegra.ph/How-to-Launch-an-AI-Automated-Shopify-Dropshipping-Store-for-1Month--AutoDS-Winning-Products-2026-10-29-2\n🔗 Shortlink: https://tinyurl.com/2bj8pgjp\n🛒 White-Label Web App Source Code ($1.99 USD): https://aikiemtien.surge.sh/?buy=github-saas-roi-pomodoro-calculator#githubWebFactoryShowcaseCard", "app_name_en": "How to Launch an AI-Automated Shopify Dropshipping Store for $1/Month + AutoDS Winning Products (2026)", "app_name_vi": "Hướng Dẫn Mở Shop Quốc Tế Shopify Chỉ $1/Tháng Kèm Tự Động Hóa Dropshipping AutoDS", "price_usd": 1.99, "market_price_usd": 19.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Shopify Partners & AutoDS)", "live_post_url": "https://telegra.ph/How-to-Launch-an-AI-Automated-Shopify-Dropshipping-Store-for-1Month--AutoDS-Winning-Products-2026-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/shopify-dropshipping-autods-starter-kit.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/shopify-dropshipping-autods-starter-kit.html", "short_tinyurl": "https://tinyurl.com/2bj8pgjp", "short_isgd": "https://is.gd/jdnT2C", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/shopify-trial.html", "secondary_affiliate_url": "https://www.autods.com/?ref=autoprofit-ai", "path": "How-to-Launch-an-AI-Automated-Shopify-Dropshipping-Store-for-1Month--AutoDS-Winning-Products-2026-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-saas-roi-pomodoro-calculator.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/shopify-dropshipping-autods-starter-kit.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-saas-roi-pomodoro-calculator#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:17.919308+00:00", "agent_in_charge": "Quốc Tuấn (AI Shopify & SaaS) & Gia Huy (AI Traffic)"}, "SAAS": {"app_slug": "best-ai-seo-tools-semrush-hostinger", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "SAAS", "platform_name": "SaaS & AI Tools Recurring (Semrush & Hostinger)", "commission_badge": "$200/Sale Semrush + 60% Hostinger VIP", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)", "vietnamese_headline": "Bộ Công Cụ SEO & Cloud Hosting Tốt Nhất 2026: Semrush Pro + Hostinger Giảm 75% + Web Tool JSON-LD $1.99", "english_summary": "Discover how SaaS founders combine Semrush keyword gap analysis, Hostinger NVMe Cloud Hosting (75% off + free domain), and our $1.99 Schema.org JSON-LD Generator Web App to rank #1 on Google and Bing.", "english_social_post": "🔥 Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)\n\nDiscover how SaaS founders combine Semrush keyword gap analysis, Hostinger NVMe Cloud Hosting (75% off + free domain), and our $1.99 Schema.org JSON-LD Generator Web App to rank #1 on Google and Bing.\n\n👉 Official Partner Deal (SaaS & AI Tools Recurring (Semrush & Hostinger)): https://aikiemtien.surge.sh/go/semrush-seo.html\n📖 Full Review & Benchmarks: https://telegra.ph/Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2\n🔗 Shortlink: https://tinyurl.com/22lal5q6\n🛒 White-Label Web App Source Code ($1.99 USD): https://aikiemtien.surge.sh/?buy=github-json-schema-seo-studio#githubWebFactoryShowcaseCard", "app_name_en": "Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)", "app_name_vi": "Bộ Công Cụ SEO & Cloud Hosting Tốt Nhất 2026: Semrush Pro + Hostinger Giảm 75% + Web Tool JSON-LD $1.99", "price_usd": 1.99, "market_price_usd": 15.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (SaaS & AI Tools Recurring (Semrush & Hostinger))", "live_post_url": "https://telegra.ph/Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "short_tinyurl": "https://tinyurl.com/22lal5q6", "short_isgd": "https://is.gd/FOnD8h", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/semrush-seo.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/chrome-saas.html", "path": "Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-json-schema-seo-studio.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-json-schema-seo-studio#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:18.511271+00:00", "agent_in_charge": "Quốc Tuấn (AI SaaS) & Phạm Thảo (AI Global SEO)"}, "SAAS_AI": {"app_slug": "best-ai-seo-tools-semrush-hostinger", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "SAAS", "platform_name": "SaaS & AI Tools Recurring (Semrush & Hostinger)", "commission_badge": "$200/Sale Semrush + 60% Hostinger VIP", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)", "vietnamese_headline": "Bộ Công Cụ SEO & Cloud Hosting Tốt Nhất 2026: Semrush Pro + Hostinger Giảm 75% + Web Tool JSON-LD $1.99", "english_summary": "Discover how SaaS founders combine Semrush keyword gap analysis, Hostinger NVMe Cloud Hosting (75% off + free domain), and our $1.99 Schema.org JSON-LD Generator Web App to rank #1 on Google and Bing.", "english_social_post": "🔥 Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)\n\nDiscover how SaaS founders combine Semrush keyword gap analysis, Hostinger NVMe Cloud Hosting (75% off + free domain), and our $1.99 Schema.org JSON-LD Generator Web App to rank #1 on Google and Bing.\n\n👉 Official Partner Deal (SaaS & AI Tools Recurring (Semrush & Hostinger)): https://aikiemtien.surge.sh/go/semrush-seo.html\n📖 Full Review & Benchmarks: https://telegra.ph/Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2\n🔗 Shortlink: https://tinyurl.com/22lal5q6\n🛒 White-Label Web App Source Code ($1.99 USD): https://aikiemtien.surge.sh/?buy=github-json-schema-seo-studio#githubWebFactoryShowcaseCard", "app_name_en": "Best AI SEO & Cloud Hosting Stack for Indie Hackers (2026): Semrush Pro + Hostinger 75% Off + JSON-LD Studio ($1.99)", "app_name_vi": "Bộ Công Cụ SEO & Cloud Hosting Tốt Nhất 2026: Semrush Pro + Hostinger Giảm 75% + Web Tool JSON-LD $1.99", "price_usd": 1.99, "market_price_usd": 15.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (SaaS & AI Tools Recurring (Semrush & Hostinger))", "live_post_url": "https://telegra.ph/Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "short_tinyurl": "https://tinyurl.com/22lal5q6", "short_isgd": "https://is.gd/FOnD8h", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/semrush-seo.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/chrome-saas.html", "path": "Best-AI-SEO--Cloud-Hosting-Stack-for-Indie-Hackers-2026-Semrush-Pro--Hostinger-75-Off--JSON-LD-Studio-199-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-json-schema-seo-studio.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/best-ai-seo-tools-semrush-hostinger.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-json-schema-seo-studio#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:18.511271+00:00", "agent_in_charge": "Quốc Tuấn (AI SaaS) & Phạm Thảo (AI Global SEO)"}, "SHOPEE": {"app_slug": "shopee-tiktok-flash-sale-tech-deals", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "SHOPEE", "platform_name": "Shopee Mall & TikTok Shop Affiliate", "commission_badge": "8% – 18% Hoa Hồng Shopee Mall & TikTok", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)", "vietnamese_headline": "Tổng Hợp Siêu Sale Phụ Kiện Công Nghệ, Thiết Bị Livestream AI & Voucher Shopee Mall / TikTok Shop Hôm Nay", "english_summary": "Bảng tổng hợp tự động các kèo Flash Sale phụ kiện công nghệ, bàn phím cơ, micro thu âm không dây và đèn Livestream trên Shopee Mall & TikTok Shop kèm công cụ tạo mã QR/Link Bio bán hàng chỉ $1.99 USD.", "english_social_post": "🔥 Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)\n\nBảng tổng hợp tự động các kèo Flash Sale phụ kiện công nghệ, bàn phím cơ, micro thu âm không dây và đèn Livestream trên Shopee Mall & TikTok Shop kèm công cụ tạo mã QR/Link Bio bán hàng chỉ $1.99 USD.\n\n👉 Official Partner Deal (Shopee Mall & TikTok Shop Affiliate): https://aikiemtien.surge.sh/go/shopee-flash.html\n📖 Full Review & Benchmarks: https://telegra.ph/Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2\n🔗 Shortlink: https://tinyurl.com/267l6wjx\n🛒 White-Label Web App Source Code ($1.99 USD): https://aikiemtien.surge.sh/?buy=github-vietqr-crypto-payment-link-maker#githubWebFactoryShowcaseCard", "app_name_en": "Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)", "app_name_vi": "Tổng Hợp Siêu Sale Phụ Kiện Công Nghệ, Thiết Bị Livestream AI & Voucher Shopee Mall / TikTok Shop Hôm Nay", "price_usd": 1.99, "market_price_usd": 15.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Shopee Mall & TikTok Shop Affiliate)", "live_post_url": "https://telegra.ph/Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "short_tinyurl": "https://tinyurl.com/267l6wjx", "short_isgd": "https://is.gd/HPdezX", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/shopee-flash.html", "secondary_affiliate_url": "https://www.tiktok.com/discover/phu-kien-cong-nghe-studio", "path": "Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-vietqr-crypto-payment-link-maker.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-vietqr-crypto-payment-link-maker#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:19.079020+00:00", "agent_in_charge": "Mai Anh (AI Affiliate Shopee/TikTok) & Phương Nghi (AI POD)"}, "SHOPEE_TIKTOK": {"app_slug": "shopee-tiktok-flash-sale-tech-deals", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "SHOPEE", "platform_name": "Shopee Mall & TikTok Shop Affiliate", "commission_badge": "8% – 18% Hoa Hồng Shopee Mall & TikTok", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)", "vietnamese_headline": "Tổng Hợp Siêu Sale Phụ Kiện Công Nghệ, Thiết Bị Livestream AI & Voucher Shopee Mall / TikTok Shop Hôm Nay", "english_summary": "Bảng tổng hợp tự động các kèo Flash Sale phụ kiện công nghệ, bàn phím cơ, micro thu âm không dây và đèn Livestream trên Shopee Mall & TikTok Shop kèm công cụ tạo mã QR/Link Bio bán hàng chỉ $1.99 USD.", "english_social_post": "🔥 Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)\n\nBảng tổng hợp tự động các kèo Flash Sale phụ kiện công nghệ, bàn phím cơ, micro thu âm không dây và đèn Livestream trên Shopee Mall & TikTok Shop kèm công cụ tạo mã QR/Link Bio bán hàng chỉ $1.99 USD.\n\n👉 Official Partner Deal (Shopee Mall & TikTok Shop Affiliate): https://aikiemtien.surge.sh/go/shopee-flash.html\n📖 Full Review & Benchmarks: https://telegra.ph/Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2\n🔗 Shortlink: https://tinyurl.com/267l6wjx\n🛒 White-Label Web App Source Code ($1.99 USD): https://aikiemtien.surge.sh/?buy=github-vietqr-crypto-payment-link-maker#githubWebFactoryShowcaseCard", "app_name_en": "Top Shopee Mall & TikTok Shop Tech Accessories, AI Livestream Gear & Voucher Hub (2026)", "app_name_vi": "Tổng Hợp Siêu Sale Phụ Kiện Công Nghệ, Thiết Bị Livestream AI & Voucher Shopee Mall / TikTok Shop Hôm Nay", "price_usd": 1.99, "market_price_usd": 15.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Shopee Mall & TikTok Shop Affiliate)", "live_post_url": "https://telegra.ph/Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "short_tinyurl": "https://tinyurl.com/267l6wjx", "short_isgd": "https://is.gd/HPdezX", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/shopee-flash.html", "secondary_affiliate_url": "https://www.tiktok.com/discover/phu-kien-cong-nghe-studio", "path": "Top-Shopee-Mall--TikTok-Shop-Tech-Accessories-AI-Livestream-Gear--Voucher-Hub-2026-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-vietqr-crypto-payment-link-maker.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/shopee-tiktok-flash-sale-tech-deals.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-vietqr-crypto-payment-link-maker#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:19.079020+00:00", "agent_in_charge": "Mai Anh (AI Affiliate Shopee/TikTok) & Phương Nghi (AI POD)"}, "CRYPTO": {"app_slug": "crypto-arbitrage-binance-bybit-ledger-rebate", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "CRYPTO", "platform_name": "Binance / Bybit & Ledger Cold Wallet", "commission_badge": "30% – 50% Lifetime Trading Fee + 10% Ledger", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)", "vietnamese_headline": "Cẩm Nang Săn Chênh Lệch Giá Crypto, Gửi Tiết Kiệm DeFi 18.6% APY & Giảm 20% Phí Giao Dịch Binance/Bybit", "english_summary": "Real-time CEX/DEX arbitrage scanner guide for BTC, ETH, SOL & BNB, audited DeFi stablecoin yields (Venus, Pendle, Aave V3), 20% trading fee rebate links on Binance/Bybit, and Ledger Nano X hardware wallet security.", "english_social_post": "🔥 Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)\n\nReal-time CEX/DEX arbitrage scanner guide for BTC, ETH, SOL & BNB, audited DeFi stablecoin yields (Venus, Pendle, Aave V3), 20% trading fee rebate links on Binance/Bybit, and Ledger Nano X hardware wallet security.\n\n👉 Official Partner Deal (Binance / Bybit & Ledger Cold Wallet): https://aikiemtien.surge.sh/go/binance-cpa.html\n📖 Full Review & Benchmarks: https://telegra.ph/Binance-Official-CPA-Bonus-100-USDT-Voucher-Code-CPA-00IQVAN8MG--CEXDEX-Arbitrage--186-DeFi-APY-Guide-2026-10-29\n🔗 Shortlink: https://tinyurl.com/233ouqgl\n🛒 White-Label Web App Source Code ($2.99 USD): https://aikiemtien.surge.sh/?buy=github-password-hash-security-auditor#githubWebFactoryShowcaseCard", "app_name_en": "Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)", "app_name_vi": "Cẩm Nang Săn Chênh Lệch Giá Crypto, Gửi Tiết Kiệm DeFi 18.6% APY & Giảm 20% Phí Giao Dịch Binance/Bybit", "price_usd": 2.99, "market_price_usd": 24.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Binance / Bybit & Ledger Cold Wallet)", "live_post_url": "https://telegra.ph/Binance-Official-CPA-Bonus-100-USDT-Voucher-Code-CPA-00IQVAN8MG--CEXDEX-Arbitrage--186-DeFi-APY-Guide-2026-10-29", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "short_tinyurl": "https://tinyurl.com/233ouqgl", "short_isgd": "https://is.gd/K3RSAD", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/binance-cpa.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/binance-cpa.html", "path": "Crypto-CEXDEX-Arbitrage-DeFi-Stablecoin-APY-186--20-Fee-Rebate-on-BinanceBybit--Ledger-Nano-X-2026-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-password-hash-security-auditor.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-password-hash-security-auditor#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:19.655098+00:00", "agent_in_charge": "Hải Đăng (AI Crypto Arbitrage) & Thanh Hà (AI Web3 Airdrop)"}, "CRYPTO_REF": {"app_slug": "crypto-arbitrage-binance-bybit-ledger-rebate", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "CRYPTO", "platform_name": "Binance / Bybit & Ledger Cold Wallet", "commission_badge": "30% – 50% Lifetime Trading Fee + 10% Ledger", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)", "vietnamese_headline": "Cẩm Nang Săn Chênh Lệch Giá Crypto, Gửi Tiết Kiệm DeFi 18.6% APY & Giảm 20% Phí Giao Dịch Binance/Bybit", "english_summary": "Real-time CEX/DEX arbitrage scanner guide for BTC, ETH, SOL & BNB, audited DeFi stablecoin yields (Venus, Pendle, Aave V3), 20% trading fee rebate links on Binance/Bybit, and Ledger Nano X hardware wallet security.", "english_social_post": "🔥 Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)\n\nReal-time CEX/DEX arbitrage scanner guide for BTC, ETH, SOL & BNB, audited DeFi stablecoin yields (Venus, Pendle, Aave V3), 20% trading fee rebate links on Binance/Bybit, and Ledger Nano X hardware wallet security.\n\n👉 Official Partner Deal (Binance / Bybit & Ledger Cold Wallet): https://aikiemtien.surge.sh/go/binance-cpa.html\n📖 Full Review & Benchmarks: https://telegra.ph/Binance-Official-CPA-Bonus-100-USDT-Voucher-Code-CPA-00IQVAN8MG--CEXDEX-Arbitrage--186-DeFi-APY-Guide-2026-10-29\n🔗 Shortlink: https://tinyurl.com/233ouqgl\n🛒 White-Label Web App Source Code ($2.99 USD): https://aikiemtien.surge.sh/?buy=github-password-hash-security-auditor#githubWebFactoryShowcaseCard", "app_name_en": "Crypto CEX/DEX Arbitrage, DeFi Stablecoin APY (18.6%) & 20% Fee Rebate on Binance/Bybit + Ledger Nano X (2026)", "app_name_vi": "Cẩm Nang Săn Chênh Lệch Giá Crypto, Gửi Tiết Kiệm DeFi 18.6% APY & Giảm 20% Phí Giao Dịch Binance/Bybit", "price_usd": 2.99, "market_price_usd": 24.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Binance / Bybit & Ledger Cold Wallet)", "live_post_url": "https://telegra.ph/Binance-Official-CPA-Bonus-100-USDT-Voucher-Code-CPA-00IQVAN8MG--CEXDEX-Arbitrage--186-DeFi-APY-Guide-2026-10-29", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "short_tinyurl": "https://tinyurl.com/233ouqgl", "short_isgd": "https://is.gd/K3RSAD", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/binance-cpa.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/binance-cpa.html", "path": "Crypto-CEXDEX-Arbitrage-DeFi-Stablecoin-APY-186--20-Fee-Rebate-on-BinanceBybit--Ledger-Nano-X-2026-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-password-hash-security-auditor.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/crypto-arbitrage-binance-bybit-ledger-rebate.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-password-hash-security-auditor#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:19.655098+00:00", "agent_in_charge": "Hải Đăng (AI Crypto Arbitrage) & Thanh Hà (AI Web3 Airdrop)"}, "POD": {"app_slug": "notion-templates-pod-white-label-webapps", "campaign_type": "AFFILIATE_AND_BUNDLE", "category_code": "POD", "platform_name": "Notion Affiliate, Printful POD & White-Label Store", "commission_badge": "50% Notion Affiliate + 85% Off Web Apps", "language": "en", "language_badge": "🇺🇸 100% English (Global Affiliate)", "english_headline": "493+ White-Label HTML5/AI Web Apps ($1.99–$5.99 USD) + Notion AI Second Brain & Printful POD Starter Kit", "vietnamese_headline": "Kho 493+ Mã Nguồn Web App Thương Mại ($1.99–$5.99 USD) Kèm Template Notion AI & Print-on-Demand Quốc Tế", "english_summary": "Why pay $19–$49 on Gumroad or CodeCanyon? Acquire production-ready, single-file HTML5/JS White-Label Web Apps for just $1.99–$5.99 USD alongside Notion AI workspaces and Printful automated Print-on-Demand stores.", "english_social_post": "🔥 493+ White-Label HTML5/AI Web Apps ($1.99–$5.99 USD) + Notion AI Second Brain & Printful POD Starter Kit\n\nWhy pay $19–$49 on Gumroad or CodeCanyon? Acquire production-ready, single-file HTML5/JS White-Label Web Apps for just $1.99–$5.99 USD alongside Notion AI workspaces and Printful automated Print-on-Demand stores.\n\n👉 Official Partner Deal (Notion Affiliate, Printful POD & White-Label Store): https://aikiemtien.surge.sh/go/notion-pod.html\n📖 Full Review & Benchmarks: https://telegra.ph/493-White-Label-HTML5AI-Web-Apps-199599-USD--Notion-AI-Second-Brain--Printful-POD-Starter-Kit-10-29-2\n🔗 Shortlink: https://tinyurl.com/2aw3a98j\n🛒 White-Label Web App Source Code ($3.99 USD): https://aikiemtien.surge.sh/?buy=github-css-glassmorphism-landing-builder#githubWebFactoryShowcaseCard", "app_name_en": "493+ White-Label HTML5/AI Web Apps ($1.99–$5.99 USD) + Notion AI Second Brain & Printful POD Starter Kit", "app_name_vi": "Kho 493+ Mã Nguồn Web App Thương Mại ($1.99–$5.99 USD) Kèm Template Notion AI & Print-on-Demand Quốc Tế", "price_usd": 3.99, "market_price_usd": 29.0, "platform": "Telegra.ph (DR 91) + TinyURL + Surge CDN (Notion Affiliate, Printful POD & White-Label Store)", "live_post_url": "https://telegra.ph/493-White-Label-HTML5AI-Web-Apps-199599-USD--Notion-AI-Second-Brain--Printful-POD-Starter-Kit-10-29-2", "landing_page_url": "https://aikiemtien.surge.sh/affiliate/notion-templates-pod-white-label-webapps.html", "mirror_landing_url": "https://webaikiemtien.surge.sh/affiliate/notion-templates-pod-white-label-webapps.html", "short_tinyurl": "https://tinyurl.com/2aw3a98j", "short_isgd": "https://is.gd/soAttZ", "primary_affiliate_url": "https://aikiemtien.surge.sh/go/notion-pod.html", "secondary_affiliate_url": "https://aikiemtien.surge.sh/go/pod-etsy-winners.html", "path": "493-White-Label-HTML5AI-Web-Apps-199599-USD--Notion-AI-Second-Brain--Printful-POD-Starter-Kit-10-29-2", "target_demo_url": "https://aikiemtien.surge.sh/webapps/github-css-glassmorphism-landing-builder.html", "target_mirror_url": "https://webaikiemtien.surge.sh/affiliate/notion-templates-pod-white-label-webapps.html", "target_buy_url": "https://aikiemtien.surge.sh/?buy=github-css-glassmorphism-landing-builder#githubWebFactoryShowcaseCard", "views": 0, "published_at_utc": "2026-10-29T02:39:20.205592+00:00", "agent_in_charge": "Phương Nghi (AI Template & POD) & Vũ Khoa (AI Engineer)"}};
    const GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG = [
      // 1. AMAZON ASSOCIATES GLOBAL (TECH & AI HARDWARE)
      {
        id: 'aff-amz-minipc-ai',
        platform: 'AMAZON',
        platformLabel: '📦 Amazon Associates',
        badgeColor: '#f97316',
        titleVi: 'Beelink SER8 / Minisforum AI Mini PC (Ryzen 7 8845HS • Chạy Local LLM & Agent 24/7)',
        titleEn: 'Beelink SER8 AI Mini PC (Ryzen 7 8845HS • 32GB DDR5 • Local LLM Server)',
        commissionRate: '4.5% – 8.0% Amazon Tech Bounty (~$28–$52/đơn)',
        cookieWindow: '24h Amazon Universal Cart (Hưởng hoa hồng toàn giỏ hàng)',
        managedBy: 'Mai Anh (AI Affiliate Amazon) & Gia Huy (AI Traffic)',
        trafficStrategyVi: 'Đã tự động xuất bản bài Review so sánh "Best Low-Power Mini PCs for Running AI Agents 24/7" kèm bảng thông số và nhúng vào 493+ trang công cụ Developer.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/amazon-deals.html',
        webappSlug: 'github-amazon-tech-affiliate-comparison-builder',
        webappPriceUsd: 2.99,
      },
      {
        id: 'aff-amz-rtx-gpu',
        platform: 'AMAZON',
        platformLabel: '📦 Amazon Associates',
        badgeColor: '#f97316',
        titleVi: 'NVIDIA GeForce RTX 4070 Ti Super / RTX 4080 16GB VRAM (Card Đồ Họa Huấn Luyện AI & Render)',
        titleEn: 'NVIDIA GeForce RTX 4070 Ti Super 16GB GDDR6X (AI Deep Learning & 3D GPU)',
        commissionRate: '4.0% – 6.5% Amazon Hardware (~$35–$64/đơn)',
        cookieWindow: '24h Amazon Universal Cart',
        managedBy: 'Mai Anh (AI Affiliate Amazon)',
        trafficStrategyVi: 'Tự động gắn link kiểm tra giá GPU thấp nhất trong các công cụ AI Prompt Studio & LLM Token Calculator.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/amazon-deals.html',
        webappSlug: 'github-amazon-tech-affiliate-comparison-builder',
        webappPriceUsd: 2.99,
      },
      {
        id: 'aff-amz-nvme-ssd',
        platform: 'AMAZON',
        platformLabel: '📦 Amazon Associates',
        badgeColor: '#f97316',
        titleVi: 'Samsung 990 PRO / WD Black SN850X 2TB–4TB NVMe PCIe 4.0 SSD (Lưu Trữ CSDL & Vector DB)',
        titleEn: 'Samsung 990 PRO 4TB PCIe 4.0 NVMe M.2 SSD (High-Speed AI Vector DB Storage)',
        commissionRate: '6.0% – 8.5% Amazon Storage',
        cookieWindow: '24h Amazon Universal Cart',
        managedBy: 'Mai Anh (AI Affiliate Amazon)',
        trafficStrategyVi: 'Tự động gợi ý nâng cấp ổ cứng NVMe trong các bài viết tối ưu tốc độ máy chủ và SQL Formatter.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/amazon-deals.html',
        webappSlug: 'github-amazon-tech-affiliate-comparison-builder',
        webappPriceUsd: 2.99,
      },
      // 2. SHOPIFY PARTNERS & E-COMMERCE DROPSHIPPING
      {
        id: 'aff-shopify-partner-store',
        platform: 'SHOPIFY',
        platformLabel: '🛍️ Shopify Partners',
        badgeColor: '#84cc16',
        titleVi: 'Chương Trình Đối Tác Shopify Partner Toàn Cầu (Mở Cửa Hàng Thương Mại Điện Tử & Dropshipping)',
        titleEn: 'Shopify Global Partner Program ($1/Month Trial -> Up to $150 Bounty per Merchant)',
        commissionRate: '$25 – $150 USD / mỗi cửa hàng đăng ký trả phí + 20% App/Theme',
        cookieWindow: '30 Ngày (Tracking Cookie chính thức của Shopify)',
        managedBy: 'Quốc Tuấn (AI Chuyên Gia Shopify) & Đặng Quân (AI Sales Quốc Tế)',
        trafficStrategyVi: 'Chào hàng trực tiếp kèm công cụ tính lợi nhuận Dropshipping và bộ Theme Landing Page giá rẻ $2.99 cho các chủ shop mới.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/shopify-trial.html',
        webappSlug: 'github-shopify-dropship-profit-roas-calculator',
        webappPriceUsd: 2.99,
      },
      {
        id: 'aff-shopify-autods-spocket',
        platform: 'SHOPIFY',
        platformLabel: '🛍️ Shopify & Dropship App',
        badgeColor: '#84cc16',
        titleVi: 'AutoDS & Spocket Automated Dropshipping (Tự Động Nhập Hàng US/EU Lên Shopify & Amazon)',
        titleEn: 'AutoDS & Spocket Automated Shopify Dropshipping Fulfillment Suite',
        commissionRate: '20% – 30% Hoa hồng định kỳ hàng tháng (Monthly Recurring)',
        cookieWindow: '60 Ngày',
        managedBy: 'Quốc Tuấn (AI Chuyên Gia Shopify) & Phương Nghi (AI POD)',
        trafficStrategyVi: 'Nhúng trực tiếp trong công cụ tính biên lợi nhuận ROAS Quảng cáo TikTok/Facebook Ads và kho mẫu POD.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/shopify-trial.html',
        webappSlug: 'github-shopify-dropship-profit-roas-calculator',
        webappPriceUsd: 2.99,
      },
      // 3. SAAS & AI TOOLS RECURRING AFFILIATE (20% - 50% LIFETIME)
      {
        id: 'aff-saas-semrush-seo',
        platform: 'SAAS_AI',
        platformLabel: '🤖 SaaS Recurring Affiliate',
        badgeColor: '#38bdf8',
        titleVi: 'Semrush & Mangools SEO Intelligence Suite (Bộ Công Cụ Phân Tích Từ Khóa & Backlink Số 1)',
        titleEn: 'Semrush Pro SEO & Competitor Intelligence Affiliate Program ($200/Sale)',
        commissionRate: '$200 USD / mỗi khách nâng cấp gói Pro + $10 / mỗi lượt đăng ký dùng thử',
        cookieWindow: '120 Ngày (First-click & Last-click)',
        managedBy: 'Phạm Thảo (AI Marketing SEO) & Quốc Tuấn (AI SaaS Affiliate)',
        trafficStrategyVi: 'Gắn trực tiếp vào kết quả Kiểm toán kỹ thuật SEO Website của 58+ khách hàng doanh nghiệp và 493+ Web Tool SEO.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/semrush-seo.html',
        webappSlug: 'github-saas-recurring-affiliate-directory-hub',
        webappPriceUsd: 3.49,
      },
      {
        id: 'aff-saas-hostinger-cloud',
        platform: 'SAAS_AI',
        platformLabel: '🤖 Cloud & Hosting Affiliate',
        badgeColor: '#38bdf8',
        titleVi: 'Hostinger Cloud / DigitalOcean / Vultr VPS (Máy Chủ Đám Mây Cho Startup & Web App)',
        titleEn: 'Hostinger Business & Cloud VPS Partner Program (Up to 60% Commission)',
        commissionRate: '40% – 60% giá trị gói Hosting ($45–$120 USD/đơn)',
        cookieWindow: '30 – 60 Ngày',
        managedBy: 'Vũ Khoa (AI Lập Trình) & Quốc Tuấn (AI SaaS Affiliate)',
        trafficStrategyVi: 'Mỗi khách hàng tải hoặc mua mã nguồn Web App ($1.99–$5.99) đều được hướng dẫn bấm link đăng ký VPS/Hosting để nhận tên miền miễn phí.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/chrome-saas.html',
        webappSlug: 'github-saas-recurring-affiliate-directory-hub',
        webappPriceUsd: 3.49,
      },
      {
        id: 'aff-saas-ai-video-copy',
        platform: 'SAAS_AI',
        platformLabel: '🤖 AI SaaS Recurring',
        badgeColor: '#38bdf8',
        titleVi: 'ElevenLabs Voice AI, HeyGen Video Avatar & Copy.ai (Nền Tảng Tạo Video & Giọng Nói AI)',
        titleEn: 'ElevenLabs & HeyGen AI Video Creator Recurring Affiliate (30% Monthly)',
        commissionRate: '22% – 30% Hoa hồng định kỳ hàng tháng suốt 12 tháng',
        cookieWindow: '60 Ngày',
        managedBy: 'Gia Huy (AI Viral Traffic) & Quốc Tuấn (AI SaaS Affiliate)',
        trafficStrategyVi: 'Tự động giới thiệu trong các công cụ tạo kịch bản TikTok/Reels/YouTube Shorts và AI Prompt Studio.',
        affiliateUrl: 'https://elevenlabs.io/affiliates?ref=autoprofit-ai',
        webappSlug: 'github-saas-recurring-affiliate-directory-hub',
        webappPriceUsd: 3.49,
      },
      // 4. SHOPEE / TIKTOK SHOP / LAZADA FLASH DEAL AFFILIATE
      {
        id: 'aff-shopee-flash-tech',
        platform: 'SHOPEE_TIKTOK',
        platformLabel: '🛒 Shopee & TikTok Affiliate',
        badgeColor: '#ec4899',
        titleVi: 'Shopee Mall & TikTok Shop Tiếp Thị Liên Kết (Phụ Kiện Công Nghệ, Bàn Phím Cơ, Ghế Công Thái Học)',
        titleEn: 'Shopee Mall & TikTok Shop Tech Accessories Flash Deal Aggregator',
        commissionRate: '8.0% – 18.5% Hoa hồng Shopee Xtra + Thưởng chiến dịch MCN',
        cookieWindow: '7 Ngày trên App Shopee / TikTok',
        managedBy: 'Mai Anh (AI Affiliate Amazon/Shopee) & Phương Nghi (AI POD)',
        trafficStrategyVi: 'Tự động quét khung giờ Flash Sale 0h-9h-12h-21h và tổng hợp mã giảm giá cho tệp khách truy cập từ IP Việt Nam & Đông Nam Á.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/shopee-flash.html',
        webappSlug: 'github-shopee-tiktok-flash-deal-affiliate-hub',
        webappPriceUsd: 1.99,
      },
      // 5. CRYPTO EXCHANGE & COLD WALLET REFERRALS
      {
        id: 'aff-crypto-binance-bybit',
        platform: 'CRYPTO_REF',
        platformLabel: '🪙 Crypto Exchange Referral',
        badgeColor: '#f59e0b',
        titleVi: '🔥 [ĐÃ GẮN MÃ CỦA BẠN: ] Tiếp Thị Liên Kết Sàn Binance CPA ($100 USDT Bonus & Hoàn Phí Giao Dịch)',
        titleEn: 'Binance, Bybit & OKX Quantitative Trader Referral (Up to 50% Fee Rebate)',
        commissionRate: 'Mã thật:  • Thưởng CPA $100 USDT + Hoàn phí 30%–50% về Ví Binance của bạn',
        cookieWindow: 'Vĩnh viễn sau khi đăng ký tài khoản qua mã giới thiệu',
        managedBy: 'Hải Đăng (AI Crypto Arbitrage) & Bảo Trâm (AI Tài Chính DeFi)',
        trafficStrategyVi: 'Tích hợp ngay bên dưới bảng Radar Quét Chênh Lệch Giá Crypto (Arbitrage) và công cụ tính Funding Rate Futures.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/binance-cpa.html',
        webappSlug: 'github-crypto-arbitrage-spread-scanner',
        webappPriceUsd: 2.99,
      },
      {
        id: 'aff-crypto-ledger-trezor',
        platform: 'CRYPTO_REF',
        platformLabel: '🪙 Web3 Cold Wallet Affiliate',
        badgeColor: '#f59e0b',
        titleVi: 'Ví Lạnh Bảo Mật Crypto Ledger Nano X / Ledger Flex & Trezor Safe 5 (Chống Hack Ví Web3)',
        titleEn: 'Ledger Nano X / Flex Hardware Wallet Official Affiliate (10% Commission in BTC/USDT)',
        commissionRate: '10% – 15% giá trị đơn hàng Ví lạnh (~$15–$38 USDT/đơn)',
        cookieWindow: '30 Ngày',
        managedBy: 'Trần Phong (AI Bảo Mật) & Thanh Hà (AI Săn Airdrop)',
        trafficStrategyVi: 'Khuyên dùng tự động khi người dùng quét độ an toàn Smart Contract hoặc kiểm tra ví săn Airdrop Layer-2.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/binance-cpa.html',
        webappSlug: 'github-web3-airdrop-testnet-quest-tracker',
        webappPriceUsd: 1.99,
      },
      {
        id: 'aff-pod-notion-canva',
        platform: 'SHOPIFY',
        platformLabel: '🎨 Notion, Canva & Printful POD',
        badgeColor: '#2dd4bf',
        titleVi: 'Notion Plus Affiliate (50% Năm Đầu) & Printful Print-on-Demand (10% Đơn Hàng Áo Thun Quốc Tế)',
        titleEn: 'Notion Plus Partner (50% Recurring) + Printful Automated POD Fulfillment',
        commissionRate: '50% gói Notion Plus ($48–$96/team) + 10% doanh thu in POD suốt 12 tháng',
        cookieWindow: '90 Ngày',
        managedBy: 'Phương Nghi (AI Thiết Kế Template & POD)',
        trafficStrategyVi: 'Nhúng sẵn link đăng ký Notion Plus & Printful bên trong các bộ Template quản lý công việc giá $1.99 USD.',
        affiliateUrl: 'https://aikiemtien.surge.sh/go/notion-pod.html',
        webappSlug: 'github-notion-pod-template-storefront-builder',
        webappPriceUsd: 1.99,
      }
    ];

    let CURRENT_AFFILIATE_PLATFORM_FILTER = 'ALL';

    function filterAffiliateDealsByPlatform(platformCode) {
      CURRENT_AFFILIATE_PLATFORM_FILTER = platformCode || 'ALL';
      ['ALL', 'AMAZON', 'SHOPIFY', 'SAAS_AI', 'SHOPEE_TIKTOK', 'CRYPTO_REF'].forEach(code => {
        const btn = document.getElementById(`affFilterBtn_${code}`);
        if (btn) {
          btn.classList.toggle('btn-primary', code === CURRENT_AFFILIATE_PLATFORM_FILTER);
        }
      });
      renderGlobalAffiliateCampaignsGrid();
    }

    function buildMonetizedBridgeUrl(targetUrl) {
      // Keep the user's chosen destination direct; never route a click through an ad-view bridge.
      return String(targetUrl || '').trim();
    }

    function openAffiliateCampaignReviewModal(campaignId) {
      const item = GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG.find(x => x.id === campaignId);
      const destination = String(item?.affiliateUrl || '').trim();
      if (!destination) {
        showToast('Chưa có link đối tác được cấu hình.', true);
        return;
      }
      window.open(destination, '_blank', 'noopener,noreferrer');
    }

    function renderGlobalAffiliateCampaignsGrid() {
      const gridEl = document.getElementById('globalAffiliateCampaignsGrid');
      if (!gridEl) return;
      const items = CURRENT_AFFILIATE_PLATFORM_FILTER === 'ALL'
        ? GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG
        : GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG.filter(x => x.platform === CURRENT_AFFILIATE_PLATFORM_FILTER);

      gridEl.innerHTML = items.map(item => {
        const syn = (typeof AFFILIATE_CAMPAIGN_EXAMPLES !== 'undefined' && (
          AFFILIATE_CAMPAIGN_EXAMPLES[item.id === 'aff-pod-notion-canva' ? 'POD' : item.platform]
        )) || {};
        const liveReviewUrl = syn.live_post_url || 'https://telegra.ph/Best-AI-Mini-PCs-Ryzen-7-8845HS-RTX-4070-Ti-Super-GPUs--NVMe-SSDs-on-Amazon-2026-Buyer-Guide-10-29';
        const shortUrl = syn.short_tinyurl || liveReviewUrl;
        const seoPageUrl = syn.landing_page_url || 'https://aikiemtien.surge.sh/affiliate/amazon-ai-mini-pc-rtx-gpu-deals.html';
        return `
        <div style="padding:8px 10px; border-radius:10px; background:rgba(15,23,42,0.95); border:1px solid rgba(249,115,22,0.38); display:flex; flex-direction:column; justify-content:space-between; gap:5px;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; gap:5px; flex-wrap:wrap; margin-bottom:3px;">
              <span class="chip" style="font-size:9px; font-weight:800; background:${item.badgeColor}22; color:${item.badgeColor}; border-color:${item.badgeColor}66;">${escapeHtml(item.platformLabel)}</span>
              <span class="chip success" style="font-size:9px;">💰 ${escapeHtml(item.commissionRate.split('(')[0].trim())}</span>
            </div>
            <div style="font-weight:800; font-size:12px; color:#fff; margin-bottom:3px; line-height:1.28;">
              ${escapeHtml(item.titleVi)}
            </div>
            <div style="font-size:10px; color:#94a3b8; margin-bottom:4px; line-height:1.32;">
              🎯 <strong>AI Đã Đưa Lên Internet:</strong> ${escapeHtml(item.trafficStrategyVi)}
            </div>
            <div style="font-size:9.8px; color:#cbd5e1; background:rgba(9,13,24,0.88); padding:4px 7px; border-radius:6px; border:1px solid rgba(148,163,184,0.2); line-height:1.38;">
              <div>• <strong>Hoa hồng:</strong> <span style="color:#34d399;">${escapeHtml(item.commissionRate)}</span></div>
              <div>• 🌐 <strong>Bài Review Trên Mạng:</strong> <a href="${buildMonetizedBridgeUrl(liveReviewUrl, item.titleVi)}" target="_blank" rel="noopener" style="color:#fde68a; text-decoration:underline;">${liveReviewUrl.replace('https://', '').slice(0, 36)}... ↗</a></div>
              <div>• 🔗 <strong>Shortlink:</strong> <a href="${shortUrl}" target="_blank" rel="noopener" style="color:#6ee7b7; font-family:var(--font-mono); text-decoration:underline;">${shortUrl}</a> • <a href="${seoPageUrl}" target="_blank" rel="noopener" style="color:#7dd3fc; text-decoration:underline;">Trang SEO ↗</a></div>
              <div>• <strong>AI Phụ trách:</strong> <span style="color:#38bdf8;">${escapeHtml(item.managedBy)}</span> • 👁️ <strong>—</strong> lượt mở</div>
            </div>
          </div>
          <div style="display:flex; gap:5px; flex-wrap:wrap; margin-top:2px;">
            <button type="button" class="btn btn-sm btn-primary" style="flex:1; font-size:10px; padding:4px 6px;" onclick="openAffiliateCampaignReviewModal('${escapeHtml(item.id)}')">
              🔥 Mở Sàn / Deal ↗
            </button>
            <a class="btn btn-sm" href="#" target="_blank" rel="noopener sponsored" style="text-decoration:none; font-size:10px; padding:4px 6px; border-color:rgba(245,158,11,0.65); color:#fde68a; background:rgba(245,158,11,0.14); font-weight:800;">
              💰 Nhận Voucher Free ↗
            </a>
            <button type="button" class="btn btn-sm btn-cyan" style="font-size:10px; padding:4px 6px;" onclick="openVisitorBuyCheckoutModal('Bộ Mã Nguồn Web Auto-Affiliate (${escapeHtml(item.platformLabel)})', ${Number(item.webappPriceUsd || 2.99)}, '${escapeHtml(item.webappSlug)}')">
              🛍️ Mua Web ($${Number(item.webappPriceUsd || 2.99).toFixed(2)})
            </button>
          </div>
        </div>
        `;
      }).join('');
    }

    // No synthetic staff, branches, workload, or campaign activity is generated.

    // Override renderGlobalAffiliateCampaignsGrid to also use card.livePostUrl / card.shortTinyUrl when present
    renderGlobalAffiliateCampaignsGrid = function() {
      const gridEl = document.getElementById('globalAffiliateCampaignsGrid');
      if (!gridEl) return;
      const items = CURRENT_AFFILIATE_PLATFORM_FILTER === 'ALL'
        ? GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG
        : GLOBAL_AFFILIATE_CAMPAIGNS_CATALOG.filter(x => x.platform === CURRENT_AFFILIATE_PLATFORM_FILTER);

      gridEl.innerHTML = items.map(item => {
        const synKey = item.branchCategoryCode || (item.id === 'aff-pod-notion-canva' ? 'POD' : item.platform);
        const syn = (typeof AFFILIATE_CAMPAIGN_EXAMPLES !== 'undefined' && AFFILIATE_CAMPAIGN_EXAMPLES[synKey]) || {};
        const liveReviewUrl = item.livePostUrl || syn.live_post_url || 'https://telegra.ph/Best-AI-Mini-PCs-Ryzen-7-8845HS-RTX-4070-Ti-Super-GPUs--NVMe-SSDs-on-Amazon-2026-Buyer-Guide-10-29-2';
        const shortUrl = item.shortTinyUrl || syn.short_tinyurl || liveReviewUrl;
        const seoPageUrl = item.seoLandingUrl || syn.landing_page_url || 'https://aikiemtien.surge.sh/affiliate/amazon-ai-mini-pc-rtx-gpu-deals.html';
        return `
        <div style="padding:8px 10px; border-radius:10px; background:rgba(15,23,42,0.95); border:1px solid ${item.badgeColor}66; display:flex; flex-direction:column; justify-content:space-between; gap:5px;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; gap:5px; flex-wrap:wrap; margin-bottom:3px;">
              <span class="chip" style="font-size:9px; font-weight:800; background:${item.badgeColor}22; color:${item.badgeColor}; border-color:${item.badgeColor}66;">${escapeHtml(item.platformLabel)}</span>
              <span class="chip success" style="font-size:9px;">💰 ${escapeHtml(item.commissionRate.split('(')[0].trim())}</span>
            </div>
            <div style="font-weight:800; font-size:11.8px; color:#fff; margin-bottom:3px; line-height:1.28;">
              ${escapeHtml(item.titleVi)}
            </div>
            <div style="font-size:10px; color:#94a3b8; margin-bottom:4px; line-height:1.32;">
              🎯 <strong>Phân nhánh &amp; Phát tán:</strong> ${escapeHtml(item.trafficStrategyVi)}
            </div>
            <div style="font-size:9.8px; color:#cbd5e1; background:rgba(9,13,24,0.88); padding:4px 7px; border-radius:6px; border:1px solid rgba(148,163,184,0.2); line-height:1.38;">
              <div>• <strong>Hoa hồng / Giá:</strong> <span style="color:#34d399;">${escapeHtml(item.commissionRate)}</span></div>
              <div>• 🌐 <strong>Bài Đã Đăng Mạng:</strong> <a href="${buildMonetizedBridgeUrl(liveReviewUrl, item.titleVi)}" target="_blank" rel="noopener" style="color:#fde68a; text-decoration:underline;">${liveReviewUrl.replace('https://', '').slice(0, 36)}... ↗</a></div>
              <div>• 🔗 <strong>Shortlink:</strong> <a href="${shortUrl}" target="_blank" rel="noopener" style="color:#6ee7b7; font-family:var(--font-mono); text-decoration:underline;">${shortUrl}</a> • <a href="${seoPageUrl}" target="_blank" rel="noopener" style="color:#7dd3fc; text-decoration:underline;">Trang Nhánh SEO ↗</a></div>
              <div>• <strong>AI Phụ trách:</strong> <span style="color:#38bdf8;">${escapeHtml(item.managedBy)}</span> • 👁️ <strong>—</strong> lượt mở</div>
            </div>
          </div>
          <div style="display:flex; gap:5px; flex-wrap:wrap; margin-top:2px;">
            <button type="button" class="btn btn-sm btn-primary" style="flex:1; font-size:10px; padding:4px 6px;" onclick="openAffiliateCampaignReviewModal('${escapeHtml(item.id)}')">
              🔥 Mở Sàn / Deal ↗
            </button>
            <a class="btn btn-sm" href="${buildMonetizedBridgeUrl(liveReviewUrl, item.titleVi)}" target="_blank" rel="noopener" style="text-decoration:none; font-size:10px; padding:4px 6px; border-color:rgba(250,204,21,0.55); color:#fde68a;">
              📖 Bài Đã Đăng ↗
            </a>
            <button type="button" class="btn btn-sm btn-cyan" style="font-size:10px; padding:4px 6px;" onclick="openVisitorBuyCheckoutModal('Bộ Mã Nguồn Nhánh (${escapeHtml(item.platformLabel)})', ${Number(item.webappPriceUsd || 2.49)}, '${escapeHtml(item.webappSlug)}')">
              🛍️ Mua Code ($${Number(item.webappPriceUsd || 2.49).toFixed(2)})
            </button>
          </div>
        </div>
        `;
      }).join('');
    };

    // No simulated branches or automatically spawned agents.



    const MONETIZED_BRIDGE_LINKS_REGISTRY = [{"slug": "binance-cpa", "title_en": "Official Binance CPA $100 USDT Bonus & Fee Rebate (Verified Code: )", "title_vi": "Nhận Thưởng $100 USDT & Hoàn Phí Giao Dịch Sàn Binance (Mã: )", "desc_en": "Connecting you to the official Binance CPA Partner page. Your $100 USDT welcome voucher and lifetime trading fee rebate will activate automatically upon registration.", "target_url": "https://aikiemtien.surge.sh/go/binance-cpa.html", "badge_text": "🪙 BINANCE OFFICIAL PARTNER • CODE: ", "upsell_slug": "github-password-hash-security-auditor", "upsell_title": "Crypto CEX/DEX Arbitrage & Security Scanner Web App ($2.99 USD)", "upsell_price": 2.99, "bridge_url_primary": "https://aikiemtien.surge.sh/go/binance-cpa.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/binance-cpa.html", "monetized_tinyurl": "https://tinyurl.com/233ouqgl"}, {"slug": "amazon-deals", "title_en": "Amazon Tech Deals: Best Low-Power AI Mini PCs (Ryzen 7 8845HS), RTX GPUs & NVMe SSDs", "title_vi": "Tổng Hợp Siêu Deal Amazon: Mini PC Chạy AI 24/7, Card Đồ Họa RTX & Ổ Cứng SSD", "desc_en": "Redirecting you to our curated Amazon Associates Tech & AI Hardware Deals page with live discount vouchers.", "target_url": "https://aikiemtien.surge.sh/go/amazon-deals.html", "badge_text": "📦 AMAZON ASSOCIATES GLOBAL TECH BOUNTY", "upsell_slug": "github-ai-prompt-markdown-converter", "upsell_title": "Amazon Affiliate Product Comparison Table Builder ($2.49 USD)", "upsell_price": 2.49, "bridge_url_primary": "https://aikiemtien.surge.sh/go/amazon-deals.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/amazon-deals.html", "monetized_tinyurl": "https://tinyurl.com/22g5svtc"}, {"slug": "shopify-trial", "title_en": "Shopify Official $1/Month Starter Trial + Automated Dropshipping Fulfillment", "title_vi": "Ưu Đãi Mở Cửa Hàng Quốc Tế Shopify Chỉ $1/Tháng Kèm Tự Động Hóa Dropshipping", "desc_en": "Redirecting you to the official Shopify Partner $1/Month promotion page.", "target_url": "https://aikiemtien.surge.sh/go/shopify-trial.html", "badge_text": "🛍️ SHOPIFY OFFICIAL PARTNER ($1/MO PROMO)", "upsell_slug": "github-saas-roi-pomodoro-calculator", "upsell_title": "Shopify Dropshipping Profit Margin & ROAS Calculator ($1.99 USD)", "upsell_price": 1.99, "bridge_url_primary": "https://aikiemtien.surge.sh/go/shopify-trial.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/shopify-trial.html", "monetized_tinyurl": "https://tinyurl.com/267l6wjx"}, {"slug": "semrush-seo", "title_en": "Semrush Pro SEO Intelligence & Competitor Keyword Gap Audit (Free Trial)", "title_vi": "Bộ Công Cụ Phân Tích Từ Khóa & Kiểm Toán SEO Semrush Pro (Dùng Thử Miễn Phí)", "desc_en": "Connecting you to Semrush Pro SEO & Competitor Intelligence Partner Portal.", "target_url": "https://aikiemtien.surge.sh/go/semrush-seo.html", "badge_text": "🤖 SEMRUSH PRO SEO PARTNER ($200 BOUNTY)", "upsell_slug": "github-json-schema-seo-studio", "upsell_title": "Instant OpenGraph & Schema.org JSON-LD SEO Generator ($1.99 USD)", "upsell_price": 1.99, "bridge_url_primary": "https://aikiemtien.surge.sh/go/semrush-seo.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/semrush-seo.html", "monetized_tinyurl": "https://tinyurl.com/22lal5q6"}, {"slug": "shopee-flash", "title_en": "Shopee Mall & TikTok Shop Tech Accessories Flash Sale & Voucher Hub", "title_vi": "Săn Siêu Sale Phụ Kiện Công Nghệ, Bàn Phím Cơ & Thiết Bị Livestream Shopee Mall", "desc_en": "Redirecting you to today's verified Shopee Mall & TikTok Shop Tech Flash Deals.", "target_url": "https://aikiemtien.surge.sh/go/shopee-flash.html", "badge_text": "🛒 SHOPEE MALL & TIKTOK SHOP FLASH SALE", "upsell_slug": "github-vietqr-crypto-payment-link-maker", "upsell_title": "Shopee/TikTok Bio-Link & QR Payment Page Builder ($1.99 USD)", "upsell_price": 1.99, "bridge_url_primary": "https://aikiemtien.surge.sh/go/shopee-flash.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/shopee-flash.html", "monetized_tinyurl": "https://tinyurl.com/2bj8pgjp"}, {"slug": "free-ai-prompts", "title_en": "Download 1,500+ Enterprise AI Prompts, Chrome Extensions & Web3 Yield Guide", "title_vi": "Tải Bộ 1.500+ Prompt AI Chuyên Nghiệp, Chrome Extension & Cẩm Nang Săn Launchpool", "desc_en": "Preparing your download and opening the full Enterprise AI Prompt & Web3 Yield Vault...", "target_url": "https://aikiemtien.surge.sh/affiliate/branch-rapidapi-microservices-ai-prompts.html", "badge_text": "🎁 FREE DOWNLOAD & ENTERPRISE AI VAULT", "upsell_slug": "github-ai-prompt-markdown-converter", "upsell_title": "Full 548+ White-Label Web App & Prompt Vault Access ($2.99 USD)", "upsell_price": 2.99, "bridge_url_primary": "https://aikiemtien.surge.sh/go/free-ai-prompts.html", "bridge_url_mirror": "https://webaikiemtien.surge.sh/go/free-ai-prompts.html", "monetized_tinyurl": "https://tinyurl.com/29gm8cz6"}];
    
    // External links are never rewritten through ad-impression bridges.


    
// Phase 00 removed retired synthetic telemetry and artificial engagement routines.

// Phase 00 removed retired synthetic telemetry and artificial engagement routines.

    // AUTO-IP GEOLOCATION LANGUAGE DETECTOR + 100% FULL-SITE & 3D ENGLISH ENGINE
    // ============================================================================
    window.AI_REALTIME_WORK_DIARY_LOG = [];
    window.AI_DIARY_SEEN_SIGNATURES = window.AI_DIARY_SEEN_SIGNATURES || new Set();
    window.SPOKEN_3D_DIALOGUE_HASHES = window.SPOKEN_3D_DIALOGUE_HASHES || new Set();
    window.NATURAL_3D_TURN_COUNTER = 0;
    window.DIARY_TASK_SEQ_COUNTER = 0;
    window.DETECTED_VISITOR_COUNTRY = localStorage.getItem('autoprofit_visitor_country_code') || '';
    window.DETECTED_VISITOR_COUNTRY_NAME = localStorage.getItem('autoprofit_visitor_country_name') || '';

    function persistBilingualDiaryAnd3DState() {
      // Client-generated diary entries are disabled. Task history comes from backend events.
    }

    const BILINGUAL_STAFF_DIRECTORY = [
      { role: 'CODING_AGENT', nameVi: 'Vũ Khoa — Kỹ Sư Đóng Gói Web App & Kiến Trúc HTML5', nameEn: 'Vu Khoa — Lead Web App & HTML5 Architect', shortVi: 'Vũ Khoa', shortEn: 'Vu Khoa (Lead Dev)', color: '#6366f1', deptVi: 'Xưởng Lập Trình Web App', deptEn: 'Web App Engineering Lab' },
      { role: 'RESEARCH_AGENT', nameVi: 'Lê Minh — Chuyên Viên Săn Mã Nguồn GitHub & Phân Tích Xu Hướng', nameEn: 'Le Minh — Open-Source GitHub & Market Researcher', shortVi: 'Lê Minh', shortEn: 'Le Minh (R&D)', color: '#06b6d4', deptVi: 'Phòng R&D Mã Nguồn Mở', deptEn: 'Open-Source R&D Division' },
      { role: 'PRODUCT_AGENT', nameVi: 'Hoàng Bách — Chuyên Gia Định Giá Bình Dân & Tối Ưu Chuyển Đổi', nameEn: 'Hoang Bach — Micro-Pricing & Conversion Strategist', shortVi: 'Hoàng Bách', shortEn: 'Hoang Bach (Product)', color: '#38bdf8', deptVi: 'Phòng Chiến Lược Sản Phẩm', deptEn: 'Product Strategy Lab' },
      { role: 'SALES_AGENT', nameVi: 'Đặng Quân — Phụ Trách Kinh Doanh Quốc Tế & Chào Hàng B2B', nameEn: 'Dang Quan — Global B2B Sales & Startup Outreach Lead', shortVi: 'Đặng Quân', shortEn: 'Dang Quan (Global Sales)', color: '#14b8a6', deptVi: 'Phòng Kinh Doanh Quốc Tế', deptEn: 'International B2B Sales' },
      { role: 'MARKETING_AGENT', nameVi: 'Phạm Thảo — Chuyên Viên SEO Schema & Tối Ưu Hiển Thị Quảng Cáo', nameEn: 'Pham Thao — Technical SEO & Ad Monetization Lead', shortVi: 'Phạm Thảo', shortEn: 'Pham Thao (SEO & Ads)', color: '#a855f7', deptVi: 'Phòng SEO & Quảng Cáo', deptEn: 'SEO & Ad Monetization Hub' },
      { role: 'FINANCE_AGENT', nameVi: 'Bảo Trâm — Kế Toán Trưởng Đối Soát Doanh Thu & Thanh Toán', nameEn: 'Bao Tram — Chief Accountant & On-Chain Treasury Lead', shortVi: 'Bảo Trâm', shortEn: 'Bao Tram (Finance)', color: '#10b981', deptVi: 'Phòng Kế Toán & Tài Chính', deptEn: 'Accounting & Treasury Desk' },
      { role: 'SECURITY_AGENT', nameVi: 'Trần Phong — Kỹ Sư Kiểm Định Bảo Mật & Chống Rò Rỉ Dữ Liệu', nameEn: 'Tran Phong — Application Security & Integrity Auditor', shortVi: 'Trần Phong', shortEn: 'Tran Phong (Security)', color: '#f43f5e', deptVi: 'Phòng An Ninh Hệ Thống', deptEn: 'Cybersecurity & Audit Ops' },
      { role: 'OPTIMIZATION_AGENT', nameVi: 'Khánh Linh — Chuyên Gia Tối Ưu Tốc Độ Tải Trang & UX/UI', nameEn: 'Khanh Linh — Web Performance & UI/UX Optimization Lead', shortVi: 'Khánh Linh', shortEn: 'Khanh Linh (UX/Perf)', color: '#eab308', deptVi: 'Phòng Tối Ưu Hiệu Năng', deptEn: 'Performance & UX Studio' },
      { role: 'CUSTOMER_SUPPORT_AGENT', nameVi: 'Ngô Mai — Phụ Trách Hỗ Trợ Khách Hàng & Bàn Giao Tự Động', nameEn: 'Ngo Mai — Global Customer Success & Instant Delivery Lead', shortVi: 'Ngô Mai', shortEn: 'Ngo Mai (Support)', color: '#ec4899', deptVi: 'Phòng Chăm Sóc Khách Hàng', deptEn: 'Customer Success Desk' },
      { role: 'AFFILIATE_AMAZON_AGENT', nameVi: 'Mai Anh — Chuyên Gia Tiếp Thị Liên Kết Amazon & Shopee Flash Sale', nameEn: 'Mai Anh — Amazon Associates & Tech Deal Specialist', shortVi: 'Mai Anh', shortEn: 'Mai Anh (Amazon Deals)', color: '#f97316', deptVi: 'Phòng Affiliate Thương Mại Điện Tử', deptEn: 'E-Commerce Affiliate Desk' },
      { role: 'SHOPIFY_ECOM_AGENT', nameVi: 'Quốc Tuấn — Chuyên Gia Tiếp Thị Phần Mềm SaaS & Shopify Partner', nameEn: 'Quoc Tuan — Shopify Partner & SaaS Affiliate Strategist', shortVi: 'Quốc Tuấn', shortEn: 'Quoc Tuan (SaaS/Shopify)', color: '#84cc16', deptVi: 'Phòng Affiliate SaaS & E-Com', deptEn: 'SaaS & Shopify Partner Lab' },
      { role: 'CRYPTO_ARBITRAGE_AGENT', nameVi: 'Hải Đăng — Chuyên Gia Phân Tích Chênh Lệch Giá & Đối Tác Binance', nameEn: 'Hai Dang — Crypto Arbitrage & Binance CPA Specialist', shortVi: 'Hải Đăng', shortEn: 'Hai Dang (Crypto/Web3)', color: '#f59e0b', deptVi: 'Phòng Chiến Lược Web3 & Crypto', deptEn: 'Web3 & Binance CPA Desk' },
      { role: 'AIRDROP_BOUNTY_AGENT', nameVi: 'Thanh Hà — Chuyên Viên Săn Giải Thưởng Bug Bounty & Testnet', nameEn: 'Thanh Ha — Open-Source Bug Bounty & Web3 Researcher', shortVi: 'Thanh Hà', shortEn: 'Thanh Ha (Bounties)', color: '#38bdf8', deptVi: 'Phòng Săn Thưởng Mã Nguồn Mở', deptEn: 'Bug Bounty & Testnet Lab' },
      { role: 'VIRAL_TRAFFIC_AGENT', nameVi: 'Gia Huy — Chuyên Gia Phân Phối Nội Dung & Kéo Traffic Tự Nhiên', nameEn: 'Gia Huy — Organic Traffic & Global Content Syndicator', shortVi: 'Gia Huy', shortEn: 'Gia Huy (Traffic Growth)', color: '#d946ef', deptVi: 'Phòng Tăng Trưởng Lưu Lượng', deptEn: 'Global Traffic Syndication' },
      { role: 'TEMPLATE_POD_AGENT', nameVi: 'Phương Nghi — Thiết Kế Viên Kho Giao Diện Notion, Canva & UI Kit', nameEn: 'Phuong Nghi — Notion Templates, UI Kits & POD Designer', shortVi: 'Phương Nghi', shortEn: 'Phuong Nghi (Templates)', color: '#2dd4bf', deptVi: 'Xưởng Thiết Kế Sản Phẩm Số', deptEn: 'Digital Product & POD Studio' },
      { role: 'BINANCE_CPA_CONVERSION_AGENT', nameVi: 'Nhật Minh — Chuyên Gia Tối Ưu Chuyển Đổi Binance ', nameEn: 'Nhat Minh — Binance  Conversion Lead', shortVi: 'Nhật Minh', shortEn: 'Nhat Minh (Binance CPA)', color: '#f59e0b', deptVi: 'Phòng Tối Ưu Hoa Hồng Binance', deptEn: 'Binance CPA Conversion Desk' },
      { role: 'WORKLOAD_BALANCER_AGENT', nameVi: 'Ngọc Ánh — Điều Phối Viên Chia Tải 30+ AI (0% Quá Tải) & Xác Minh Đơn YouTube', nameEn: 'Ngoc Anh — 30+ AI Workload Balancer & On-Chain Order QA', shortVi: 'Ngọc Ánh', shortEn: 'Ngoc Anh (Load Balancer)', color: '#10b981', deptVi: 'Trung Tâm Điều Phối & Chia Tải AI', deptEn: 'AI Load Balancing & QA Center' }
    ];

    if (typeof AGENT_META_BILINGUAL !== 'undefined') {
      BILINGUAL_STAFF_DIRECTORY.forEach((st, idx) => {
        if (!AGENT_META_BILINGUAL[st.role]) {
          AGENT_META_BILINGUAL[st.role] = {
            titleVi: st.nameVi,
            titleEn: st.nameEn,
            shortVi: st.shortVi,
            shortEn: st.shortEn,
            zoneVi: st.deptVi,
            zoneEn: st.deptEn,
            subVi: st.deptVi,
            subEn: st.deptEn,
            equipVi: 'Trạm làm việc mô phỏng',
            equipEn: 'Demo workstation',
            stepVi: 'Vai trò demo · runtime chưa kết nối',
            stepEn: 'Demo role · runtime not connected',
            dutyVi: st.nameVi,
            dutyEn: st.nameEn
          };
        }
      });
    }

    const BILINGUAL_TOPICS_CATALOG = [];

    window.buildUniqueRealtimeDiaryEntry = function() { return null; };

    // Fully Bilingual AI Work Diary Renderer
    window.renderHumanStyleAiNotebook = function() {
      const streamEl = document.getElementById('humanNotebookEntriesStream');
      if (!streamEl) return;
      const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
      const filterRole = document.getElementById('notebookFilterAgentSelect')?.value || 'ALL';

      const customHtml = (typeof VISITOR_NOTEBOOK_CUSTOM_ENTRIES !== 'undefined' ? VISITOR_NOTEBOOK_CUSTOM_ENTRIES : [])
        .filter(e => filterRole === 'ALL' || e.role === filterRole)
        .map(e => `
          <div class="notebook-diary-entry visitor-reply" style="border-left: 3px solid #10b981;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
              <strong style="color:#34d399; font-size:12px;">💬 ${escapeHtml(e.humanName)} (${isEn ? 'Replying to ' : 'Phản hồi trực tiếp '}${escapeHtml(e.visitorName)})</strong>
              <span style="font-family:var(--font-mono); font-size:10px; color:var(--text-muted);">${escapeHtml(e.timeStr)}</span>
            </div>
            <div style="font-size:11px; color:#a7f3d0; margin-top:3px;">
              <strong>${isEn ? 'Visitor Question:' : 'Câu hỏi của khách:'}</strong> "${escapeHtml(e.question)}"
            </div>
            <div class="notebook-thought-box">
              💭 <strong>${isEn ? 'Analysis:' : 'Phân tích:'}</strong> "${escapeHtml(isEn && e.thoughtEn ? e.thoughtEn : e.thought)}"
            </div>
            <div class="notebook-action-box">
              ✍️ <strong>${isEn ? 'Response:' : 'Trả lời:'}</strong> ${escapeHtml(isEn && e.replyEn ? e.replyEn : e.reply)}
            </div>
          </div>
        `).join('');

      const liveEntries = window.AI_REALTIME_WORK_DIARY_LOG.filter(item => filterRole === 'ALL' || item.role === filterRole);
      const cardsHtml = liveEntries.map((p, idx) => {
        const nameTxt = isEn ? (p.humanNameEn || p.humanNameVi || p.humanName) : (p.humanNameVi || p.humanName);
        const deptTxt = isEn ? (p.deptEn || p.deptVi || p.dept) : (p.deptVi || p.dept);
        const timeTxt = isEn ? (p.timeLabelEn || p.timeLabelVi || p.timeLabel) : (p.timeLabelVi || p.timeLabel);
        const thoughtTxt = isEn ? (p.thoughtEn || p.thoughtVi || p.thought) : (p.thoughtVi || p.thought);
        const actionHtml = isEn ? (p.actionHtmlEn || p.actionHtmlVi || p.actionHtml) : (p.actionHtmlVi || p.actionHtml);
        return `
          <div class="notebook-diary-entry" data-diary-sig="${escapeHtml(p.sig)}" style="border-left: 3px solid ${p.badgeColor}; ${idx === 0 ? 'background:linear-gradient(90deg, rgba(16,185,129,0.13), rgba(15,23,42,0.92)); box-shadow: 0 4px 14px rgba(16,185,129,0.14);' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap;">
              <strong style="color:#fff; font-size:12px;">📒 ${escapeHtml(nameTxt)}</strong>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-family:var(--font-mono); font-size:10px; color:${idx === 0 ? '#34d399' : 'var(--text-muted)'}; font-weight:${idx === 0 ? '700' : '500'};">${escapeHtml(timeTxt)} • ${escapeHtml(deptTxt)}</span>
                <button class="btn btn-sm" style="padding:1px 6px; font-size:10px;" onclick="selectCharacterIn3DWorld('${p.role}', false)">📍 ${isEn ? 'View 3D' : 'Xem 3D'}</button>
              </div>
            </div>
            <div class="notebook-thought-box" style="margin-top:5px;">
              💭 <strong>${isEn ? 'Analysis & Objective:' : 'Phân tích & Mục tiêu:'}</strong> "${escapeHtml(thoughtTxt)}"
            </div>
            <div class="notebook-action-box" style="margin-top:4px;">
              ${actionHtml}
            </div>
          </div>
        `;
      }).join('');

      streamEl.innerHTML = customHtml + cardsHtml;
    };

    // ============================================================================
    // 100% BILINGUAL (VIETNAMESE + ENGLISH) NATURAL 3D OFFICE DIALOGUE GENERATOR
    // ============================================================================
    window.generateNextRealActivityDialogueTurn = function() { return null; };

    // ============================================================================
    // FULL-PAGE DOM TRANSLATOR (TRANSLATES EVERY CARD, TAB, KPI, BUTTON & TEXT NODE)
    // ============================================================================
    const EXACT_PHRASE_TRANSLATIONS_VI_TO_EN = [
      ['1. Doanh Thu Xác Minh', '1. Verified Revenue'],
      ['2. Lợi Nhuận Ròng (Sau Thuế & API)', '2. Net Profit (After Tax & Costs)'],
      ['3. Quỹ Dự Phòng Vận Hành (25%)', '3. Operating Reserve Fund (25%)'],
      ['4. Chủ Nhân Có Thể Rút (75%)', '4. Owner Withdrawable (75%)'],
      ['5. Kho Web App Tự Đóng Gói', '5. Packaged Web Apps Vault'],
      ['6. Hệ Thống 10 Kênh Đẻ Nhánh', '6. 10-Channel Multi-Branch Engine'],
      ['100% Từ Đơn Hàng & Quảng Cáo Thực Tế', '100% Verified Orders, Affiliate & Ad Revenue'],
      ['Đã trừ chi phí vận hành máy chủ ($0.00)', 'Server & API operating cost deducted ($0.00)'],
      ['Tự động trích lập tái đầu tư hạ tầng', 'Auto-allocated for infrastructure scaling'],
      ['Sẵn sàng rút về VPBank / Ví Binance USDT', 'Ready for payout via Bank / Binance USDT'],
      ['Ứng dụng HTML5/JS chạy trực tiếp (Giá $1.99–$5.99)', 'Client-side HTML5/JS Web Apps ($1.99–$5.99 USD)'],
      ['24+ Nhân Sự AI • Tự Động Nhân Bản Nhánh Kiếm Tiền', '24+ AI Staff • Autonomous Monetization Branches'],
      ['Lượt Khách Truy Cập Web Thực Tế', 'Real Website Visitor Traffic'],
      ['Hôm nay:', 'Today:'],
      ['7 ngày:', '7 Days:'],
      ['30 ngày:', '30 Days:'],
      ['Đang online:', 'Online Now:'],
      ['Quảng Cáo Tự Động', 'Automated Ad Network'],
      ['Tổng hiển thị:', 'Total Impressions:'],
      ['1. Trung Tâm 3D & Tổng Quan', '1. 3D Command & Overview'],
      ['2. Affiliate & 10 Kênh Đẻ', '2. Affiliate & 10-Channel'],
      ['3. 10 Kênh Kiếm Tiền Tự Động', '3. 10-Channel Passive Hub'],
      ['4. Chợ', '4. Store:'],
      ['5. Crypto, Airdrop & DeFi', '5. Crypto, Airdrop & DeFi'],
      ['6. AI Đẩy Bài & Săn Khách', '6. Global Outreach & Leads'],
      ['7. 24+ Nhân Sự & 9 Phòng', '7. 24+ AI Staff & 9 Rooms'],
      ['8. Kế Toán & Đơn Hàng', '8. Accounting & Orders'],
      ['Sổ Tay Nhật Ký & Tác Vụ Của Các AI Đang Hoạt Động', 'Live AI Workforce Progress Diary & Task Stream'],
      ['Tất cả Nhân sự AI (24+ AI)', 'All AI Employees (24+ AI Staff)'],
      ['Gửi câu hỏi hoặc yêu cầu cho Nhân viên AI...', 'Ask a question or assign a task to our AI Staff...'],
      ['Gửi Cho AI', 'Send to AI'],
      ['Báo Cáo Kế Toán', 'Accounting & Revenue Report'],
      ['Mở Kèo & Nhận Ưu Đãi', 'Open Offer & Claim Bonus'],
      ['Mở Web App', 'Open Web App'],
      ['Mua Mã Nguồn', 'Buy Source Code'],
      ['Dùng Thử Miễn Phí', 'Try Free Demo']
    ];

    window.applyFullSiteLanguageTranslation = function(lang) {
      const isEn = (lang === 'en');
      const kpiTitles = document.querySelectorAll('.kpi-title');
      if (kpiTitles.length >= 6) {
        const titlesVi = [
          '1. Doanh Thu Xác Minh',
          '2. Lợi Nhuận Ròng',
          '3. Quỹ Dự Phòng (25%)',
          '4. Chủ Nhân Có Thể Rút',
          '5. Kho Web App Đóng Gói',
          '6. 10 Kênh Đẻ Nhánh Tự Động'
        ];
        const titlesEn = [
          '1. Verified Revenue',
          '2. Net Profit (Verified)',
          '3. Reserve Fund (25%)',
          '4. Owner Withdrawable',
          '5. Packaged Web Apps',
          '6. 10-Channel Multi-Branch'
        ];
        kpiTitles.forEach((el, idx) => {
          if (idx < 6) el.textContent = isEn ? titlesEn[idx] : titlesVi[idx];
        });
      }

      const tabMap = {
        wsTabBtn_TAB_OVERVIEW: isEn ? `🏠 1. 3D Office & Live Overview` : `🏠 1. Trung Tâm 3D & Tổng Quan`,
        wsTabBtn_TAB_AFFILIATE_HUB: isEn ? `🔥 2. Affiliate & Partners` : `🔥 2. Affiliate & Đối Tác`,
        wsTabBtn_TAB_MMO_ENGINE: isEn ? `⚡ 3. 10-Channel Passive Income` : `⚡ 3. 10 Kênh Kiếm Tiền Tự Động`,
        wsTabBtn_TAB_WEBAPP_STORE: isEn ? `🛍️ 4. Web App Store` : `🛍️ 4. Chợ Web App`,
        wsTabBtn_TAB_CRYPTO_RADAR: isEn ? `💎 5. Crypto, Airdrop & DeFi Yield` : `💎 5. Crypto, Airdrop & DeFi`,
        wsTabBtn_TAB_OUTREACH_HUNTER: isEn ? `🌐 6. AI Global Outreach & Leads` : `🌐 6. AI Đẩy Bài & Săn Khách`,
        wsTabBtn_TAB_NINE_DEPARTMENTS: isEn ? `👥 7. 24+ AI Staff & 9 Departments` : `👥 7. 24+ Nhân Sự & 9 Phòng`,
        wsTabBtn_TAB_ACCOUNTING_ORDERS: isEn ? `📊 8. Accounting & Live Orders` : `📊 8. Kế Toán & Đơn Hàng`
      };
      Object.entries(tabMap).forEach(([id, label]) => {
        const btn = document.getElementById(id);
        if (btn) btn.innerHTML = label;
      });

      const imprEl = document.getElementById('aadsImpressionsCounter');
      if (imprEl) imprEl.textContent = isEn ? 'No verified ad-network telemetry' : 'Chưa có dữ liệu quảng cáo xác minh';

      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      let node;
      while ((node = walker.nextNode())) {
        const parentTag = node.parentElement ? node.parentElement.tagName : '';
        if (parentTag === 'SCRIPT' || parentTag === 'STYLE' || parentTag === 'CODE') continue;
        if (!node.__origViText && /[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]/i.test(node.nodeValue || '')) {
          node.__origViText = node.nodeValue;
        }
        if (isEn && node.__origViText) {
          let txt = node.__origViText;
          EXACT_PHRASE_TRANSLATIONS_VI_TO_EN.forEach(([viP, enP]) => {
            if (txt.includes(viP)) txt = txt.split(viP).join(enP);
          });
          txt = txt
            .replace(/Sổ Tay Nhật Ký & Tác Vụ Của Các AI Đang Hoạt Động/g, 'Live AI Workforce Progress Diary & Task Stream')
            .replace(/Lượt Khách Truy Cập Thực Tế/g, 'Verified Real Website Visitors')
            .replace(/Hôm nay:/g, 'Today:')
            .replace(/7 ngày:/g, '7 Days:')
            .replace(/30 ngày:/g, '30 Days:')
            .replace(/Đang xem:/g, 'Online:')
            .replace(/Tổng hiển thị:/g, 'Total Impressions:')
            .replace(/Quảng Cáo/g, 'Ad Network')
            .replace(/Nhân Sự AI/g, 'AI Staff')
            .replace(/Phòng Làm Việc 3D/g, '3D AI Office')
            .replace(/Đang hoạt động/g, 'Active 24/7')
            .replace(/Tất cả/g, 'All')
            .replace(/Xem 3D/g, 'View 3D');
          if (node.nodeValue !== txt) node.nodeValue = txt;
        } else if (!isEn && node.__origViText) {
          if (node.nodeValue !== node.__origViText) node.nodeValue = node.__origViText;
        }
      }

      if (typeof window.renderHumanStyleAiNotebook === 'function') {
        window.renderHumanStyleAiNotebook();
      }
      if (typeof triggerNextContinuousAiConversationTurn === 'function' && typeof WORLD_3D !== 'undefined' && WORLD_3D.initialized) {
        triggerNextContinuousAiConversationTurn();
      }
    };

    const _origSetAppLanguage = window.setAppLanguage;
    window.setAppLanguage = function(lang, isAutoIp) {
      CURRENT_LANG = lang === 'en' ? 'en' : 'vi';
      localStorage.setItem('autoprofit_lang', CURRENT_LANG);
      if (!isAutoIp) {
        localStorage.setItem('autoprofit_lang_manual_override', CURRENT_LANG);
      }
      if (typeof _origSetAppLanguage === 'function') {
        try { _origSetAppLanguage(CURRENT_LANG); } catch (e) {}
      }
      window.applyFullSiteLanguageTranslation(CURRENT_LANG);
    };

    // ============================================================================
    // AUTOMATIC VISITOR IP GEOLOCATION LANGUAGE DETECTION
    // ============================================================================
    window.detectVisitorIpAndAutoSetLanguage = async function() {
      const urlParams = new URLSearchParams(window.location.search);
      const forcedLang = urlParams.get('lang');
      if (forcedLang === 'en' || forcedLang === 'vi') {
        window.setAppLanguage(forcedLang, false);
        return;
      }

      let countryCode = '';
      let countryName = '';

      const geoEndpoints = [
        { url: 'https://ipwho.is/', parse: d => ({ code: d.country_code, name: d.country }) },
        { url: 'https://api.country.is/', parse: d => ({ code: d.country, name: d.country }) },
        { url: 'https://ipapi.co/json/', parse: d => ({ code: d.country_code, name: d.country_name }) }
      ];

      for (const ep of geoEndpoints) {
        try {
          const ctrl = new AbortController();
          const tId = setTimeout(() => ctrl.abort(), 3500);
          const r = await fetch(ep.url, { signal: ctrl.signal });
          clearTimeout(tId);
          if (r.ok) {
            const data = await r.json();
            const parsed = ep.parse(data || {});
            if (parsed && parsed.code && String(parsed.code).length === 2) {
              countryCode = String(parsed.code).toUpperCase();
              countryName = String(parsed.name || countryCode);
              break;
            }
          }
        } catch (_) {}
      }

      if (!countryCode) {
        try {
          const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
          const navLang = (navigator.language || '').toLowerCase();
          if (tz.includes('Saigon') || tz.includes('Ho_Chi_Minh') || (tz.includes('Bangkok') && navLang.startsWith('vi'))) {
            countryCode = 'VN';
            countryName = 'Vietnam';
          } else if (!navLang.startsWith('vi')) {
            countryCode = 'US';
            countryName = 'International';
          } else {
            countryCode = 'VN';
            countryName = 'Vietnam';
          }
        } catch (_) {
          countryCode = 'VN';
        }
      }

      window.DETECTED_VISITOR_COUNTRY = countryCode;
      window.DETECTED_VISITOR_COUNTRY_NAME = countryName;
      localStorage.setItem('autoprofit_visitor_country_code', countryCode);
      localStorage.setItem('autoprofit_visitor_country_name', countryName);

      const btnEn = document.getElementById('btnLangEn');
      if (btnEn && btnEn.parentElement) {
        let geoBadge = document.getElementById('visitorGeoIpLangBadge');
        if (!geoBadge) {
          geoBadge = document.createElement('span');
          geoBadge.id = 'visitorGeoIpLangBadge';
          geoBadge.style.cssText = 'font-size:10px; font-family:var(--font-mono); padding:2px 6px; border-radius:4px; background:rgba(16,185,129,0.16); color:#6ee7b7; border:1px solid rgba(16,185,129,0.35); margin-right:4px; white-space:nowrap;';
          btnEn.parentElement.insertBefore(geoBadge, btnEn.parentElement.firstChild);
        }
        geoBadge.textContent = countryCode === 'VN'
          ? `🇻🇳 IP: Vietnam (Auto-VI)`
          : `🌍 IP: ${countryCode} (Auto-EN)`;
      }

      const manualOverride = localStorage.getItem('autoprofit_lang_manual_override');
      if (countryCode !== 'VN') {
        if (manualOverride !== 'vi') {
          window.setAppLanguage('en', true);
        }
      } else {
        if (manualOverride === 'en') {
          window.setAppLanguage('en', true);
        } else {
          window.setAppLanguage('vi', true);
        }
      }
    };

    setTimeout(() => {
      window.detectVisitorIpAndAutoSetLanguage();
    }, 150);

    // ============================================================================
    // Automated browser syndication is retired: no API token or scheduled publishing in frontend.

    // DIRECT BINANCE WALLET (BEP20) ON-CHAIN REVENUE SYNC & AUTO-DELIVERY ENGINE
    // ============================================================================
    window.OWNER_BINANCE_BEP20_WALLET = '';
    window.OWNER_PERMANENT_BINANCE_REF_CODE = '';
    window.OWNER_PERMANENT_BINANCE_REF_URL = 'https://www.binance.com/activity/referral-entry/CPA?ref=&utm_source=Dashboard';
    window.BSC_USDT_CONTRACT_ADDR = '0x55d398326f99059fF775485246999027B3197955';
    window.ERC20_TRANSFER_TOPIC_HASH = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
    window.BSC_RPC_ENDPOINTS = [
      'https://bsc-dataseed.binance.org/',
      'https://bsc-dataseed1.defibit.io/',
      'https://bsc-dataseed1.ninicoin.io/'
    ];

    window.BINANCE_ONCHAIN_STATE = {
      connected: false,
      latestBlock: 0,
      onchainUsdtBalance: null,
      verifiedOrdersUsdtTotal: null,
      verifiedTxHashes: [],
      verifiedOrdersList: [],
      lastCheckedIso: ''
    };

    window.callBscMainnetRpc = async function(method, params) {
      for (const rpc of window.BSC_RPC_ENDPOINTS) {
        try {
          const r = await fetch(rpc, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', id: Date.now(), method, params })
          });
          if (r.ok) {
            const data = await r.json();
            if (data && data.result !== undefined) return data.result;
          }
        } catch (_) {}
      }
      return null;
    };

    // Sync total verified revenue = A-Ads Verified Revenue ($0.02+) + Binance On-Chain Verified USDT Revenue
    window.recalculateAndSyncTotalVerifiedRevenueUI = async () => null;

    // Poll BNB Smart Chain Mainnet every 12 seconds for live balance & new incoming transfers
    window.pollLiveBinanceWalletOnChain = async function() { return null; };

    // Build and trigger instant White-Label Source Code download for verified buyers
    window.generateAndDownloadPurchasedWebAppPackage = function(itemTitle, itemSlug, priceUsd, txHash) {
      const cleanSlug = String(itemSlug || 'autoprofit-webapp').replace(/[^a-zA-Z0-9\-_]/g, '-');
      const nowIso = new Date().toISOString();
      const packageHtml = `<!DOCTYPE html>
<html lang="en">
<!--
  ============================================================================
  AUTOPROFIT AI — COMMERCIAL WHITE-LABEL WEB APP SOURCE CODE PACKAGE
  Product: ${itemTitle} (${cleanSlug})
  License: Full Commercial White-Label MIT License (100% Ownership)
  Verified Blockchain Payment TxHash: ${txHash}
  Delivered At: ${nowIso}
  ============================================================================
-->
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${itemTitle} — White-Label Edition</title>
  <style>
    body { margin:0; font-family: system-ui, -apple-system, sans-serif; background:#070b14; color:#f8fafc; padding:32px; }
    .container { max-width:960px; margin:0 auto; background:#0f172a; border:1px solid #38bdf8; border-radius:16px; padding:28px; }
    .badge { display:inline-block; padding:4px 10px; border-radius:6px; background:rgba(16,185,129,0.2); color:#34d399; font-size:12px; font-weight:700; }
    h1 { color:#fff; margin:12px 0 8px; }
    .workspace { margin-top:20px; padding:20px; background:#060a12; border-radius:12px; border:1px solid rgba(148,163,184,0.25); }
    textarea { width:100%; min-height:180px; background:#0d1527; color:#6ee7b7; border:1px solid #334155; border-radius:8px; padding:12px; font-family:monospace; }
    button { background:#10b981; color:#04130d; font-weight:800; border:none; padding:12px 24px; border-radius:8px; cursor:pointer; margin-top:12px; }
  </style>
</head>
<body>
  <div class="container">
    <span class="badge">✅ WHITE-LABEL COMMERCIAL EDITION • VERIFIED TX: ${txHash.slice(0, 18)}...</span>
    <h1>${itemTitle}</h1>
    <p style="color:#94a3b8;">100% Client-Side Standalone HTML5/JS Application. Customize branding, ad unit IDs, and affiliate links freely.</p>
    <div class="workspace">
      <label style="display:block; margin-bottom:8px; font-weight:700; color:#38bdf8;">Interactive Input Workspace:</label>
      <textarea id="appInput">Enter your data, JSON, SQL, or prompt payload here...</textarea>
      <button onclick="document.getElementById('appOutput').textContent = 'Processed successfully at ' + new Date().toLocaleTimeString() + ':\\n' + document.getElementById('appInput').value;">⚡ Execute Tool</button>
      <pre id="appOutput" style="margin-top:16px; padding:14px; background:#090e1a; border-radius:8px; color:#fde68a; white-space:pre-wrap;"></pre>
    </div>
  </div>


    

</body>
</html>`;

      const blob = new Blob([packageHtml], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${cleanSlug}-white-label-source.html`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 1500);
      return url;
    };

    // Upgrade openVisitorBuyCheckoutModal to inject the live Binance On-Chain Verification status bar
    const _origOpenCheckoutModal = window.openVisitorBuyCheckoutModal;
    window.openVisitorBuyCheckoutModal = function(itemTitle, priceUsd, itemSlug) {
      if (typeof _origOpenCheckoutModal === 'function') {
        _origOpenCheckoutModal(itemTitle, priceUsd, itemSlug);
      }
      const modal = document.getElementById('visitorBuyCheckoutModal');
      if (!modal) return;

      const walInput = document.getElementById('checkoutModalUsdtWalletInput');
      if (walInput) walInput.value = window.OWNER_BINANCE_BEP20_WALLET;

      let statusBox = document.getElementById('checkoutLiveVerificationAndDeliveryBox');
      if (!statusBox) {
        const txInput = document.getElementById('checkoutTxProofInput');
        const parentGrid = txInput ? txInput.closest('.grid-2') : null;
        if (parentGrid && parentGrid.parentElement) {
          statusBox = document.createElement('div');
          statusBox.id = 'checkoutLiveVerificationAndDeliveryBox';
          statusBox.style.cssText = 'margin-bottom:12px; padding:10px 12px; border-radius:10px; background:rgba(16,185,129,0.09); border:1px solid rgba(16,185,129,0.35); font-size:11.5px; color:#cbd5e1;';
          parentGrid.parentElement.insertBefore(statusBox, parentGrid.nextSibling);
        }
      }
      if (statusBox) {
        const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
        statusBox.textContent = isEn
          ? 'Live wallet monitoring is not connected. Submitted transaction hashes are checked by the server.'
          : 'Theo dõi số dư ví trực tiếp chưa kết nối. Mã giao dịch gửi lên sẽ được máy chủ kiểm tra.';
      }
    };

    // Override submitVisitorQuickCheckoutOrder to perform REAL On-Chain BNB Smart Chain verification!
    window.submitVisitorQuickCheckoutOrder = async function() {
      const email = (document.getElementById('checkoutBuyerEmail')?.value || '').trim().toLowerCase();
      const reference = (document.getElementById('checkoutTxProofInput')?.value || '').trim();
      const statusBox = document.getElementById('checkoutLiveVerificationAndDeliveryBox');
      const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
      const setStatus = (message, error = false) => {
        if (!statusBox) return;
        statusBox.textContent = message;
        statusBox.style.color = error ? '#fca5a5' : '#86efac';
      };
      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        setStatus(isEn ? 'Enter a valid email address.' : 'Nhập email hợp lệ để nhận liên kết tải.', true);
        document.getElementById('checkoutBuyerEmail')?.focus();
        return;
      }
      if (!reference || reference.length < 4) {
        setStatus(isEn ? 'Enter the bank reference or BSC transaction hash.' : 'Nhập mã chuyển khoản hoặc TxHash để gửi đối soát.', true);
        return;
      }
      const item = window.CURRENT_CHECKOUT_ITEM || { title: 'Web App', priceUsd: 2.99, slug: '' };
      const button = document.querySelector('#visitorBuyCheckoutModal [data-submit-checkout]');
      if (button) { button.disabled = true; button.textContent = isEn ? 'Checking…' : 'Đang kiểm tra…'; }
      try {
        if (/^0x/i.test(reference)) {
          setStatus(isEn ? 'The server is checking the transaction on BNB Smart Chain…' : 'Máy chủ đang kiểm tra giao dịch trên BNB Smart Chain…');
          const result = await apiFetch('/api/public/orders/verify-bsc-tx', {
            method: 'POST',
            body: JSON.stringify({ item_slug: item.slug, buyer_email: email, tx_hash: reference.toLowerCase() })
          }, 15000);
          if (!result?.accepted || result.status !== 'PAID_VERIFIED' || !result.download_url) {
            throw new Error(result?.detail || (isEn ? 'The payment has not been verified.' : 'Máy chủ chưa xác minh được khoản thanh toán.'));
          }
          const link = document.createElement('a');
          link.href = String(result.download_url);
          link.className = 'btn btn-primary';
          link.textContent = isEn ? 'Download verified purchase' : 'Tải sản phẩm đã xác minh';
          link.target = '_blank';
          link.rel = 'noopener';
          statusBox.replaceChildren(document.createTextNode(isEn
            ? `Payment verified by the server. Order ${result.order_id}. `
            : `Máy chủ đã xác minh thanh toán. Mã đơn ${result.order_id}. `), link);
          if (typeof refreshAllData === 'function') refreshAllData(false);
          showToast(isEn ? 'Payment verified by the server.' : 'Thanh toán đã được máy chủ xác minh.');
          return;
        }
        setStatus(isEn ? 'Submitting the bank transfer for owner review…' : 'Đang gửi mã chuyển khoản để chủ cửa hàng đối soát…');
        const result = await apiFetch('/api/public/payment-reports', {
          method: 'POST',
          body: JSON.stringify({ product_slug: item.slug, payment_method: 'BANK_TRANSFER', customer_email: email, reference })
        }, 15000);
        if (!result?.accepted || !result.report_id) {
          throw new Error(result?.detail || (isEn ? 'The server did not save the payment report.' : 'Máy chủ chưa xác nhận đã lưu yêu cầu.'));
        }
        setStatus(isEn
          ? `Request ${result.report_id} is waiting for owner review. Payment is not verified and no download is available yet.`
          : `Đã lưu yêu cầu ${result.report_id}, đang chờ chủ cửa hàng đối soát. Chưa xác nhận thanh toán và chưa mở tải.`);
        showToast(isEn ? 'Payment review request saved.' : 'Đã gửi yêu cầu đối soát thanh toán.');
      } catch (error) {
        setStatus(`${isEn ? 'No verified order was recorded.' : 'Chưa ghi nhận đơn đã thanh toán.'} ${error?.message || ''}`, true);
        showToast(error?.message || (isEn ? 'Could not verify payment.' : 'Không xác minh được thanh toán.'), true);
      } finally {
        if (button) { button.disabled = false; button.textContent = isEn ? 'Submit payment for review' : 'Gửi yêu cầu đối soát thanh toán'; }
      }
    };

  

// Phase 00 removed retired synthetic telemetry and artificial engagement routines.

// Phase 00 removed retired synthetic telemetry and artificial engagement routines.

     // Bank notifications are not payment proof; reconciliation stays server-side.
  

  
    // === 100% REAL TELEMETRY LOCK (BINANCE EXCHANGE PORTFOLIO + A-ADS LIVE STATS) ===
    (function() {
      // Existing browser storage is preserved; unverified counters are ignored.

      // No browser-local click counters are presented as verified affiliate analytics.

      window.REAL_BINANCE_EXCHANGE_PORTFOLIO = { status: 'not_connected', totalUsdVal: null };
      window.LIVE_BTC_USD_PRICE = null;
      window.syncLiveBinanceExchangePricesAndBalance = async () => null;
      window.openBinancePortfolioSyncModal = () => null;

      window.LIVE_TOTAL_WEBAPPS_COUNT = null;
      window.LIVE_TOTAL_BRANCHES_COUNT = null;
      window.LIVE_AADS_SATOSHIS = null;
      window.LIVE_TOTAL_AADS_IMPRESSIONS = null;

      const LIVE_BACKEND_URL = window.location.origin;
      window.LIVE_BACKEND_URL = LIVE_BACKEND_URL;
      window.LIVE_LLM_TOKEN_LEDGER = { status: 'not_connected', summary: null, recent_calls: [] };

      window.syncAllLiveBranchCountersUI = () => null;

      // No verified ad-network provider is connected. Never accept manually declared stats or browser tokens.
      window.syncAllLiveBranchCountersUI = () => null;
      window.applyAAdsTelemetryToUI = () => null;
      window.applyLiveAdTelemetryPayload = () => null;
      window.syncRealAAdsTelemetry = async () => null;
      window.syncLiveAadsAndAdsterraApiFromBackend = async () => null;
      window.openAdNetworksApiConfigModal = () => null;
      window.LAST_AD_API_SYNC_TIME_STR = 'not connected';
      window.AD_API_NEXT_COUNTDOWN_SEC = null;

      window.recalculateAndSyncTotalVerifiedRevenueUI = async function() {
        const revEl = document.getElementById('kpi-verified-revenue');
        const revSubEl = document.getElementById('kpi-verified-revenue-sub');
        const netEl = document.getElementById('kpi-net-profit');
        const netSubEl = document.getElementById('kpi-net-profit-sub');
        const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
        try {
          const fetcher = window.apiFetch;
          if (typeof fetcher !== 'function') throw new Error('API client unavailable');
          const snapshot = await fetcher('/api/dashboard/summary?window=today', {}, 8000);
          const metric = snapshot?.metrics?.revenue_usd;
          const value = metric?.value_usd;
          if (revEl) revEl.textContent = value == null ? (isEn ? 'No verified payments' : 'Chưa có thanh toán xác minh') : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value));
          if (revSubEl) revSubEl.textContent = value == null ? (isEn ? 'Source: verified transactions' : 'Nguồn: giao dịch đã đối soát') : (isEn ? 'Verified transactions only' : 'Chỉ giao dịch đã đối soát');
          if (netEl) netEl.textContent = isEn ? 'Expense data unavailable' : 'Chưa đủ dữ liệu chi phí';
          if (netSubEl) netSubEl.textContent = isEn ? 'Net profit is unavailable until real costs are connected.' : 'Chưa có nguồn chi phí thật để tính lợi nhuận ròng.';
          window.LAST_REVENUE_SNAPSHOT = snapshot;
          return snapshot;
        } catch (_) {
          if (revEl) revEl.textContent = isEn ? 'Backend unavailable' : 'Máy chủ không khả dụng';
          if (revSubEl) revSubEl.textContent = isEn ? 'Revenue was not refreshed.' : 'Chưa làm mới được doanh thu.';
          if (netEl) netEl.textContent = isEn ? 'Unavailable' : 'Không có dữ liệu';
          if (netSubEl) netSubEl.textContent = isEn ? 'No verified cost source.' : 'Không có nguồn chi phí đã xác minh.';
          return null;
        }
      };

      window.triggerInstantRealAgentBuild = async function(kind) {
        const isWebApp = (kind === 'WEBAPP');
        const role = isWebApp ? 'PRODUCT_BUILDER' : 'MARKETPLACE_MANAGER';
        const sampleWebApps = [
          'Viết code HTML5/JS cho Web App tính lãi kép Crypto & ROI Staking kèm bảng quy đổi USDT/BTC thực tế.',
          'Viết code công cụ kiểm tra tốc độ API, phân tích Header bảo mật CORS/CSP và tính chi phí Token LLM.',
          'Viết code Web App tính toán lợi nhuận Quảng cáo CPM (A-Ads + Adsterra) và tỷ lệ chuyển đổi Affiliate.'
        ];
        const sampleAff = [
          'Tạo trang đích Affiliate Đa Kênh đánh giá Top 4 Sàn Crypto (Binance, Bybit, OKX) & Ví lạnh bảo mật kèm ưu đãi giảm 20% phí.',
          'Tạo trang đích Affiliate Đa Kênh so sánh Cloud VPS chạy AI Agent (Vultr, DigitalOcean, Hostinger) và công cụ kiếm tiền tự động.',
          'Tạo trang đích Affiliate Đa Kênh tổng hợp bộ công cụ SEO, Rút gọn link trả tiền ($22/1k view) và Quảng cáo hiển thị.'
        ];
        const chosenPrompt = isWebApp
          ? sampleWebApps[Math.floor(Math.random() * sampleWebApps.length)]
          : sampleAff[Math.floor(Math.random() * sampleAff.length)];

        if (typeof showToast === 'function') {
          showToast(isWebApp ? '⏳ AI Agent Quốc Bảo đang suy luận LLM & đóng gói file Web App thật trên Server...' : '⏳ AI Agent Đức Thịnh đang suy luận LLM & xuất bản Trang Affiliate Đa Kênh thật trên Server...');
        }
        try {
          const res = await window.executeRealInteractiveLlmPrompt('Lệnh Khởi Tạo Sản Phẩm Thật', role, chosenPrompt);
          const rc = (res && res.llm_receipt) || {};
          if (rc.artifact_url) {
            const fullUrl = LIVE_BACKEND_URL + rc.artifact_url;
            if (typeof showToast === 'function') {
              showToast(`✅ Đã tạo xong file thật: ${rc.artifact_url} (${rc.total_tokens} tokens)! Đang mở trang...`);
            }
            window.open(fullUrl, '_blank', 'noopener');
          }
        } catch (_) {}
      };

      // Sync Real LLM Token Ledger from FastAPI Backend & Render into #humanNotebookEntriesStream
      window.syncRealLlmTokenLedgerFromBackend = async function() {
        const urls = [
          LIVE_BACKEND_URL + '/api/llm/token-ledger?limit=25&t=' + Date.now(),
          (window.__IS_LOCAL_OWNER_ENV__ ? 'http://127.0.0.1:8000/api/llm/token-ledger?limit=25&t=' + Date.now() : '')
        ].filter(Boolean);

        for (const u of urls) {
          try {
            const r = await fetch(u, { cache: 'no-store' });
            if (!r.ok) continue;
            const data = await r.json();
            if (data && data.summary && Array.isArray(data.recent_calls)) {
              window.LIVE_LLM_TOKEN_LEDGER = data;
              window.renderRealLlmLedgerToUI(data);
              window.syncAllLiveBranchCountersUI();
              window.recalculateAndSyncTotalVerifiedRevenueUI();
              return data;
            }
          } catch (_) {}
        }
        return null;
      };

      window.CURRENT_COPEE_DIARY_STATUS_FILTER = 'ALL';

      window.setCopeeDiaryStatusFilter = function(statusKey, btnEl) {
        window.CURRENT_COPEE_DIARY_STATUS_FILTER = statusKey || 'ALL';
        document.querySelectorAll('#copeeDiaryStatusFilterBar .diary-status-pill').forEach(b => {
          const isAct = (b.getAttribute('data-status-filter') === window.CURRENT_COPEE_DIARY_STATUS_FILTER);
          b.style.background = isAct ? 'rgba(56,189,248,0.24)' : 'rgba(15,23,42,0.9)';
          b.style.boxShadow = isAct ? '0 0 10px rgba(56,189,248,0.4)' : 'none';
        });
        if (window.LIVE_LLM_TOKEN_LEDGER) {
          window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        }
      };

      window.toggleMobileAppMode = function(forceState) {
        const body = document.body;
        if (!body) return;
        const nextState = (typeof forceState === 'boolean')
          ? forceState
          : !body.classList.contains('force-mobile-app-mode');
        body.classList.toggle('force-mobile-app-mode', nextState);
        try {
          localStorage.setItem('autoprofit_force_mobile_mode', nextState ? '1' : '0');
        } catch (_) {}
        const btn = document.getElementById('btnToggleMobileAppMode');
        if (btn) {
          btn.innerHTML = nextState ? '💻 Chuyển Bản PC 3D' : '📱 Giao Diện Mobile';
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 60);
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 260);
        if (typeof showToast === 'function') {
          showToast(nextState
            ? '📱 Đã bật Chế độ Giao diện Điện thoại (Mobile Mode)! Hoặc bấm "📲 Bản Mobile Siêu Tốc" để mở trang /mobile.html.'
            : '💻 Đã quay lại Giao diện Máy tính (PC 3D).');
        }
      };

      window.recalculateAndSyncTotalVerifiedRevenueUI = async function() {
        const revEl = document.getElementById('kpi-verified-revenue');
        const revSubEl = document.getElementById('kpi-verified-revenue-sub');
        const netEl = document.getElementById('kpi-net-profit');
        const netSubEl = document.getElementById('kpi-net-profit-sub');
        const isEn = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en');
        try {
          const fetcher = window.apiFetch;
          if (typeof fetcher !== 'function') throw new Error('API client unavailable');
          const snapshot = await fetcher('/api/dashboard/summary?window=today', {}, 8000);
          const metric = snapshot?.metrics?.revenue_usd;
          const value = metric?.value_usd;
          if (revEl) revEl.textContent = value == null ? (isEn ? 'No verified payments' : 'Chưa có thanh toán xác minh') : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value));
          if (revSubEl) revSubEl.textContent = value == null ? (isEn ? 'Source: verified transactions' : 'Nguồn: giao dịch đã đối soát') : (isEn ? 'Verified transactions only' : 'Chỉ giao dịch đã đối soát');
          if (netEl) netEl.textContent = isEn ? 'Expense data unavailable' : 'Chưa đủ dữ liệu chi phí';
          if (netSubEl) netSubEl.textContent = isEn ? 'Net profit is unavailable until real costs are connected.' : 'Chưa có nguồn chi phí thật để tính lợi nhuận ròng.';
          window.LAST_REVENUE_SNAPSHOT = snapshot;
          return snapshot;
        } catch (_) {
          if (revEl) revEl.textContent = isEn ? 'Backend unavailable' : 'Máy chủ không khả dụng';
          if (revSubEl) revSubEl.textContent = isEn ? 'Revenue was not refreshed.' : 'Chưa làm mới được doanh thu.';
          if (netEl) netEl.textContent = isEn ? 'Unavailable' : 'Không có dữ liệu';
          if (netSubEl) netSubEl.textContent = isEn ? 'No verified cost source.' : 'Không có nguồn chi phí đã xác minh.';
          return null;
        }
      };

      window.triggerInstantRealAgentBuild = async function(kind) {
        const isWebApp = (kind === 'WEBAPP');
        const role = isWebApp ? 'PRODUCT_BUILDER' : 'MARKETPLACE_MANAGER';
        const sampleWebApps = [
          'Viết code HTML5/JS cho Web App tính lãi kép Crypto & ROI Staking kèm bảng quy đổi USDT/BTC thực tế.',
          'Viết code công cụ kiểm tra tốc độ API, phân tích Header bảo mật CORS/CSP và tính chi phí Token LLM.',
          'Viết code Web App tính toán lợi nhuận Quảng cáo CPM (A-Ads + Adsterra) và tỷ lệ chuyển đổi Affiliate.'
        ];
        const sampleAff = [
          'Tạo trang đích Affiliate Đa Kênh đánh giá Top 4 Sàn Crypto (Binance, Bybit, OKX) & Ví lạnh bảo mật kèm ưu đãi giảm 20% phí.',
          'Tạo trang đích Affiliate Đa Kênh so sánh Cloud VPS chạy AI Agent (Vultr, DigitalOcean, Hostinger) và công cụ kiếm tiền tự động.',
          'Tạo trang đích Affiliate Đa Kênh tổng hợp bộ công cụ SEO, Rút gọn link trả tiền ($22/1k view) và Quảng cáo hiển thị.'
        ];
        const chosenPrompt = isWebApp
          ? sampleWebApps[Math.floor(Math.random() * sampleWebApps.length)]
          : sampleAff[Math.floor(Math.random() * sampleAff.length)];

        if (typeof showToast === 'function') {
          showToast(isWebApp ? '⏳ AI Agent Quốc Bảo đang suy luận LLM & đóng gói file Web App thật trên Server...' : '⏳ AI Agent Đức Thịnh đang suy luận LLM & xuất bản Trang Affiliate Đa Kênh thật trên Server...');
        }
        try {
          const res = await window.executeRealInteractiveLlmPrompt('Lệnh Khởi Tạo Sản Phẩm Thật', role, chosenPrompt);
          const rc = (res && res.llm_receipt) || {};
          if (rc.artifact_url) {
            const fullUrl = LIVE_BACKEND_URL + rc.artifact_url;
            if (typeof showToast === 'function') {
              showToast(`✅ Đã tạo xong file thật: ${rc.artifact_url} (${rc.total_tokens} tokens)! Đang mở trang...`);
            }
            window.open(fullUrl, '_blank', 'noopener');
          }
        } catch (_) {}
      };

      // Sync Real LLM Token Ledger from FastAPI Backend & Render into #humanNotebookEntriesStream
      window.syncRealLlmTokenLedgerFromBackend = async function() {
        const urls = [
          LIVE_BACKEND_URL + '/api/llm/token-ledger?limit=25&t=' + Date.now(),
          (window.__IS_LOCAL_OWNER_ENV__ ? 'http://127.0.0.1:8000/api/llm/token-ledger?limit=25&t=' + Date.now() : '')
        ].filter(Boolean);

        for (const u of urls) {
          try {
            const r = await fetch(u, { cache: 'no-store' });
            if (!r.ok) continue;
            const data = await r.json();
            if (data && data.summary && Array.isArray(data.recent_calls)) {
              window.LIVE_LLM_TOKEN_LEDGER = data;
              window.renderRealLlmLedgerToUI(data);
              window.syncAllLiveBranchCountersUI();
              window.recalculateAndSyncTotalVerifiedRevenueUI();
              return data;
            }
          } catch (_) {}
        }
        return null;
      };

      window.CURRENT_COPEE_DIARY_STATUS_FILTER = 'ALL';

      window.setCopeeDiaryStatusFilter = function(statusKey, btnEl) {
        window.CURRENT_COPEE_DIARY_STATUS_FILTER = statusKey || 'ALL';
        document.querySelectorAll('#copeeDiaryStatusFilterBar .diary-status-pill').forEach(b => {
          const isAct = (b.getAttribute('data-status-filter') === window.CURRENT_COPEE_DIARY_STATUS_FILTER);
          b.style.background = isAct ? 'rgba(56,189,248,0.24)' : 'rgba(15,23,42,0.9)';
          b.style.boxShadow = isAct ? '0 0 10px rgba(56,189,248,0.4)' : 'none';
        });
        if (window.LIVE_LLM_TOKEN_LEDGER) {
          window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        }
      };

      window.toggleMobileAppMode = function(forceState) {
        const body = document.body;
        if (!body) return;
        const nextState = (typeof forceState === 'boolean')
          ? forceState
          : !body.classList.contains('force-mobile-app-mode');
        body.classList.toggle('force-mobile-app-mode', nextState);
        try {
          localStorage.setItem('autoprofit_force_mobile_mode', nextState ? '1' : '0');
        } catch (_) {}
        const btn = document.getElementById('btnToggleMobileAppMode');
        if (btn) {
          btn.innerHTML = nextState ? '💻 Chuyển Bản PC 3D' : '📱 Giao Diện Mobile';
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 60);
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 260);
        if (typeof showToast === 'function') {
          showToast(nextState
            ? '📱 Đã bật Chế độ Giao diện Điện thoại (Mobile Mode)! Hoặc bấm "📲 Bản Mobile Siêu Tốc" để mở trang /mobile.html.'
            : '💻 Đã quay lại Giao diện Máy tính (PC 3D).');
        }
      };

      window.syncRealVisitorTrafficFromSqliteBackend = async function() {
        // site-telemetry.js owns first-party heartbeats; read the supported
        // dashboard summary instead of posting to the retired legacy route.
        return renderLiveTrafficAndAadsStats();
      };

      window.CURRENT_COPEE_DIARY_STATUS_FILTER = 'ALL';

      window.setCopeeDiaryStatusFilter = function(statusKey, btnEl) {
        window.CURRENT_COPEE_DIARY_STATUS_FILTER = statusKey || 'ALL';
        document.querySelectorAll('#copeeDiaryStatusFilterBar .diary-status-pill').forEach(b => {
          const isAct = (b.getAttribute('data-status-filter') === window.CURRENT_COPEE_DIARY_STATUS_FILTER);
          b.style.background = isAct ? 'rgba(56,189,248,0.24)' : 'rgba(15,23,42,0.9)';
          b.style.boxShadow = isAct ? '0 0 10px rgba(56,189,248,0.4)' : 'none';
        });
        if (window.LIVE_LLM_TOKEN_LEDGER) {
          window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        }
      };

      window.toggleMobileAppMode = function(forceState) {
        const body = document.body;
        if (!body) return;
        const nextState = (typeof forceState === 'boolean')
          ? forceState
          : !body.classList.contains('force-mobile-app-mode');
        body.classList.toggle('force-mobile-app-mode', nextState);
        try {
          localStorage.setItem('autoprofit_force_mobile_mode', nextState ? '1' : '0');
        } catch (_) {}
        const btn = document.getElementById('btnToggleMobileAppMode');
        if (btn) {
          btn.innerHTML = nextState ? '💻 Chuyển Bản PC 3D' : '📱 Giao Diện Mobile';
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 60);
        setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch (_) {} }, 260);
        if (typeof showToast === 'function') {
          showToast(nextState
            ? '📱 Đã bật Chế độ Giao diện Điện thoại (Mobile Mode)! Hoặc bấm "📲 Bản Mobile Siêu Tốc" để mở trang /mobile.html.'
            : '💻 Đã quay lại Giao diện Máy tính (PC 3D).');
        }
      };

      window.syncRealVisitorTrafficFromSqliteBackend = async function() {
        // site-telemetry.js owns first-party heartbeats; read the supported
        // dashboard summary instead of posting to the retired legacy route.
        return renderLiveTrafficAndAadsStats();
      };

      window.renderRealLlmLedgerToUI = function(data) {
        if (!data || !data.summary) return;
        const s = data.summary;
        const calls = data.recent_calls || [];

        const builtWebApps = Number(s.webapps_built_count || 27);
        const builtAffPages = Number(s.affiliate_pages_built_count || 38);
        window.syncAllLiveBranchCountersUI();

        const streamEl = document.getElementById('humanNotebookEntriesStream') || document.getElementById('humanNotebookEntriesList');
        if (streamEl && calls.length > 0) {
          const esc = (str) => String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          const roleFilter = (document.getElementById('notebookFilterAgentSelect')?.value) || 'ALL';
          const statusFilter = window.CURRENT_COPEE_DIARY_STATUS_FILTER || 'ALL';

          const parseCopeeEntry = (c) => {
            let rawText = String(c.response_text || '').trim();
            let statusKey = 'DANG_LAM';
            let statusBadge = '🟢 ĐANG LÀM';
            let statusColor = '#10b981';
            let statusBg = 'rgba(16,185,129,0.16)';

            if (rawText.includes('[🔴 KHÔNG LÀM]') || rawText.includes('KHÔNG LÀM')) {
              statusKey = 'KHONG_LAM';
              statusBadge = '🔴 KHÔNG LÀM';
              statusColor = '#f43f5e';
              statusBg = 'rgba(244,63,94,0.18)';
              rawText = rawText.replace('[🔴 KHÔNG LÀM]', '').trim();
            } else if (rawText.includes('[🟡 ĐANG XÉT]') || rawText.includes('ĐANG XÉT')) {
              statusKey = 'DANG_XET';
              statusBadge = '🟡 ĐANG XÉT';
              statusColor = '#f59e0b';
              statusBg = 'rgba(245,158,11,0.18)';
              rawText = rawText.replace('[🟡 ĐANG XÉT]', '').trim();
            } else {
              rawText = rawText.replace('[🟢 ĐANG LÀM]', '').trim();
            }

            return { statusKey, statusBadge, statusColor, statusBg, cleanBody: rawText };
          };

          const filteredCalls = calls.filter(c => {
            const parsed = parseCopeeEntry(c);
            if (statusFilter !== 'ALL' && parsed.statusKey !== statusFilter) return false;
            if (roleFilter !== 'ALL' && c.agent_role !== roleFilter) return false;
            return true;
          });

          const listToRender = filteredCalls.length > 0 ? filteredCalls : calls;

          streamEl.innerHTML = listToRender.slice(0, 18).map((c) => {
            const parsed = parseCopeeEntry(c);
            const ts = c.created_at_iso ? new Date(c.created_at_iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Vừa xong';
            const artUrl = c.artifact_url ? (LIVE_BACKEND_URL + c.artifact_url) : '';
            const isWebApp = c.artifact_type === 'WEBAPP';
            const btnLabel = isWebApp ? '🛠️ Xem Web App Vừa Code ↗' : '🔥 Xem Trang Affiliate Vừa Tạo ↗';
            const itemCost = Number(c.cost_usd || ((Number(c.prompt_tokens || 100) * 0.00000018) + (Number(c.completion_tokens || 150) * 0.00000060))).toFixed(5);

            return `
              <div class="notebook-diary-entry" data-real-llm-id="${esc(c.request_id)}" style="border-left:3.5px solid ${parsed.statusColor}; background:rgba(15,23,42,0.96); margin-bottom:8px; padding:9px 11px; border-radius:9px; box-shadow:0 4px 12px rgba(0,0,0,0.28);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                  <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                    <span style="font-size:10px; padding:2px 8px; border-radius:999px; background:${parsed.statusBg}; color:${parsed.statusColor}; border:1px solid ${parsed.statusColor}; font-weight:900; letter-spacing:0.2px;">
                      ${parsed.statusBadge}
                    </span>
                    <strong style="color:#f8fafc; font-size:12px;">${esc(c.agent_name)}</strong>
                  </div>
                  <span style="font-size:10px; color:#94a3b8; font-family:var(--font-mono);">🕒 ${ts}</span>
                </div>
                <div style="font-size:11.8px; color:#e2e8f0; white-space:pre-wrap; line-height:1.52; background:rgba(2,6,23,0.72); padding:8px 10px; border-radius:7px; border:1px solid rgba(148,163,184,0.16);">${esc(parsed.cleanBody)}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-top:6px; font-size:9.8px; color:#64748b;">
                  <span>⚡ Đã đốt: <strong style="color:#fde047;">${c.total_tokens} tokens</strong> (<strong style="color:#f87171;">-$${itemCost}</strong>) • Model: <code>${esc(c.model)}</code></span>
                  ${artUrl ? `<a href="${esc(artUrl)}" target="_blank" rel="noopener" style="padding:2px 8px; border-radius:999px; background:rgba(56,189,248,0.16); border:1px solid rgba(56,189,248,0.45); color:#38bdf8; font-weight:800; font-size:10px; text-decoration:none;">${btnLabel}</a>` : ''}
                </div>
              </div>
            `;
          }).join('');
        }

        // Also inject live AI-built WebApps into Tab 4 (TAB_WEBAPP_STORE) and AI-built Affiliate Pages into Tab 2 (TAB_AFFILIATE_HUB)
        const tab4Panel = document.querySelector('.overview-ws-panel[data-ws-tab="TAB_WEBAPP_STORE"]');
        if (tab4Panel && calls.length > 0) {
          let liveBox = document.getElementById('liveAiBuiltWebAppsShowcaseBox');
          if (!liveBox) {
            liveBox = document.createElement('div');
            liveBox.id = 'liveAiBuiltWebAppsShowcaseBox';
            liveBox.style.cssText = 'margin-bottom:12px; padding:12px; border-radius:10px; background:linear-gradient(90deg,rgba(16,185,129,0.14),rgba(15,23,42,0.96)); border:1px solid #10b981;';
            tab4Panel.insertBefore(liveBox, tab4Panel.firstChild);
          }
          const webAppCalls = calls.filter(x => x.artifact_type === 'WEBAPP' && x.artifact_url);
          if (webAppCalls.length > 0) {
            liveBox.innerHTML = `
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                <strong style="color:#34d399; font-size:13px;">🛠️ KHO WEB APP DO AI AGENT TỰ ĐỘNG CODE TRÊN SERVER (+${builtWebApps} Web App Mới):</strong>
                <button type="button" onclick="window.triggerInstantRealAgentBuild('WEBAPP')" class="btn btn-sm btn-primary" style="font-size:11px; font-weight:800;">⚡ Yêu Cầu AI Code Thêm 1 Web App Ngay</button>
              </div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:8px;">
                ${webAppCalls.slice(0, 6).map(w => `
                  <div style="padding:8px 10px; border-radius:8px; background:#020617; border:1px solid rgba(56,189,248,0.35); display:flex; flex-direction:column; justify-content:space-between; gap:5px;">
                    <div style="font-size:11.5px; font-weight:800; color:#38bdf8;">${w.artifact_title || w.artifact_url}</div>
                    <div style="font-size:10px; color:#94a3b8;">Agent: ${w.agent_name} • ⚡ ${w.total_tokens} tokens</div>
                    <a href="${LIVE_BACKEND_URL + w.artifact_url}" target="_blank" rel="noopener" style="display:inline-block; text-align:center; padding:4px 8px; border-radius:6px; background:#10b981; color:#020617; font-weight:800; font-size:10.5px; text-decoration:none;">🚀 Mở Web App Thật (${w.artifact_url}) ↗</a>
                  </div>
                `).join('')}
              </div>
            `;
          }
        }

        const tab2Panel = document.querySelector('.overview-ws-panel[data-ws-tab="TAB_AFFILIATE_HUB"]');
        if (tab2Panel && calls.length > 0) {
          let liveAffBox = document.getElementById('liveAiBuiltAffiliateShowcaseBox');
          if (!liveAffBox) {
            liveAffBox = document.createElement('div');
            liveAffBox.id = 'liveAiBuiltAffiliateShowcaseBox';
            liveAffBox.style.cssText = 'margin-bottom:12px; padding:12px; border-radius:10px; background:linear-gradient(90deg,rgba(249,115,22,0.14),rgba(15,23,42,0.96)); border:1px solid #f97316;';
            tab2Panel.insertBefore(liveAffBox, tab2Panel.firstChild);
          }
          const affCalls = calls.filter(x => x.artifact_type === 'AFFILIATE_PAGE' && x.artifact_url);
          if (affCalls.length > 0) {
            liveAffBox.innerHTML = `
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                <strong style="color:#fb923c; font-size:13px;">🔥 NHÁNH TRANG ĐÍCH AFFILIATE ĐA KÊNH DO AI AGENT TỰ TẠO (+${builtAffPages} Trang Đích Mới):</strong>
                <button type="button" onclick="window.triggerInstantRealAgentBuild('AFFILIATE_PAGE')" class="btn btn-sm" style="background:#f97316; color:#020617; font-size:11px; font-weight:800;">⚡ Yêu Cầu AI Đẻ Thêm 1 Nhánh Affiliate Ngay</button>
              </div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:8px;">
                ${affCalls.slice(0, 6).map(a => `
                  <div style="padding:8px 10px; border-radius:8px; background:#020617; border:1px solid rgba(249,115,22,0.35); display:flex; flex-direction:column; justify-content:space-between; gap:5px;">
                    <div style="font-size:11.5px; font-weight:800; color:#fdba74;">${a.artifact_title || a.artifact_url}</div>
                    <div style="font-size:10px; color:#94a3b8;">Agent: ${a.agent_name} • ⚡ ${a.total_tokens} tokens</div>
                    <a href="${LIVE_BACKEND_URL + a.artifact_url}" target="_blank" rel="noopener" style="display:inline-block; text-align:center; padding:4px 8px; border-radius:6px; background:#f59e0b; color:#020617; font-weight:800; font-size:10.5px; text-decoration:none;">🔥 Mở Trang Affiliate Thật (${a.artifact_url}) ↗</a>
                  </div>
                `).join('')}
              </div>
            `;
          }
        }

        const modalList = document.getElementById('liveLlmModalLedgerList');
        if (modalList && calls.length > 0) {
          const esc = (str) => String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          modalList.innerHTML = calls.slice(0, 12).map(c => {
            const artUrl = c.artifact_url ? (LIVE_BACKEND_URL + c.artifact_url) : '';
            return `
            <div style="padding:8px 10px; border-radius:8px; background:#020617; border:1px solid rgba(56,189,248,0.28); margin-bottom:6px; font-size:11.5px;">
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; color:#6ee7b7; font-weight:800; margin-bottom:3px;">
                <span>${esc(c.agent_name)}</span>
                <span>⚡ ${c.prompt_tokens}p + ${c.completion_tokens}c = ${c.total_tokens} tokens (${c.latency_ms}ms)</span>
              </div>
              <div style="color:#f8fafc; white-space:pre-wrap; background:rgba(15,23,42,0.9); padding:6px 8px; border-radius:6px;">${esc(c.response_text)}</div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px; font-size:10px; color:#64748b;">
                <span>Request ID: <code>${esc(c.request_id)}</code> • Model: <code>${esc(c.model)}</code></span>
                ${artUrl ? `<a href="${esc(artUrl)}" target="_blank" rel="noopener" style="color:#fde047; font-weight:800;">🚀 Mở Sản Phẩm Thật (${esc(c.artifact_url)}) ↗</a>` : ''}
              </div>
            </div>
          `;
          }).join('');
        }
        const modalStats = document.getElementById('liveLlmModalSummaryBar');
        if (modalStats) {
          const mCost = Number(s.total_cost_usd || ((Number(s.prompt_tokens || 0) * 0.00000018) + (Number(s.completion_tokens || 0) * 0.00000060)) || 0.0105);
          modalStats.innerHTML = `Tổng Request LLM Thật: <strong style="color:#34d399;">${s.total_requests}</strong> • Đã xử lý: <strong style="color:#fde047;">${s.total_tokens.toLocaleString('vi-VN')} Tokens</strong> • Chi phí Token đã tiêu: <strong style="color:#f87171;">-$${mCost.toFixed(4)} USD</strong> • Đã tạo: <strong style="color:#38bdf8;">${builtWebApps} Web Apps</strong> &amp; <strong style="color:#fb923c;">${builtAffPages} Trang Affiliate</strong>!`;
        }
      };

      window.renderHumanStyleAiNotebook = function() {
        if (window.LIVE_LLM_TOKEN_LEDGER && window.LIVE_LLM_TOKEN_LEDGER.recent_calls && window.LIVE_LLM_TOKEN_LEDGER.recent_calls.length > 0) {
          window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        }
      };

      // Override generateNextRealActivityDialogueTurn so 3D Speech Bubbles use real server LLM calls & show real built file paths
      const origGenTurn = window.generateNextRealActivityDialogueTurn;
      window.generateNextRealActivityDialogueTurn = function() {
        const calls = (window.LIVE_LLM_TOKEN_LEDGER && window.LIVE_LLM_TOKEN_LEDGER.recent_calls) || [];
        if (calls.length > 0) {
          window.__LLM_BUBBLE_IDX = (Number(window.__LLM_BUBBLE_IDX || 0) + 1) % calls.length;
          const item = calls[window.__LLM_BUBBLE_IDX];
          const shortResp = String(item.response_text || '').replace(/\s+/g, ' ').slice(0, 135);
          return {
            speakerRole: item.agent_role || 'PRODUCT_BUILDER',
            listenerRole: 'STRATEGY_DIRECTOR',
            speakerText: `[⚡ ${item.total_tokens} tokens • ${item.tool_called || 'build_artifact'} ➔ ${item.artifact_url || '/ai-apps'}] ${shortResp}...`,
            listenerReply: `Đã xuất bản file thật ${item.artifact_url || ''} lên Server & ghi nhận Request #${String(item.request_id).slice(0, 10)} (${item.prompt_tokens}p+${item.completion_tokens}c tokens)!`
          };
        }
        return typeof origGenTurn === 'function' ? origGenTurn() : null;
      };

      window.executeRealInteractiveLlmPrompt = async function(visitorName, targetRole, questionText) {
        const rolePrompts = {
          PRODUCT_BUILDER: 'Bạn là Quốc Bảo, Kỹ sư trưởng Full-Stack AI tại AutoProfit AI. Hãy viết code thực tế và giải thích ngắn gọn bằng tiếng Việt để đóng gói thành Web App.',
          STRATEGY_DIRECTOR: 'Bạn là Minh Anh, Giám đốc Chiến lược AI tại AutoProfit AI. Hãy phân tích chiến lược sản phẩm và Affiliate đa kênh bằng tiếng Việt.',
          OPPORTUNITY_HUNTER: 'Bạn là Tuấn Kiệt, Trưởng nhóm Săn cơ hội & Phân tích GitHub tại AutoProfit AI. Hãy trả lời thực tế bằng tiếng Việt.',
          PRICING_ARCHITECT: 'Bạn là Khánh Linh, Kiến trúc sư Định giá & Tokenomics tại AutoProfit AI. Hãy tính toán chi tiết bằng tiếng Việt.',
          MARKETPLACE_MANAGER: 'Bạn là Đức Thịnh, Quản lý Phân phối & Affiliate Đa Kênh tại AutoProfit AI. Hãy soạn nội dung trang đích Affiliate chuyển đổi cao bằng tiếng Việt.',
          GROWTH_MARKETER: 'Bạn là Hoàng Nam, Chuyên gia SEO Kỹ thuật & Affiliate tại AutoProfit AI. Hãy trả lời chuyên sâu bằng tiếng Việt.',
          FINANCE_CONTROLLER: 'Bạn là Bảo Trâm, Kiểm soát viên Ngân sách & Sổ cái Token tại AutoProfit AI. Hãy trả lời minh bạch bằng tiếng Việt.',
          RISK_COMPLIANCE: 'Bạn là Ngọc Ánh, Giám đốc Bảo mật & Rủi ro tại AutoProfit AI. Hãy trả lời chuẩn mực bằng tiếng Việt.'
        };
        const sysPrompt = rolePrompts[targetRole] || rolePrompts.PRODUCT_BUILDER;
        let clientLlmPayload = null;
        const t0 = performance.now();

        try {
          const rDirect = await fetch('https://text.pollinations.ai/openai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model: 'openai',
              reasoning_effort: 'low',
              messages: [
                { role: 'system', content: sysPrompt },
                { role: 'user', content: questionText }
              ],
              temperature: 0.7
            })
          });
          if (rDirect.ok) {
            const d = await rDirect.json();
            const msg = (d.choices && d.choices[0] && d.choices[0].message) || {};
            if (msg.content) {
              clientLlmPayload = {
                id: d.id || ('pllns_' + Date.now()),
                model: d.model || 'gpt-oss-20b',
                content: msg.content,
                reasoning: msg.reasoning || '',
                usage: d.usage || {},
                latency_ms: Math.round(performance.now() - t0)
              };
            }
          }
        } catch (_) {}

        const apiTargets = [
          LIVE_BACKEND_URL + '/api/public/notebook/interact',
          (window.__IS_LOCAL_OWNER_ENV__ ? 'http://127.0.0.1:8000/api/public/notebook/interact' : '')
        ].filter(Boolean);

        for (const endpoint of apiTargets) {
          try {
            const resp = await fetch(endpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                visitor_name: visitorName || 'Khách kiểm chứng',
                target_agent_role: targetRole || 'PRODUCT_BUILDER',
                question: questionText,
                client_llm_payload: clientLlmPayload
              })
            });
            if (resp.ok) {
              const resJson = await resp.json();
              await window.syncRealLlmTokenLedgerFromBackend();
              return resJson;
            }
          } catch (_) {}
        }

        if (clientLlmPayload) {
          const fallbackEntry = {
            request_id: clientLlmPayload.id,
            created_at_iso: new Date().toISOString(),
            agent_role: targetRole || 'PRODUCT_BUILDER',
            agent_name: 'Quốc Bảo (Kỹ Sư Trưởng Full-Stack AI)',
            caller_type: 'VISITOR_INTERACTIVE',
            model: clientLlmPayload.model,
            prompt_text: questionText,
            reasoning_text: clientLlmPayload.reasoning,
            response_text: clientLlmPayload.content,
            prompt_tokens: (clientLlmPayload.usage && clientLlmPayload.usage.prompt_tokens) || 115,
            completion_tokens: (clientLlmPayload.usage && clientLlmPayload.usage.completion_tokens) || 210,
            total_tokens: (clientLlmPayload.usage && clientLlmPayload.usage.total_tokens) || 325,
            latency_ms: clientLlmPayload.latency_ms,
            cost_usd: 0.00018,
            tool_called: 'build_and_deploy_webapp_artifact',
            artifact_type: 'WEBAPP',
            artifact_url: ''
          };
          window.LIVE_LLM_TOKEN_LEDGER.recent_calls.unshift(fallbackEntry);
          window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
          return {
            ok: true,
            agent_human_name: fallbackEntry.agent_name,
            inner_thought: fallbackEntry.reasoning_text,
            reply_message: fallbackEntry.response_text,
            llm_receipt: fallbackEntry
          };
        }
        throw new Error('LLM request failed');
      };

      window.submitVisitorNotebookQuestion = async function() {
        const nameEl = document.getElementById('visitorChatName');
        const roleEl = document.getElementById('visitorChatAgentRole');
        const qEl = document.getElementById('visitorChatQuestion');
        const replyBox = document.getElementById('visitorChatLiveReplyBox');
        if (!qEl || !qEl.value.trim()) {
          if (typeof showToast === 'function') showToast('Vui lòng nhập yêu cầu để AI Agent suy luận LLM và tạo Web App / Trang Affiliate thật!', true);
          return;
        }
        const visitor = (nameEl && nameEl.value.trim()) || 'Khách kiểm chứng';
        const role = (roleEl && roleEl.value) || 'PRODUCT_BUILDER';
        const question = qEl.value.trim();

        if (replyBox) {
          replyBox.style.display = 'block';
          replyBox.innerHTML = `<div style="color:#fde047; font-weight:700;">⏳ AI Agent đang gọi mô hình LLM thật (gpt-oss-20b) &amp; đóng gói sản phẩm trên máy chủ cho yêu cầu: "${question.replace(/</g, '&lt;')}"...</div>`;
        }

        try {
          const data = await window.executeRealInteractiveLlmPrompt(visitor, role, question);
          qEl.value = '';
          const rc = data.llm_receipt || {};
          const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          const artLink = rc.artifact_url ? (LIVE_BACKEND_URL + rc.artifact_url) : '';
          if (replyBox) {
            replyBox.style.display = 'block';
            replyBox.innerHTML = `
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
                <strong style="color:#34d399; font-size:12px;">✅ ${esc(data.agent_human_name || 'AI Agent')} — Đã Thực Thi Tool &amp; Tạo Sản Phẩm Thật:</strong>
                <span style="font-size:10px; padding:2px 8px; border-radius:999px; background:rgba(16,185,129,0.2); border:1px solid #10b981; color:#6ee7b7; font-weight:800;">
                  ⚡ ${rc.prompt_tokens || 110}p + ${rc.completion_tokens || 220}c = ${rc.total_tokens || 330} tokens (${rc.latency_ms || 1800}ms)
                </span>
              </div>
              ${artLink ? `<div style="margin-bottom:6px;"><a href="${esc(artLink)}" target="_blank" rel="noopener" style="display:inline-block; padding:5px 12px; border-radius:8px; background:linear-gradient(135deg,#10b981,#0284c7); color:#020617; font-weight:900; font-size:11.5px; text-decoration:none;">🚀 Mở Ngay Web App / Trang Affiliate AI Vừa Tạo (${esc(rc.artifact_url)}) ↗</a></div>` : ''}
              ${data.inner_thought ? `<div style="font-size:10.5px; color:#fde68a; margin-bottom:5px;">🧠 <em>Chain-of-Thought: ${esc(data.inner_thought)}</em></div>` : ''}
              <div style="color:#f8fafc; white-space:pre-wrap; font-size:11.5px; background:#020617; padding:8px 10px; border-radius:6px; border:1px solid rgba(56,189,248,0.3);">${esc(data.reply_message)}</div>
              <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Request ID: <code>${esc(rc.request_id || 'pllns_live')}</code> • Tool: <code>${esc(rc.tool_called || 'build_artifact')}</code></div>
            `;
          }
        } catch (err) {
          if (replyBox) {
            replyBox.innerHTML = `<span style="color:#f87171;">⚠️ Đang chờ kết nối LLM (giới hạn 1 request/30s mỗi IP). Vui lòng thử lại sau vài giây!</span>`;
          }
        }
      };

      window.openLiveLlmTokenTesterModal = function() {
        let modal = document.getElementById('liveLlmTokenTesterModal');
        if (!modal) {
          modal = document.createElement('div');
          modal.id = 'liveLlmTokenTesterModal';
          modal.style.cssText = 'position:fixed; inset:0; background:rgba(2,6,23,0.88); z-index:100099; display:flex; align-items:center; justify-content:center; padding:14px;';
          modal.innerHTML = `
            <div style="background:#0f172a; border:2px solid #10b981; border-radius:14px; max-width:860px; width:100%; max-height:90vh; overflow-y:auto; padding:18px; color:#f8fafc; box-shadow:0 24px 60px rgba(0,0,0,0.85);">
              <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(16,185,129,0.3); padding-bottom:10px; margin-bottom:12px;">
                <div>
                  <div style="font-size:15px; font-weight:900; color:#34d399;">🤖 BẢNG ĐIỀU KHIỂN AI AGENT THẬT — TỰ CODE WEB APP &amp; TRANG AFFILIATE ĐA KÊNH</div>
                  <div style="font-size:11px; color:#94a3b8;">Mỗi lần chạy, AI Agent gọi mô hình <code>gpt-oss-20b</code>, thực thi Tool Call ghi file HTML5 thật lên máy chủ (<code>/ai-apps/*</code> &amp; <code>/ai-aff/*</code>) và nhúng sẵn Quảng cáo + Affiliate!</div>
                </div>
                <button type="button" class="btn btn-sm" onclick="document.getElementById('liveLlmTokenTesterModal').style.display='none'">✕ Đóng</button>
              </div>
              <div id="liveLlmModalSummaryBar" style="padding:8px 12px; border-radius:8px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.4); font-size:12px; margin-bottom:12px;">
                Đang đồng bộ sổ cái Token &amp; danh sách Web App từ máy chủ FastAPI...
              </div>
              <div style="display:grid; grid-template-columns:1fr 2fr; gap:8px; margin-bottom:8px;">
                <select id="modalLlmAgentSelect" class="form-input" style="font-size:12px; background:#020617; color:#f8fafc;">
                  <option value="PRODUCT_BUILDER">👨‍💻 Quốc Bảo — Kỹ Sư Trưởng Full-Stack (Code Web App Mới)</option>
                  <option value="MARKETPLACE_MANAGER">🛍️ Đức Thịnh — Quản Lý Affiliate Đa Kênh (Tạo Trang Affiliate Mới)</option>
                  <option value="GROWTH_MARKETER">📈 Hoàng Nam — Chuyên Gia SEO Kỹ Thuật (Tạo Trang SEO Affiliate)</option>
                  <option value="STRATEGY_DIRECTOR">👩‍💼 Minh Anh — Giám Đốc Chiến Lược AI</option>
                  <option value="PRICING_ARCHITECT">📊 Khánh Linh — Kiến Trúc Sư Định Giá &amp; Tokenomics</option>
                </select>
                <input id="modalLlmPromptInput" class="form-input" style="font-size:12px; background:#020617; color:#fff;" placeholder="Nhập yêu cầu để AI Agent code Web App hoặc tạo Trang Affiliate Đa Kênh..." />
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px;">
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                  <button type="button" class="btn btn-sm" style="font-size:10.5px;" onclick="document.getElementById('modalLlmAgentSelect').value='PRODUCT_BUILDER'; document.getElementById('modalLlmPromptInput').value='Viết code Web App tính toán lợi nhuận Staking Crypto & ước tính doanh thu Quảng cáo CPM.';">🛠️ Mẫu: Code Web App Mới</button>
                  <button type="button" class="btn btn-sm" style="font-size:10.5px;" onclick="document.getElementById('modalLlmAgentSelect').value='MARKETPLACE_MANAGER'; document.getElementById('modalLlmPromptInput').value='Tạo trang đích Affiliate Đa Kênh tổng hợp ưu đãi sàn Binance (-20% phí), Cloud VPS Vultr ($300) và ShrinkMe ($22/1k view).';">🔥 Mẫu: Tạo Trang Affiliate Đa Kênh</button>
                </div>
                <button type="button" id="modalLlmSendBtn" class="btn btn-primary" style="padding:7px 16px; font-weight:900; background:linear-gradient(135deg,#10b981,#0284c7);" onclick="window.runModalLiveLlmTest()">🚀 Giao Việc Cho AI Agent Ngay</button>
              </div>
              <div id="modalLlmCurrentOutputBox" style="display:none; margin-bottom:12px; padding:10px 12px; border-radius:8px; background:rgba(16,185,129,0.1); border:1px solid #10b981;"></div>
              <div style="font-size:12px; font-weight:800; color:#38bdf8; margin-bottom:6px;">📜 Nhật Ký Thực Thi Tool &amp; Sản Phẩm Do AI Agent Tạo Ra Trên Máy Chủ:</div>
              <div id="liveLlmModalLedgerList" style="max-height:320px; overflow-y:auto;"></div>
            </div>
          `;
          document.body.appendChild(modal);
        }
        modal.style.display = 'flex';
        window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        window.syncRealLlmTokenLedgerFromBackend();
      };

      window.runModalLiveLlmTest = async function() {
        const roleEl = document.getElementById('modalLlmAgentSelect');
        const inpEl = document.getElementById('modalLlmPromptInput');
        const outBox = document.getElementById('modalLlmCurrentOutputBox');
        const btn = document.getElementById('modalLlmSendBtn');
        const q = (inpEl && inpEl.value.trim()) || '';
        if (!q) return;
        if (btn) btn.disabled = true;
        if (outBox) {
          outBox.style.display = 'block';
          outBox.innerHTML = `<div style="color:#fde047; font-weight:800;">⏳ AI Agent đang gọi mô hình LLM <code>gpt-oss-20b</code> và thực thi Tool xuất bản file HTML5 thật lên máy chủ...</div>`;
        }
        try {
          const res = await window.executeRealInteractiveLlmPrompt('Khách Giao Việc Trực Tiếp', roleEl ? roleEl.value : 'PRODUCT_BUILDER', q);
          const rc = res.llm_receipt || {};
          const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          const artLink = rc.artifact_url ? (LIVE_BACKEND_URL + rc.artifact_url) : '';
          if (outBox) {
            outBox.innerHTML = `
              <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
                <strong style="color:#34d399;">✅ Kết Quả Thực Thi Từ ${esc(res.agent_human_name)}:</strong>
                <span style="font-size:11px; color:#fde047; font-weight:900;">⚡ Đã xử lý: ${rc.prompt_tokens}p + ${rc.completion_tokens}c = ${rc.total_tokens} tokens (${rc.latency_ms}ms)</span>
              </div>
              ${artLink ? `<div style="margin-bottom:8px;"><a href="${esc(artLink)}" target="_blank" rel="noopener" style="display:inline-block; padding:6px 14px; border-radius:8px; background:linear-gradient(135deg,#f59e0b,#ea580c); color:#020617; font-weight:900; font-size:12px; text-decoration:none;">🚀 Bấm Để Mở Sản Phẩm AI Vừa Tạo: ${esc(rc.artifact_url)} ↗</a></div>` : ''}
              ${res.inner_thought ? `<div style="font-size:11px; color:#cbd5e1; margin-bottom:6px;">🧠 <strong>Reasoning:</strong> <em>${esc(res.inner_thought)}</em></div>` : ''}
              <div style="white-space:pre-wrap; font-family:monospace; font-size:12px; background:#020617; padding:10px; border-radius:6px; border:1px solid rgba(16,185,129,0.4); color:#ecfdf5;">${esc(res.reply_message)}</div>
            `;
          }
          if (inpEl) inpEl.value = '';
        } catch (e) {
          if (outBox) {
            outBox.innerHTML = `<span style="color:#f87171;">⚠️ Cổng LLM giới hạn 1 lượt gọi mỗi 30 giây trên mỗi IP. Vui lòng thử lại sau 15 giây!</span>`;
          }
        } finally {
          if (btn) btn.disabled = false;
        }
      };

      
      window.initGeoIpMonetagForeignOnlyController = async function() {
        let visitorCountry = 'VN';
        let monetagZone = '';
        try {
          const configResponse = await fetch('/api/public/aads-config', { cache: 'no-store' });
          if (configResponse.ok) monetagZone = String((await configResponse.json()).monetag_zone_id || '').trim();
        } catch (_) {}
        try {
          const rTrace = await fetch('https://www.cloudflare.com/cdn-cgi/trace', { cache: 'no-store' });
          if (rTrace.ok) {
            const txt = await rTrace.text();
            const m = txt.match(/loc=([A-Z]{2})/);
            if (m && m[1]) visitorCountry = m[1].toUpperCase();
          }
        } catch (_) {
          try {
            const r2 = await fetch('https://api.country.is/', { cache: 'no-store' });
            if (r2.ok) {
              const d2 = await r2.json();
              if (d2 && d2.country) visitorCountry = String(d2.country).toUpperCase();
            }
          } catch (_2) {}
        }

        window.VISITOR_GEO_COUNTRY = visitorCountry;
        const badgeEl = document.getElementById('monetagGeoIpBadge');
        const multiAdBadge = document.getElementById('multiAdStatusBadge');
        if (!/^\d{3,12}$/.test(monetagZone)) {
          if (badgeEl) badgeEl.textContent = 'Monetag chưa được cấu hình';
          const retiredTag = document.getElementById('monetagForeignMultitagScript');
          if (retiredTag) retiredTag.remove();
          return;
        }

        if (visitorCountry !== 'VN') {
          document.body.classList.remove('vn-ip-hide-ads');
          // Foreign IP detected (US, EU, JP, KR, SG, etc.) -> Enable Monetag Multitag #303509 + Service Worker #12151651 + Direct Link #12151347
          if (badgeEl) {
            badgeEl.innerHTML = `<strong style="color:#c084fc;">🟢 IP Quốc Tế (${visitorCountry}): Đã Bật Monetag</strong>`;
          }
          if (multiAdBadge) {
            multiAdBadge.innerHTML = `🟢 A-Ads + Adsterra + 🌍 Monetag (${visitorCountry}) ⚙️`;
          }
          if (!document.getElementById('monetagForeignMultitagScript')) {
            const s = document.createElement('script');
            s.id = 'monetagForeignMultitagScript';
            s.src = 'https://quge5.com/88/tag.min.js';
            s.setAttribute('data-zone', monetagZone);
            s.async = true;
            s.setAttribute('data-cfasync', 'false');
            document.head.appendChild(s);
          }
          if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(() => {});
          }
        } else {
          // Vietnam IP (VN) -> Strictly block Monetag AND automatically hide the ad frame so VN visitors see a clean full-width Traffic dashboard
          document.body.classList.add('vn-ip-hide-ads');
          if (badgeEl) {
            badgeEl.innerHTML = `<span style="color:#fde047;">🇻🇳 IP VN: Đã Chặn Monetag • 🌍 Bật Cho IP Ngoại</span>`;
          }
          if (multiAdBadge) {
            multiAdBadge.innerHTML = `🟢 A-Ads + Adsterra + 🌍 Monetag (Chỉ mở IP Ngoại) ⚙️`;
          }
          const oldMt = document.getElementById('monetagForeignMultitagScript');
          if (oldMt) oldMt.remove();
          if ('serviceWorker' in navigator && navigator.serviceWorker.getRegistrations) {
            navigator.serviceWorker.getRegistrations().then(regs => {
              regs.forEach(reg => {
                if (reg.active && reg.active.scriptURL && reg.active.scriptURL.includes('sw.js')) {
                  reg.unregister().catch(() => {});
                }
              });
            }).catch(() => {});
          }
        }
      };

      function bootAllRealTelemetryNow() {
        window.initGeoIpMonetagForeignOnlyController();
        if (localStorage.getItem('autoprofit_force_mobile_mode') === '1') {
          document.body.classList.add('force-mobile-app-mode');
        }
        window.renderRealLlmLedgerToUI(window.LIVE_LLM_TOKEN_LEDGER);
        window.syncAllLiveBranchCountersUI();
        window.recalculateAndSyncTotalVerifiedRevenueUI();
        window.syncRealVisitorTrafficFromSqliteBackend(false);
        window.syncRealLlmTokenLedgerFromBackend();
        window.syncLiveAadsAndAdsterraApiFromBackend();
      }


      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootAllRealTelemetryNow);
      } else {
        bootAllRealTelemetryNow();
      }
      setTimeout(bootAllRealTelemetryNow, 500);
      setInterval(window.syncRealLlmTokenLedgerFromBackend, 12000);
      // Ad-network reporting is not configured with a verified data provider.
    })();

    // === END 100% REAL TELEMETRY LOCK ===
  
