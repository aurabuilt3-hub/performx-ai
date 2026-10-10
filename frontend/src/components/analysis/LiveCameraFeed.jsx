import React, { useEffect, useRef, useState, useCallback } from 'react';
import { 
  Camera, 
  CameraOff, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Cpu,
  Info,
  Crosshair,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { apiClient } from '../../services/api';
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

export default function LiveCameraFeed({ showTelemetry = true, compact = false }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const landmarkerRef = useRef(null);
  const animFrameRef = useRef(null);
  const lastVideoTimeRef = useRef(-1);
  const streamRef = useRef(null); // Reliable ref for active MediaStream
  const lastIngestionTimeRef = useRef(0); // Cadence throttle for backend ingestion (~100ms)
  const isIngestingRef = useRef(false);

  // Finite State Machine for Real Rep Counting
  // States: 'standing' -> 'descending' -> 'bottom' -> 'ascending' -> 'standing' (rep finished)
  const repStateRef = useRef('standing');
  const minKneeAngleInRepRef = useRef(180);

  const { 
    cameraState, 
    setCameraState, 
    activeSession, 
    setActiveSession, 
    settings,
    startMovementSession,
    resetMovementSession,
    calibrateStandingPose,
  } = useApp();
  const [modelLoading, setModelLoading] = useState(false);
  const [permissionError, setPermissionError] = useState(null);
  const [demoAngle, setDemoAngle] = useState(160);
  const [calibrationInProgress, setCalibrationInProgress] = useState(false);
  const latestLandmarksRef = useRef(null);

  // Initialize MediaPipe PoseLandmarker once
  useEffect(() => {
    let isMounted = true;
    async function initMediaPipe() {
      try {
        setModelLoading(true);
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );
        const landmarker = await PoseLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numPoses: 1,
          minPoseDetectionConfidence: 0.5,
          minPosePresenceConfidence: 0.5,
          minTrackingConfidence: 0.5
        });
        if (isMounted) {
          landmarkerRef.current = landmarker;
          setModelLoading(false);
        }
      } catch (err) {
        console.warn("MediaPipe Pose Landmarker fallback notice:", err);
        if (isMounted) setModelLoading(false);
      }
    }

    initMediaPipe();

    return () => {
      isMounted = false;
      // Stop all camera hardware tracks on unmount using streamRef
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          try { track.stop(); } catch (e) { /* ignore */ }
        });
        streamRef.current = null;
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  // Play audio chime for completed repetition
  const playRepAudioChime = () => {
    if (!settings?.soundCues) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch (e) {
      // AudioContext policy suppression or muted device
    }
  };

  // Helper to calculate angle between 3 2D points (A-B-C with B as vertex)
  const calculateAngle = (A, B, C) => {
    const radians = Math.atan2(C.y - B.y, C.x - B.x) - Math.atan2(A.y - B.y, A.x - B.x);
    let angle = Math.abs((radians * 180.0) / Math.PI);
    if (angle > 180.0) angle = 360.0 - angle;
    return Math.round(angle);
  };

  // Start Real Camera
  const handleStartCamera = async () => {
    setPermissionError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      setCameraState(prev => ({
        ...prev,
        active: true,
        stream,
        permissionGranted: true,
        isDemoMode: false,
      }));

      // Reset rep FSM state
      repStateRef.current = 'standing';
      minKneeAngleInRepRef.current = 180;

      // Start backend movement session
      startMovementSession();

      startTrackingLoop();
    } catch (err) {
      console.error("Camera access error:", err);
      setPermissionError("Camera access denied or hardware not found. You can test live workflows using Simulated Demo Mode.");
      setCameraState(prev => ({
        ...prev,
        active: false,
        stream: null,
      }));
    }
  };

  // Stop Real Camera
  const handleStopCamera = async () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        try { track.stop(); } catch (e) { /* ignore */ }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }

    setCameraState(prev => ({
      ...prev,
      active: false,
      stream: null,
      isDemoMode: false,
    }));

    // Reset canvas overlay
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }

    // Set active session back to idle
    setActiveSession(prev => ({
      ...prev,
      trackingStatus: 'idle',
      kneeAngle: null,
      hipAngle: null,
      movementPhase: 'Idle',
      feedbackLevel: 'neutral',
      feedbackMessage: 'Camera stream stopped. Video processing inactive.',
      trackingConfidence: 0,
    }));
  };

  // Toggle Simulated Demo Mode
  const handleToggleDemo = () => {
    if (cameraState.isDemoMode) {
      setCameraState(prev => ({ ...prev, active: false, isDemoMode: false }));
      setActiveSession(prev => ({
        ...prev,
        trackingStatus: 'idle',
        kneeAngle: null,
        hipAngle: null,
        movementPhase: 'Idle',
        feedbackLevel: 'neutral',
        feedbackMessage: 'Demo mode ended. Stream idle.',
      }));
    } else {
      // Turn off real camera if running
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => {
          try { t.stop(); } catch (e) { /* ignore */ }
        });
        streamRef.current = null;
      }
      setCameraState(prev => ({
        ...prev,
        active: true,
        stream: null,
        isDemoMode: true,
      }));
    }
  };

  // Main Tracking Loop for Real Camera
  const startTrackingLoop = () => {
    const render = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.paused || video.ended) {
        animFrameRef.current = requestAnimationFrame(render);
        return;
      }

      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
      }

      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (landmarkerRef.current && video.currentTime !== lastVideoTimeRef.current) {
        lastVideoTimeRef.current = video.currentTime;
        const startTimeMs = performance.now();
        const results = landmarkerRef.current.detectForVideo(video, startTimeMs);

        if (results && results.landmarks && results.landmarks.length > 0) {
          const landmarks = results.landmarks[0];
          drawLandmarks(ctx, landmarks, canvas.width, canvas.height);

          // Format validated 33-landmark payload for backend ingestion & calibration
          if (landmarks.length === 33) {
            const mappedLandmarks = landmarks.map(lm => ({
              x: Number.isFinite(lm.x) ? lm.x : 0.0,
              y: Number.isFinite(lm.y) ? lm.y : 0.0,
              z: Number.isFinite(lm.z) ? lm.z : 0.0,
              visibility: Number.isFinite(lm.visibility) ? lm.visibility : 1.0,
            }));

            const landmarkPayload = {
              timestamp: Date.now() / 1000.0,
              landmarks: mappedLandmarks,
            };
            latestLandmarksRef.current = landmarkPayload;

            // Stream to backend movement engine at 100ms cadence without blocking render loop
            const now = performance.now();
            if (activeSession.backendSessionId && !isIngestingRef.current && (now - lastIngestionTimeRef.current >= 100)) {
              lastIngestionTimeRef.current = now;
              isIngestingRef.current = true;
              apiClient.sessions.sendLandmarks(activeSession.backendSessionId, landmarkPayload)
                .then(engineResult => {
                  if (engineResult) {
                    setActiveSession(prev => ({
                      ...prev,
                      validReps: engineResult.repetition_count ?? prev.validReps,
                      movementPhase: engineResult.phase ?? prev.movementPhase,
                      symmetryScore: engineResult.symmetry !== undefined && engineResult.symmetry !== null
                        ? Math.round(engineResult.symmetry * 100) 
                        : prev.symmetryScore,
                    }));
                  }
                })
                .catch(ingestErr => {
                  // Non-fatal streaming glitch; keep rendering
                  console.debug('Landmark stream packet drop:', ingestErr.message);
                })
                .finally(() => {
                  isIngestingRef.current = false;
                });
            }
          }

          // Key landmarks: Hip (24), Knee (26), Ankle (28), Shoulder (12)
          const hip = landmarks[24];
          const knee = landmarks[26];
          const ankle = landmarks[28];
          const shoulder = landmarks[12];

          if (hip && knee && ankle && hip.visibility > 0.5 && knee.visibility > 0.5 && ankle.visibility > 0.5) {
            const calculatedKneeAngle = calculateAngle(hip, knee, ankle);
            const calculatedHipAngle = shoulder ? calculateAngle(shoulder, hip, knee) : 75;

            // --- REPETITION COUNTING FINITE STATE MACHINE ---
            let repIncremented = false;
            let repScoreAwarded = 90;
            const currentState = repStateRef.current;

            if (currentState === 'standing') {
              if (calculatedKneeAngle < 130) {
                repStateRef.current = 'descending';
                minKneeAngleInRepRef.current = calculatedKneeAngle;
              }
            } else if (currentState === 'descending') {
              if (calculatedKneeAngle < minKneeAngleInRepRef.current) {
                minKneeAngleInRepRef.current = calculatedKneeAngle;
              }
              if (calculatedKneeAngle <= 95) {
                repStateRef.current = 'bottom';
              } else if (calculatedKneeAngle > 135) {
                // Return without reaching depth
                repStateRef.current = 'standing';
              }
            } else if (currentState === 'bottom') {
              if (calculatedKneeAngle < minKneeAngleInRepRef.current) {
                minKneeAngleInRepRef.current = calculatedKneeAngle;
              }
              if (calculatedKneeAngle > 105) {
                repStateRef.current = 'ascending';
              }
            } else if (currentState === 'ascending') {
              if (calculatedKneeAngle > 135) {
                // Completed Repetition!
                repIncremented = true;
                const minDepth = minKneeAngleInRepRef.current;
                repScoreAwarded = minDepth <= 90 ? 98 : minDepth <= 100 ? 88 : 72;
                repStateRef.current = 'standing';
                minKneeAngleInRepRef.current = 180;
                playRepAudioChime();
              }
            }

            // Determine Phase String and Form Feedback
            let phase = 'Standing / Lockout';
            let feedback = 'Upright position. Ready for next repetition.';
            let level = 'neutral';

            if (repStateRef.current === 'descending') {
              phase = 'Eccentric (Descent)';
              feedback = 'Descending into squat. Keep knees aligned over toes.';
              level = 'optimal';
            } else if (repStateRef.current === 'bottom') {
              phase = 'Bottom Hold';
              feedback = calculatedKneeAngle <= 90 
                ? 'Optimal parallel depth reached (≤90°)! Drive back up.' 
                : 'Approaching depth. Ensure thighs reach parallel to ground.';
              level = calculatedKneeAngle <= 90 ? 'optimal' : 'warning';
            } else if (repStateRef.current === 'ascending') {
              phase = 'Concentric (Ascent)';
              feedback = 'Powering up through midfoot. Maintain chest posture.';
              level = 'optimal';
            }

            // Update real workout telemetry
            setActiveSession(prev => {
              const nextReps = repIncremented ? prev.currentReps + 1 : prev.currentReps;
              let nextSet = prev.currentSet;
              let resetReps = nextReps;

              if (repIncremented && nextReps >= prev.targetReps) {
                nextSet = Math.min(prev.targetSets, prev.currentSet + 1);
                resetReps = 0;
              }

              const newAngles = repIncremented 
                ? [...(prev.completedRepAngles || []), repScoreAwarded]
                : (prev.completedRepAngles || []);
              
              const calculatedFormScore = newAngles.length > 0 
                ? Math.round(newAngles.reduce((a, b) => a + b, 0) / newAngles.length)
                : (prev.formScore || 94);

              return {
                ...prev,
                currentReps: resetReps,
                currentSet: nextSet,
                completedRepAngles: newAngles,
                formScore: calculatedFormScore,
                kneeAngle: calculatedKneeAngle,
                hipAngle: calculatedHipAngle,
                movementPhase: phase,
                feedbackMessage: feedback,
                feedbackLevel: level,
                trackingConfidence: Math.round(knee.visibility * 100),
                trackingStatus: 'tracking',
              };
            });
          }
        } else {
          // Tracking Lost / Occluded State
          setActiveSession(prev => ({
            ...prev,
            trackingStatus: 'unreliable',
            feedbackLevel: 'neutral',
            feedbackMessage: 'Unable to assess movement reliably. Please ensure your full body is visible in the frame.',
            trackingConfidence: 0,
          }));
        }
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);
  };

  // Draw skeletal lines and landmarks on Canvas
  const drawLandmarks = (ctx, landmarks, w, h) => {
    const connections = [
      [11, 12], [11, 23], [12, 24], [23, 24], // Torso
      [11, 13], [13, 15], // Left Arm
      [12, 14], [14, 16], // Right Arm
      [23, 25], [25, 27], // Left Leg
      [24, 26], [26, 28], // Right Leg
    ];

    ctx.lineWidth = 4;
    ctx.strokeStyle = '#38BDF8'; // Cyan kinematic limb vectors

    connections.forEach(([i, j]) => {
      const p1 = landmarks[i];
      const p2 = landmarks[j];
      if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
        ctx.beginPath();
        ctx.moveTo(p1.x * w, p1.y * h);
        ctx.lineTo(p2.x * w, p2.y * h);
        ctx.stroke();
      }
    });

    // Draw Joint Nodes
    landmarks.forEach((p, idx) => {
      if (p.visibility > 0.5 && (idx >= 11 && idx <= 28)) {
        ctx.beginPath();
        ctx.arc(p.x * w, p.y * h, idx === 26 || idx === 25 ? 8 : 6, 0, 2 * Math.PI);
        ctx.fillStyle = idx === 26 || idx === 25 ? '#3D8065' : '#F26B3A';
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#FFFFFF';
        ctx.stroke();
      }
    });
  };

  // Simulated Demo Animation Loop when in Demo Mode
  useEffect(() => {
    if (!cameraState.isDemoMode) return;

    let time = 0;
    let lastCycleWasStanding = true;

    const interval = setInterval(() => {
      time += 0.05;
      const cycle = (Math.sin(time) + 1) / 2; // 0 (standing) to 1 (depth)
      const simulatedAngle = Math.round(160 - cycle * 75); // 160 deg down to 85 deg
      setDemoAngle(simulatedAngle);

      // Demo rep increment
      let demoRepIncremented = false;
      if (simulatedAngle > 150 && !lastCycleWasStanding) {
        demoRepIncremented = true;
        lastCycleWasStanding = true;
      } else if (simulatedAngle <= 90) {
        lastCycleWasStanding = false;
      }

      setActiveSession(prev => {
        let phase = 'Eccentric (Descent)';
        let feedback = '[SIMULATED DEMO] Kinematic descent vector active.';
        let level = 'optimal';

        if (simulatedAngle <= 90) {
          phase = 'Bottom Hold';
          feedback = '[SIMULATED DEMO] Parallel depth achieved (85°).';
          level = 'optimal';
        } else if (simulatedAngle > 140) {
          phase = 'Lockout / Standing';
          feedback = '[SIMULATED DEMO] Standing upright. Ready for repetition.';
          level = 'neutral';
        }

        const nextReps = demoRepIncremented ? prev.currentReps + 1 : prev.currentReps;

        return {
          ...prev,
          currentReps: nextReps,
          kneeAngle: simulatedAngle,
          hipAngle: Math.round(simulatedAngle * 0.8),
          movementPhase: phase,
          feedbackMessage: feedback,
          feedbackLevel: level,
          trackingConfidence: 99,
          trackingStatus: 'tracking',
        };
      });
    }, 50);

    return () => clearInterval(interval);
  }, [cameraState.isDemoMode]);

  return (
    <div className="flex-col gap-4">
      {/* Viewport Box */}
      <div className="viewport-box" style={{ minHeight: compact ? 260 : 340 }}>
        {/* Real Camera Video */}
        {cameraState.active && !cameraState.isDemoMode && (
          <>
            <video 
              ref={videoRef} 
              className="camera-video" 
              playsInline 
              muted 
            />
            <canvas 
              ref={canvasRef} 
              className="camera-overlay-canvas" 
            />
          </>
        )}

        {/* Simulated Demo Mode Canvas & Articulated Wireframe */}
        {cameraState.isDemoMode && (
          <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="220" height="280" viewBox="0 0 200 260" style={{ transform: 'scale(0.95)' }}>
              {/* Head */}
              <circle cx="100" cy="35" r="14" fill="#F26B3A" stroke="#FFFFFF" strokeWidth="2" />
              {/* Spine */}
              <line x1="100" y1="50" x2="100" y2="130" stroke="#CBD5E1" strokeWidth="5" strokeLinecap="round" />
              {/* Shoulders */}
              <line x1="65" y1="70" x2="135" y2="70" stroke="#CBD5E1" strokeWidth="5" strokeLinecap="round" />
              {/* Pelvis */}
              <line x1="75" y1="130" x2="125" y2="130" stroke="#CBD5E1" strokeWidth="5" strokeLinecap="round" />
              {/* Left Leg (Dynamic Knee based on demoAngle) */}
              <line 
                x1="75" 
                y1="130" 
                x2={50 + (160 - demoAngle) * 0.15} 
                y2={190 + (160 - demoAngle) * 0.2} 
                stroke="#38BDF8" 
                strokeWidth="5" 
                strokeLinecap="round" 
              />
              <line 
                x1={50 + (160 - demoAngle) * 0.15} 
                y1={190 + (160 - demoAngle) * 0.2} 
                x2="60" 
                y2="250" 
                stroke="#38BDF8" 
                strokeWidth="5" 
                strokeLinecap="round" 
              />
              {/* Right Leg */}
              <line 
                x1="125" 
                y1="130" 
                x2={150 - (160 - demoAngle) * 0.15} 
                y2={190 + (160 - demoAngle) * 0.2} 
                stroke="#38BDF8" 
                strokeWidth="5" 
                strokeLinecap="round" 
              />
              <line 
                x1={150 - (160 - demoAngle) * 0.15} 
                y1={190 + (160 - demoAngle) * 0.2} 
                x2="140" 
                y2="250" 
                stroke="#38BDF8" 
                strokeWidth="5" 
                strokeLinecap="round" 
              />
              {/* Knee Joint Accent Nodes */}
              <circle cx={50 + (160 - demoAngle) * 0.15} cy={190 + (160 - demoAngle) * 0.2} r="8" fill="#3D8065" stroke="#FFF" strokeWidth="2" />
              <circle cx={150 - (160 - demoAngle) * 0.15} cy={190 + (160 - demoAngle) * 0.2} r="8" fill="#3D8065" stroke="#FFF" strokeWidth="2" />
            </svg>
          </div>
        )}

        {/* Idle Inactive State */}
        {!cameraState.active && (
          <div className="flex-col items-center gap-3 text-center" style={{ padding: 24, zIndex: 5 }}>
            <div className="metric-icon-box" style={{ width: 56, height: 56, background: 'rgba(255, 255, 255, 0.1)', color: '#FFFFFF' }}>
              <Camera size={28} />
            </div>
            <div>
              <h4 style={{ color: '#FFFFFF', marginBottom: 4 }}>Camera Stream Inactive</h4>
              <p style={{ color: '#94A3B8', fontSize: '0.85rem', maxWidth: 280 }}>
                Activate your camera for verified local pose estimation, or launch simulated demo mode.
              </p>
            </div>
            <div className="flex-row gap-2" style={{ marginTop: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={handleStartCamera}>
                <Camera size={15} />
                <span>Start Camera</span>
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleToggleDemo}>
                <span>Try Demo Feed</span>
              </button>
            </div>
          </div>
        )}

        {/* Top Badges */}
        {cameraState.active && (
          <div className="viewport-badge">
            <span className={`live-dot ${cameraState.isDemoMode ? 'amber' : ''}`} />
            <span>{cameraState.isDemoMode ? 'SIMULATED DEMO MODE (SYNTHETIC)' : 'LIVE CAMERA • LOCAL ON-DEVICE'}</span>
          </div>
        )}

        {/* Bottom Floating Control Bar */}
        {cameraState.active && (
          <div className="viewport-controls-bar">
            <div className="flex-row gap-2 items-center">
              <span className="badge-pill" style={{ background: 'rgba(17, 25, 54, 0.8)', color: '#38BDF8', border: '1px solid rgba(255, 255, 255, 0.15)' }}>
                <Cpu size={12} />
                <span>60 FPS • Edge AI</span>
              </span>

              {/* Calibration Badge / Button */}
              {!cameraState.isDemoMode && (
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.75rem', padding: '4px 10px', height: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  onClick={async () => {
                    if (calibrationInProgress) return;
                    if (!latestLandmarksRef.current) {
                      alert('Awaiting full skeletal pose detection before calibration.');
                      return;
                    }
                    setCalibrationInProgress(true);
                    try {
                      await calibrateStandingPose(latestLandmarksRef.current);
                    } catch (e) {
                      console.warn('Calibration attempt error:', e.message);
                    } finally {
                      setCalibrationInProgress(false);
                    }
                  }}
                  disabled={calibrationInProgress}
                  title="Calibrate standing baseline angles with current posture"
                >
                  {calibrationInProgress ? <Loader2 size={12} className="animate-spin" /> : <Crosshair size={12} />}
                  <span>
                    {calibrationInProgress 
                      ? 'Calibrating...' 
                      : activeSession.calibrationStatus === 'calibrated' 
                        ? 'Recalibrate Pose' 
                        : 'Calibrate Standing Pose'}
                  </span>
                </button>
              )}
            </div>

            <button 
              className="btn btn-danger btn-sm"
              onClick={cameraState.isDemoMode ? handleToggleDemo : handleStopCamera}
              title="Stop camera session"
            >
              <CameraOff size={14} />
              <span>{cameraState.isDemoMode ? 'Exit Demo' : 'Stop Camera'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Permission Error Banner */}
      {permissionError && (
        <div className="feedback-box feedback-warning">
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span>{permissionError}</span>
        </div>
      )}

      {/* Form Feedback Card (Green / Amber / Red / Neutral) */}
      <div className={`feedback-box feedback-${activeSession.feedbackLevel}`}>
        {activeSession.feedbackLevel === 'optimal' && <CheckCircle2 size={18} style={{ flexShrink: 0 }} />}
        {activeSession.feedbackLevel === 'warning' && <AlertTriangle size={18} style={{ flexShrink: 0 }} />}
        {activeSession.feedbackLevel === 'error' && <AlertTriangle size={18} style={{ flexShrink: 0 }} />}
        {activeSession.feedbackLevel === 'neutral' && <Info size={18} style={{ flexShrink: 0 }} />}
        <div className="flex-col">
          <span className="font-semibold">{activeSession.feedbackMessage}</span>
          <span style={{ fontSize: '0.785rem', opacity: 0.85, marginTop: 2 }}>
            Tracking status: {
              activeSession.trackingStatus === 'tracking' 
                ? (cameraState.isDemoMode ? 'Simulated Synthetic Tracking' : `Active (${activeSession.trackingConfidence}% Confidence)`)
                : activeSession.trackingStatus === 'unreliable'
                  ? 'Unreliable / Subject Occluded'
                  : 'Idle (Awaiting Stream)'
            }
          </span>
        </div>
      </div>

      {/* Real-time Telemetry Bar */}
      {showTelemetry && (
        <div className="telemetry-bar">
          <div className="telemetry-item">
            <span className="telemetry-label">Knee Angle</span>
            <span className="telemetry-value accent">
              {activeSession.kneeAngle !== null ? `${activeSession.kneeAngle}°` : '--'}
            </span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Hip Hinge</span>
            <span className="telemetry-value">
              {activeSession.hipAngle !== null ? `${activeSession.hipAngle}°` : '--'}
            </span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Movement Phase</span>
            <span className="telemetry-value teal" style={{ fontSize: '1.05rem', textTransform: 'capitalize' }}>
              {activeSession.movementPhase}
            </span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Rep Count</span>
            <span className="telemetry-value">
              {activeSession.currentReps} / {activeSession.targetReps}
            </span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Form Accuracy</span>
            <span className="telemetry-value" style={{ color: 'var(--success-green)' }}>
              {activeSession.formScore !== null ? `${activeSession.formScore}%` : '--'}
            </span>
          </div>
        </div>
      )}

      {/* Local Edge AI Privacy Transparency Banner */}
      <div className="flex-row items-center gap-2" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '0 4px' }}>
        <ShieldCheck size={16} className="text-teal" style={{ flexShrink: 0 }} />
        <span>
          <strong>Zero Server Uploads:</strong> Camera frames are processed strictly in-browser via WebAssembly. Your video stream never leaves your device.
        </span>
      </div>
    </div>
  );
}
