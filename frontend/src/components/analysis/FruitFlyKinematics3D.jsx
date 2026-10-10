import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { RotateCcw, Activity } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function FruitFlyKinematics3D({ height = '100%', showControls = true }) {
  const containerRef = useRef(null);
  const { activeSession } = useApp();
  const [viewPreset, setViewPreset] = useState('perspective'); // perspective, sagittal, frontal, transverse
  const [showTrails, setShowTrails] = useState(true);

  // Three.js internal references
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const jointsRef = useRef({});
  const bonesRef = useRef([]);
  const animFrameRef = useRef(null);

  // Mouse drag interaction
  const isDraggingRef = useRef(false);
  const prevMousePosRef = useRef({ x: 0, y: 0 });
  const cameraRotationRef = useRef({ theta: 0.4, phi: 0.25, radius: 4.8 });

  // Update Camera based on rotation state
  const updateCameraPosition = useCallback(() => {
    if (!cameraRef.current) return;
    const { theta, phi, radius } = cameraRotationRef.current;
    const x = radius * Math.cos(phi) * Math.sin(theta);
    const y = radius * Math.sin(phi);
    const z = radius * Math.cos(phi) * Math.cos(theta);

    cameraRef.current.position.set(x, y, z);
    cameraRef.current.lookAt(0, -0.3, 0);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth || 400;
    const heightPx = containerRef.current.clientHeight || 300;

    // 1. Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color('#FAF8F1'); // Matching PERFORMX warm ivory background

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / heightPx, 0.1, 100);
    cameraRef.current = camera;
    updateCameraPosition();

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;

    // Clean container before appending
    while (containerRef.current.firstChild) {
      containerRef.current.removeChild(containerRef.current.firstChild);
    }
    containerRef.current.appendChild(renderer.domElement);

    // 4. Lighting (Clean soft studio illumination)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.95);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // Rim lighting with burnt orange and warm amber accents
    const orangeRim = new THREE.PointLight(0xF26B3A, 1.2, 10);
    orangeRim.position.set(-4, 3, -3);
    scene.add(orangeRim);

    const amberRim = new THREE.PointLight(0xD99A37, 1.0, 10);
    amberRim.position.set(4, -1, 3);
    scene.add(amberRim);

    // 5. Ground Coordinate Grid (Drosophila motion tracking reference plane)
    const gridHelper = new THREE.GridHelper(6, 20, 0xF26B3A, 0xE8E3D9);
    gridHelper.position.y = -1.6;
    scene.add(gridHelper);

    // 6. Build Drosophila-Inspired Articulated Kinematic Skeleton
    const jointMaterial = new THREE.MeshStandardMaterial({
      color: 0xF26B3A, // Burnt orange primary joints
      roughness: 0.2,
      metalness: 0.3,
      emissive: 0xDB5428,
      emissiveIntensity: 0.25,
    });

    const jointAccentMaterial = new THREE.MeshStandardMaterial({
      color: 0x171717, // Near-black with subtle natural green emissive for tracking joints
      roughness: 0.1,
      metalness: 0.7,
      emissive: 0x3D8065,
      emissiveIntensity: 0.4,
    });

    const boneMaterial = new THREE.MeshStandardMaterial({
      color: 0xD4CEBE,
      roughness: 0.4,
      metalness: 0.2,
    });

    // Define 17 Anatomical Keypoints
    const jointNames = [
      'head', 'neck', 'spine', 'pelvis',
      'shoulderL', 'elbowL', 'wristL',
      'shoulderR', 'elbowR', 'wristR',
      'hipL', 'kneeL', 'ankleL',
      'hipR', 'kneeR', 'ankleR'
    ];

    const joints = {};
    const jointGeom = new THREE.SphereGeometry(0.065, 16, 16);
    const jointAccentGeom = new THREE.SphereGeometry(0.08, 16, 16);

    jointNames.forEach(name => {
      const isAccent = name.includes('knee') || name.includes('hip') || name.includes('pelvis');
      const mesh = new THREE.Mesh(
        isAccent ? jointAccentGeom : jointGeom, 
        isAccent ? jointAccentMaterial : jointMaterial
      );
      scene.add(mesh);
      joints[name] = mesh;
    });
    jointsRef.current = joints;

    // Bone links definition
    const connections = [
      ['head', 'neck'],
      ['neck', 'spine'],
      ['spine', 'pelvis'],
      ['neck', 'shoulderL'],
      ['shoulderL', 'elbowL'],
      ['elbowL', 'wristL'],
      ['neck', 'shoulderR'],
      ['shoulderR', 'elbowR'],
      ['elbowR', 'wristR'],
      ['pelvis', 'hipL'],
      ['hipL', 'kneeL'],
      ['kneeL', 'ankleL'],
      ['pelvis', 'hipR'],
      ['hipR', 'kneeR'],
      ['kneeR', 'ankleR'],
    ];

    const bones = [];
    connections.forEach(([p1, p2]) => {
      const boneGeom = new THREE.CylinderGeometry(0.03, 0.03, 1, 8);
      const boneMesh = new THREE.Mesh(boneGeom, boneMaterial);
      scene.add(boneMesh);
      bones.push({ mesh: boneMesh, from: p1, to: p2 });
    });
    bonesRef.current = bones;

    // Kinematic Trajectory Ribbons (Knee and Hip paths)
    const trailPointsMax = 40;
    const kneeLTrailPoints = [];
    const hipTrailPoints = [];

    const trailGeomL = new THREE.BufferGeometry();
    const trailMaterialL = new THREE.LineBasicMaterial({ color: 0x3D8065, linewidth: 2, transparent: true, opacity: 0.85 });
    const trailLineL = new THREE.Line(trailGeomL, trailMaterialL);
    scene.add(trailLineL);

    const trailGeomR = new THREE.BufferGeometry();
    const trailMaterialR = new THREE.LineBasicMaterial({ color: 0xF26B3A, linewidth: 2, transparent: true, opacity: 0.85 });
    const trailLineR = new THREE.Line(trailGeomR, trailMaterialR);
    scene.add(trailLineR);

    // Animation Loop
    let time = 0;
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      time += 0.03;

      // Squat kinematics oscillation matching active session
      // Phase cycle: 0 -> 1 -> 0
      const squatCycle = (Math.sin(time) + 1) / 2; // 0 = standing, 1 = deep squat
      const depth = squatCycle * 0.7; // depth displacement

      // Animate joints in 3D coordinate space
      if (joints.pelvis) {
        joints.pelvis.position.set(0, 0.1 - depth, -squatCycle * 0.25);
      }
      if (joints.spine) {
        joints.spine.position.set(0, 0.5 - depth, -squatCycle * 0.15);
      }
      if (joints.neck) {
        joints.neck.position.set(0, 0.85 - depth, -squatCycle * 0.05);
      }
      if (joints.head) {
        joints.head.position.set(0, 1.1 - depth, 0);
      }

      // Arms (holding barbell or guard)
      if (joints.shoulderL && joints.shoulderR) {
        joints.shoulderL.position.set(-0.35, 0.8 - depth, -0.05);
        joints.shoulderR.position.set(0.35, 0.8 - depth, -0.05);
      }
      if (joints.elbowL && joints.elbowR) {
        joints.elbowL.position.set(-0.45, 0.55 - depth, 0.15);
        joints.elbowR.position.set(0.45, 0.55 - depth, 0.15);
      }
      if (joints.wristL && joints.wristR) {
        joints.wristL.position.set(-0.3, 0.7 - depth, 0.25);
        joints.wristR.position.set(0.3, 0.7 - depth, 0.25);
      }

      // Hips
      if (joints.hipL && joints.hipR) {
        joints.hipL.position.set(-0.24, 0.05 - depth, -squatCycle * 0.25);
        joints.hipR.position.set(0.24, 0.05 - depth, -squatCycle * 0.25);
      }

      // Knees (travel forward and bend)
      const kneeZ = 0.1 + squatCycle * 0.28;
      const kneeY = -0.65 - depth * 0.45;
      if (joints.kneeL && joints.kneeR) {
        joints.kneeL.position.set(-0.28 - squatCycle * 0.06, kneeY, kneeZ);
        joints.kneeR.position.set(0.28 + squatCycle * 0.06, kneeY, kneeZ);
      }

      // Ankles / Feet (anchored to ground)
      if (joints.ankleL && joints.ankleR) {
        joints.ankleL.position.set(-0.3, -1.45, 0.05);
        joints.ankleR.position.set(0.3, -1.45, 0.05);
      }

      // Update connecting bones
      bones.forEach(({ mesh, from, to }) => {
        const p1 = joints[from].position;
        const p2 = joints[to].position;

        const distance = p1.distanceTo(p2);
        mesh.scale.set(1, distance, 1);

        const midpoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
        mesh.position.copy(midpoint);

        const direction = new THREE.Vector3().subVectors(p2, p1).normalize();
        const orientation = new THREE.Quaternion();
        orientation.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
        mesh.setRotationFromQuaternion(orientation);
      });

      // Update Kinematic Trajectory Ribbons
      if (showTrails && joints.kneeL && joints.pelvis) {
        kneeLTrailPoints.push(joints.kneeL.position.clone());
        if (kneeLTrailPoints.length > trailPointsMax) kneeLTrailPoints.shift();
        trailGeomL.setFromPoints(kneeLTrailPoints);

        hipTrailPoints.push(joints.pelvis.position.clone());
        if (hipTrailPoints.length > trailPointsMax) hipTrailPoints.shift();
        trailGeomR.setFromPoints(hipTrailPoints);

        trailLineL.visible = true;
        trailLineR.visible = true;
      } else {
        trailLineL.visible = false;
        trailLineR.visible = false;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!containerRef.current || !renderer || !camera) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', handleResize);
      try {
        jointGeom.dispose();
        jointAccentGeom.dispose();
        jointMaterial.dispose();
        jointAccentMaterial.dispose();
        boneMaterial.dispose();
        trailGeomL.dispose();
        trailGeomR.dispose();
        trailMaterialL.dispose();
        trailMaterialR.dispose();
        gridHelper.geometry.dispose();
        renderer.dispose();
        if (renderer.domElement && renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
      } catch (err) {
        /* ignore resource release errors */
      }
    };
  }, []);

  // View Preset Handler
  const handleSetPreset = (preset) => {
    setViewPreset(preset);
    if (preset === 'sagittal') {
      // 90 deg lateral side view
      cameraRotationRef.current = { theta: Math.PI / 2, phi: 0.1, radius: 4.8 };
    } else if (preset === 'frontal') {
      // 0 deg frontal coronal view
      cameraRotationRef.current = { theta: 0, phi: 0.1, radius: 4.8 };
    } else if (preset === 'transverse') {
      // Top down superior view
      cameraRotationRef.current = { theta: 0, phi: Math.PI / 2 - 0.1, radius: 4.8 };
    } else {
      // Perspective
      cameraRotationRef.current = { theta: 0.5, phi: 0.25, radius: 4.8 };
    }
    updateCameraPosition();
  };

  // Mouse Interaction (Orbit Rotate & Zoom)
  const handleMouseDown = (e) => {
    isDraggingRef.current = true;
    prevMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e) => {
    if (!isDraggingRef.current) return;
    const deltaX = e.clientX - prevMousePosRef.current.x;
    const deltaY = e.clientY - prevMousePosRef.current.y;

    cameraRotationRef.current.theta -= deltaX * 0.008;
    cameraRotationRef.current.phi = Math.max(-0.4, Math.min(Math.PI / 2 - 0.1, cameraRotationRef.current.phi + deltaY * 0.008));

    prevMousePosRef.current = { x: e.clientX, y: e.clientY };
    updateCameraPosition();
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e) => {
    cameraRotationRef.current.radius = Math.max(2.5, Math.min(8.0, cameraRotationRef.current.radius + e.deltaY * 0.003));
    updateCameraPosition();
  };

  return (
    <div 
      className="viewport-box light-3d" 
      style={{ height, width: '100%', position: 'relative', cursor: 'grab' }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Three.js Canvas Container */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Drosophila Badge */}
      <div className="viewport-badge light-badge">
        <span className="live-dot cyan" />
        <span>Drosophila 3D Kinematics</span>
      </div>

      {/* Controls Overlay */}
      {showControls && (
        <>
          <div className="kinematics-overlay-bar">
            <button 
              className={`btn btn-sm ${viewPreset === 'perspective' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => handleSetPreset('perspective')}
              title="3D Orbit View"
            >
              Orbit
            </button>
            <button 
              className={`btn btn-sm ${viewPreset === 'sagittal' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => handleSetPreset('sagittal')}
              title="Sagittal View (Side 90° for depth)"
            >
              Sagittal
            </button>
            <button 
              className={`btn btn-sm ${viewPreset === 'frontal' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => handleSetPreset('frontal')}
              title="Frontal View (Coronal 0° for knee tracking)"
            >
              Frontal
            </button>
            <button 
              className="btn btn-secondary btn-sm btn-icon"
              onClick={() => setShowTrails(!showTrails)}
              title={showTrails ? "Hide Trajectory Trails" : "Show Trajectory Trails"}
            >
              <Activity size={15} className={showTrails ? "text-cyan" : "text-muted"} />
            </button>
            <button 
              className="btn btn-secondary btn-sm btn-icon"
              onClick={() => handleSetPreset('perspective')}
              title="Reset 3D Camera"
            >
              <RotateCcw size={15} />
            </button>
          </div>

          {/* Scientific Biomechanical Legend */}
          <div className="kinematics-legend">
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: 'var(--cyan-accent)' }} />
              <span>Knee Spatial Path ({activeSession.kneeAngle}°)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: 'var(--primary-purple)' }} />
              <span>Pelvic Kinematic Vector ({activeSession.hipAngle}°)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: '#CBD5E1' }} />
              <span>Multi-segment Kinematic Chains</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
