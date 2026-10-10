import React, { useState } from 'react';
import Modal from '../components/common/Modal';
import { 
  Search, 
  Dumbbell, 
  Target, 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  Filter,
  Sparkles,
  ChevronRight
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ExerciseLibraryPage() {
  const { setActiveSession, setActiveTab } = useApp();
  const [search, setSearch] = useState('');
  const [muscleFilter, setMuscleFilter] = useState('All');
  const [selectedExerciseModal, setSelectedExerciseModal] = useState(null);

  const exercises = [
    {
      id: 'ex-1',
      name: 'Barbell Back Squat',
      muscleGroup: 'Legs & Quads',
      equipment: 'Barbell & Squat Rack',
      difficulty: 'Intermediate',
      targetAngle: '≤ 90° Knee Flexion (Parallel)',
      keyCues: 'Drive knees outward in line with second toe; maintain rigid thoracic extension.',
      commonMistakes: 'Knee valgus (knees caving inward), excessive forward torso lean, heel rise.',
      desc: 'The foundational lower body bilateral compound movement. Heavy recruitment of quadriceps, gluteus maximus, and spinal erectors.'
    },
    {
      id: 'ex-2',
      name: 'Romanian Deadlift (RDL)',
      muscleGroup: 'Hamstrings & Glutes',
      equipment: 'Barbell / Dumbbells',
      difficulty: 'Intermediate',
      targetAngle: '65° - 75° Hip Hinge',
      keyCues: 'Initiate by pushing pelvis posterior; maintain slight soft bend in knees.',
      commonMistakes: 'Lumbar flexion (rounding lower back), squatting the weight instead of hinging.',
      desc: 'Posterior chain eccentric loading. Maximizes hamstring stretch and glute recruitment without excessive spinal shear.'
    },
    {
      id: 'ex-3',
      name: 'Bulgarian Split Squat',
      muscleGroup: 'Legs & Quads',
      equipment: 'Dumbbells & Bench',
      difficulty: 'Intermediate',
      targetAngle: '85° Lead Knee Flexion',
      keyCues: 'Keep front heel grounded; descend vertically until trailing knee approaches floor.',
      commonMistakes: 'Overstriding causing hip flexor strain, torso twisting, lead knee caving.',
      desc: 'High-intensity unilateral movement correcting bilateral imbalances and improving hip stability.'
    },
    {
      id: 'ex-4',
      name: 'Incline Barbell Bench Press',
      muscleGroup: 'Chest & Shoulders',
      equipment: 'Barbell & Incline Bench',
      difficulty: 'Intermediate',
      targetAngle: '30° - 45° Bench Incline',
      keyCues: 'Retract and depress scapulae; touch bar to upper clavicular chest.',
      commonMistakes: 'Elbows flaring excessively at 90°, arching lower back off the pad.',
      desc: 'Targeted clavicular pectoralis major and anterior deltoid development with scapular stability.'
    },
    {
      id: 'ex-5',
      name: 'Chest-Supported Dumbbell Row',
      muscleGroup: 'Back & Lats',
      equipment: 'Dumbbells & Incline Bench',
      difficulty: 'Beginner',
      targetAngle: '90° Elbow Retraction',
      keyCues: 'Drive elbows back towards hips; pause for 1s isometric contraction.',
      commonMistakes: 'Using momentum/shrugging upper traps instead of latissimus dorsi.',
      desc: 'Isolates mid-back, rhomboids, and lats while eliminating lumbar axial loading.'
    },
    {
      id: 'ex-6',
      name: 'Standing Calf Raise',
      muscleGroup: 'Calves',
      equipment: 'Machine / Dumbbell',
      difficulty: 'Beginner',
      targetAngle: 'Full Plantarflexion Peak',
      keyCues: 'Pause 2s in deep stretch at bottom; push through balls of big toes.',
      commonMistakes: 'Bouncing at the bottom without controlled eccentric tempo.',
      desc: 'Gastrocnemius and soleus hypertrophy with ankle tendon stiffness training.'
    },
  ];

  const filtered = exercises.filter(ex => {
    const matchSearch = ex.name.toLowerCase().includes(search.toLowerCase()) || 
                        ex.muscleGroup.toLowerCase().includes(search.toLowerCase());
    const matchMuscle = muscleFilter === 'All' || ex.muscleGroup.includes(muscleFilter);
    return matchSearch && matchMuscle;
  });

  const handleLaunchExercise = (ex) => {
    setActiveSession(prev => ({
      ...prev,
      exerciseName: ex.name,
      currentReps: 0,
      currentSet: 1,
    }));
    setActiveTab('live-workout');
  };

  return (
    <div className="flex-col gap-6">
      {/* Search & Muscle Filters Bar */}
      <section className="card" style={{ padding: 20 }}>
        <div className="flex-row justify-between items-center" style={{ flexWrap: 'wrap', gap: 16 }}>
          <div className="input-wrapper" style={{ width: 340 }}>
            <Search className="input-icon" size={18} />
            <input
              type="text"
              className="input-field has-icon"
              placeholder="Search exercise name or muscle target..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="flex-row items-center gap-2" style={{ flexWrap: 'wrap' }}>
            <span className="font-semibold text-secondary" style={{ fontSize: '0.85rem' }}>Muscle Group:</span>
            {['All', 'Legs', 'Hamstrings', 'Chest', 'Back', 'Calves'].map(m => (
              <button
                key={m}
                className={`btn btn-sm ${muscleFilter === m ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setMuscleFilter(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Exercise Grid */}
      <div className="exercise-grid">
        {filtered.map(ex => (
          <div key={ex.id} className="exercise-card card-hoverable">
            <div className="flex-row justify-between items-center">
              <span className="badge badge-orange">{ex.muscleGroup}</span>
              <span className="badge badge-neutral">{ex.difficulty}</span>
            </div>

            <div className="flex-col gap-1">
              <h3 style={{ fontSize: '1.15rem' }}>{ex.name}</h3>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Equipment: {ex.equipment}
              </span>
            </div>

            <p style={{ fontSize: '0.875rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
              {ex.desc}
            </p>

            <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 12 }}>
              <div style={{ fontSize: '0.785rem', color: 'var(--primary-orange)', fontWeight: 600 }}>
                Target Angle: {ex.targetAngle}
              </div>
            </div>

            <div className="flex-row gap-2" style={{ marginTop: 'auto', paddingTop: 8 }}>
              <button 
                className="btn btn-secondary btn-sm" 
                style={{ flex: 1 }}
                onClick={() => setSelectedExerciseModal(ex)}
              >
                Form Cues
              </button>

              <button 
                className="btn btn-primary btn-sm"
                onClick={() => handleLaunchExercise(ex)}
              >
                <Play size={14} />
                <span>Track Live</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Form Cues & Biomechanics Detail Modal */}
      {selectedExerciseModal && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedExerciseModal(null)}
          title={selectedExerciseModal.name}
          subtitle={`${selectedExerciseModal.muscleGroup} • Equipment: ${selectedExerciseModal.equipment}`}
          wide={true}
        >
          <div className="flex-col gap-4">
            <div className="card-flat" style={{ background: 'var(--primary-orange-soft)', border: '1px solid var(--border-subtle)' }}>
              <div className="font-bold text-orange" style={{ fontSize: '1rem', marginBottom: 4 }}>
                Target Biomechanical Standard: {selectedExerciseModal.targetAngle}
              </div>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                {selectedExerciseModal.desc}
              </p>
            </div>

            <div className="card-flat" style={{ background: 'var(--success-soft)', border: '1px solid rgba(34, 197, 94, 0.2)' }}>
              <h4 style={{ color: '#15803D', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <CheckCircle2 size={18} /> Validated Execution Cues
              </h4>
              <p style={{ fontSize: '0.875rem', color: '#166534' }}>
                {selectedExerciseModal.keyCues}
              </p>
            </div>

            <div className="card-flat" style={{ background: 'var(--error-soft)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
              <h4 style={{ color: '#B91C1C', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <AlertTriangle size={18} /> Common Mechanical Errors Detected by AI
              </h4>
              <p style={{ fontSize: '0.875rem', color: '#991B1B' }}>
                {selectedExerciseModal.commonMistakes}
              </p>
            </div>

            <div className="flex-row justify-end" style={{ marginTop: 12 }}>
              <button 
                className="btn btn-primary btn-lg"
                onClick={() => {
                  handleLaunchExercise(selectedExerciseModal);
                  setSelectedExerciseModal(null);
                }}
              >
                <span>Launch Exercise Tracking</span>
                <Play size={18} />
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
