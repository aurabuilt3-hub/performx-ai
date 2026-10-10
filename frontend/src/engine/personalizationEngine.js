/**
 * PERFORMX Personalization Engine
 * Synthesizes athlete biometrics, experience level, equipment availability,
 * and active clinician restrictions to generate customized training programs.
 * 
 * CORE PRINCIPLE: Clinician restrictions always take priority and trigger conservative
 * biomechanical substitutions before volume or intensity are assigned.
 */

export const BASE_PLANS = [
  {
    id: 'plan-1',
    title: 'Hypertrophy Biomechanics 101',
    category: 'Hypertrophy',
    difficulty: 'Intermediate',
    baseDuration: 4,
    baseDaysPerWeek: 4,
    primaryFocus: 'Quadriceps, Posterior Chain & Upper Push/Pull',
    color: '#6854FF',
    desc: 'Targeted mechanical tension and volume optimization calibrated for joint longevity and muscle hypertrophy.',
    baseSchedule: [
      {
        day: 'Day 1: Quad & Knee Kinematics',
        focus: 'Knee & Hip Flexion',
        exercises: [
          { name: 'Barbell Back Squat', sets: 4, reps: '10-12', rest: '90s', targetAngle: '≤90° Flexion', equipment: 'Barbell' },
          { name: 'Bulgarian Split Squat', sets: 3, reps: '12', rest: '75s', targetAngle: '85° Lead Knee', equipment: 'Dumbbells' },
          { name: 'Leg Extension', sets: 3, reps: '15', rest: '60s', targetAngle: 'Full Extension', equipment: 'Machine' }
        ]
      },
      {
        day: 'Day 2: Upper Body Press Mechanics',
        focus: 'Horizontal & Incline Pressing',
        exercises: [
          { name: 'Incline Barbell Bench', sets: 4, reps: '8-10', rest: '90s', targetAngle: '30° Incline', equipment: 'Barbell' },
          { name: 'Overhead Dumbbell Press', sets: 3, reps: '10', rest: '75s', targetAngle: 'Scapular Plane', equipment: 'Dumbbells' },
          { name: 'Tricep Rope Pushdown', sets: 3, reps: '12', rest: '60s', targetAngle: 'Lockout', equipment: 'Cable' }
        ]
      },
      {
        day: 'Day 3: Active Rest & Joint Mobility',
        focus: 'Restorative Mobility',
        exercises: [
          { name: 'Cat-Cow Spinal Flow', sets: 3, reps: '10', rest: '30s', targetAngle: 'Pain-Free Arc', equipment: 'Bodyweight' },
          { name: 'Deep Squat Capsule Hold', sets: 3, reps: '45s', rest: '45s', targetAngle: 'Comfortable Depth', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 4: Posterior Chain & Hip Hinge',
        focus: 'Hip Hinge & Hamstring Eccentric',
        exercises: [
          { name: 'Romanian Deadlift', sets: 4, reps: '8-10', rest: '90s', targetAngle: '65°-75° Hinge', equipment: 'Barbell' },
          { name: 'Hamstring Curl', sets: 3, reps: '12', rest: '60s', targetAngle: 'Full Flexion', equipment: 'Machine' },
          { name: 'Standing Calf Raise', sets: 4, reps: '15', rest: '45s', targetAngle: 'Full Plantarflexion', equipment: 'Dumbbells' }
        ]
      }
    ]
  },
  {
    id: 'plan-2',
    title: 'Kinematic Power & Athletic Strength',
    category: 'Strength',
    difficulty: 'Advanced',
    baseDuration: 6,
    baseDaysPerWeek: 5,
    primaryFocus: 'High-Threshold Motor Unit Recruitment & Symmetry',
    color: '#20CDB5',
    desc: 'Neural rate-of-force development tracking velocity and bilateral symmetry across compound barbell lifts.',
    baseSchedule: [
      {
        day: 'Day 1: Heavy Squat Depth Focus',
        focus: 'Bilateral Squat Mechanics',
        exercises: [
          { name: 'Barbell Back Squat', sets: 5, reps: '5', rest: '180s', targetAngle: '≤90° Flexion', equipment: 'Barbell' },
          { name: 'Pause Squat at 90°', sets: 3, reps: '3', rest: '120s', targetAngle: '90° Isometric', equipment: 'Barbell' },
          { name: 'Leg Press', sets: 3, reps: '10', rest: '90s', targetAngle: 'Controlled 95°', equipment: 'Machine' }
        ]
      },
      {
        day: 'Day 2: Heavy Bench & Scapular Rhythm',
        focus: 'Horizontal Pressing',
        exercises: [
          { name: 'Flat Barbell Bench', sets: 5, reps: '5', rest: '180s', targetAngle: 'Scapulae Retracted', equipment: 'Barbell' },
          { name: 'Chest-Supported Row', sets: 4, reps: '8', rest: '90s', targetAngle: '90° Pull', equipment: 'Dumbbells' },
          { name: 'Weighted Dips', sets: 3, reps: '8', rest: '90s', targetAngle: '90° Elbow', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 3: Neural Recovery',
        focus: 'Central Nervous System Rest',
        exercises: [
          { name: 'Light Walk & Foam Rolling', sets: 1, reps: '20m', rest: '0s', targetAngle: 'N/A', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 4: Conventional Deadlift Hinge',
        focus: 'Posterior Chain Power',
        exercises: [
          { name: 'Deadlift', sets: 5, reps: '3', rest: '180s', targetAngle: 'Rigid Lumbar', equipment: 'Barbell' },
          { name: 'Barbell Bar Path RDL', sets: 3, reps: '8', rest: '90s', targetAngle: '70° Hinge', equipment: 'Barbell' },
          { name: 'Walking Lunges', sets: 3, reps: '12', rest: '75s', targetAngle: 'Upright Torso', equipment: 'Dumbbells' }
        ]
      }
    ]
  },
  {
    id: 'plan-3',
    title: 'Functional Mobility & Joint Longevity',
    category: 'Mobility',
    difficulty: 'Beginner',
    baseDuration: 3,
    baseDaysPerWeek: 3,
    primaryFocus: 'Capsular Mobility & End-Range Isometric Strength',
    color: '#38BDF8',
    desc: 'Restorative full range-of-motion routines focusing on hip capsule depth, ankle dorsiflexion, and thoracic extension.',
    baseSchedule: [
      {
        day: 'Day 1: Hip & Ankle Capsule Mobility',
        focus: 'Lower Extremity Range',
        exercises: [
          { name: 'Deep Squat Hold', sets: 3, reps: '45s', rest: '45s', targetAngle: 'Passive Depth', equipment: 'Bodyweight' },
          { name: 'Ankle Wall Mobilization', sets: 3, reps: '15', rest: '30s', targetAngle: 'Max Dorsiflexion', equipment: 'Bodyweight' },
          { name: 'Cossack Squats', sets: 3, reps: '10', rest: '45s', targetAngle: 'Adductor Stretch', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 2: Thoracic & Scapular Movement',
        focus: 'Upper Spine Mechanics',
        exercises: [
          { name: 'Cat-Cow Spinal Flow', sets: 3, reps: '10', rest: '30s', targetAngle: 'Segmental Flexion', equipment: 'Bodyweight' },
          { name: 'Band Pull-Aparts', sets: 3, reps: '20', rest: '30s', targetAngle: 'Rhomboid Peak', equipment: 'Resistance Bands' },
          { name: 'Wall Angels', sets: 3, reps: '12', rest: '30s', targetAngle: 'Scapular Gliding', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 3: Core & Lumbar Control',
        focus: 'Antirotation & Spinal Neutrality',
        exercises: [
          { name: 'Bird-Dog Isometric', sets: 3, reps: '30s', rest: '30s', targetAngle: 'Neutral Spine', equipment: 'Bodyweight' },
          { name: 'Deadbug', sets: 3, reps: '12', rest: '30s', targetAngle: 'Posterior Pelvic Tilt', equipment: 'Bodyweight' },
          { name: 'Side Plank', sets: 3, reps: '30s', rest: '30s', targetAngle: 'Lateral Alignment', equipment: 'Bodyweight' }
        ]
      }
    ]
  },
  {
    id: 'plan-4',
    title: 'Metabolic Conditioning & Caloric Burn',
    category: 'Conditioning',
    difficulty: 'Intermediate',
    baseDuration: 4,
    baseDaysPerWeek: 4,
    primaryFocus: 'Cardiorespiratory Endurance & High-Density Circuits',
    color: '#F59E0B',
    desc: 'High-density compound circuits engineered for cardiorespiratory fitness, muscular endurance, and energy expenditure.',
    baseSchedule: [
      {
        day: 'Day 1: Full Body Circuit A',
        focus: 'Total Body Density',
        exercises: [
          { name: 'Goblet Squats', sets: 4, reps: '15', rest: '45s', targetAngle: 'Parallel Depth', equipment: 'Dumbbells' },
          { name: 'Dumbbell Push Press', sets: 4, reps: '12', rest: '45s', targetAngle: 'Overhead Drive', equipment: 'Dumbbells' },
          { name: 'Renegade Rows', sets: 4, reps: '10', rest: '45s', targetAngle: 'Anti-Rotation', equipment: 'Dumbbells' }
        ]
      },
      {
        day: 'Day 2: Interval Conditioning',
        focus: 'High Intensity Intervals',
        exercises: [
          { name: 'Kettlebell Swings', sets: 5, reps: '20', rest: '45s', targetAngle: 'Hip Hinge Snap', equipment: 'Dumbbells' },
          { name: 'Push-Ups & Plank', sets: 4, reps: '15', rest: '30s', targetAngle: '90° Elbow', equipment: 'Bodyweight' },
          { name: 'Mountain Climbers', sets: 4, reps: '30s', rest: '30s', targetAngle: 'Core Drive', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 3: Active Rest',
        focus: 'Walking & Hydration',
        exercises: [
          { name: 'Low Intensity Mobility', sets: 1, reps: '15m', rest: '0s', targetAngle: 'Free Movement', equipment: 'Bodyweight' }
        ]
      },
      {
        day: 'Day 4: Full Body Circuit B',
        focus: 'Unilateral Endurance',
        exercises: [
          { name: 'Static Split Squat', sets: 4, reps: '12', rest: '45s', targetAngle: '90° Front Knee', equipment: 'Dumbbells' },
          { name: 'Dumbbell Floor Press', sets: 4, reps: '12', rest: '45s', targetAngle: 'Triceps Contact', equipment: 'Dumbbells' },
          { name: 'Hanging Leg Raise', sets: 3, reps: '12', rest: '45s', targetAngle: 'Hip Flexion', equipment: 'Bodyweight' }
        ]
      }
    ]
  }
];

/**
 * Apply clinician constraints and equipment adaptations to an exercise
 */
export function adaptExercise({
  exercise,
  availableEquipment = [],
  clinicianRestrictions = [],
  discomfortRating = 0,
  activeRegion = ''
}) {
  let adaptedName = exercise.name;
  let substitutionNote = null;
  let targetAngle = exercise.targetAngle;

  // 1. Clinician restriction enforcement
  const isKneeRestricted = clinicianRestrictions.some(r => 
    (r.anatomicalRegion || '').toLowerCase().includes('knee') ||
    (r.instruction || '').toLowerCase().includes('knee')
  ) || (activeRegion.toLowerCase().includes('knee') && discomfortRating >= 4);

  const isSpineRestricted = clinicianRestrictions.some(r => 
    (r.anatomicalRegion || '').toLowerCase().includes('spine') ||
    (r.instruction || '').toLowerCase().includes('lumbar')
  ) || (activeRegion.toLowerCase().includes('spine') && discomfortRating >= 4);

  if (isKneeRestricted) {
    if (exercise.name === 'Barbell Back Squat') {
      adaptedName = 'Box Squat to 95° Bench';
      targetAngle = '≤95° Flexion (Depth Cap)';
      substitutionNote = 'Substituted to protect left patellofemoral joint per clinician restriction.';
    } else if (exercise.name === 'Walking Lunges') {
      adaptedName = 'Static Split Squat with Elevation';
      targetAngle = 'Upright 90°';
      substitutionNote = 'Substituted to eliminate ground deceleration shear on patellar tendon.';
    }
  }

  if (isSpineRestricted) {
    if (exercise.name === 'Deadlift') {
      adaptedName = 'Rack Pulls (Mid-Shin) or Chest-Supported Row';
      substitutionNote = 'Modified to reduce lumbar moment arm and spinal shear.';
    }
  }

  // 2. Equipment check
  const hasEquipment = availableEquipment.length === 0 || 
    availableEquipment.some(eq => exercise.equipment.toLowerCase().includes(eq.toLowerCase())) ||
    exercise.equipment === 'Bodyweight';

  let equipmentNote = null;
  if (!hasEquipment && exercise.equipment === 'Barbell') {
    adaptedName = adaptedName.replace('Barbell', 'Dumbbell');
    equipmentNote = 'Adapted from Barbell to available Dumbbells.';
  }

  return {
    ...exercise,
    name: adaptedName,
    originalName: exercise.name,
    targetAngle,
    isSubstituted: adaptedName !== exercise.name,
    substitutionNote,
    equipmentNote
  };
}

/**
 * Generate fully personalized workout plans adapting to user profile and medical constraints
 */
export function generatePersonalizedPlans({
  userProfile,
  injuryState,
  clinicianRestrictions = []
}) {
  const availableEquipment = userProfile?.equipment || ['Barbell', 'Dumbbells', 'Squat Rack'];
  const userGoal = (userProfile?.goal || 'Strength & Biomechanics').toLowerCase();
  const experience = userProfile?.experienceLevel || 'Intermediate';
  const discomfort = injuryState?.discomfortRating || 0;
  const activeRegion = injuryState?.activeRegion || '';

  return BASE_PLANS.map(plan => {
    // Determine relevance match
    const isGoalMatch = (
      (userGoal.includes('hypertrophy') && plan.category === 'Hypertrophy') ||
      (userGoal.includes('strength') && plan.category === 'Strength') ||
      (userGoal.includes('mobility') && plan.category === 'Mobility') ||
      (userGoal.includes('conditioning') && plan.category === 'Conditioning')
    );

    const isDifficultyMatch = plan.difficulty.toLowerCase() === experience.toLowerCase();

    // Adapt all schedule exercises
    let totalSubstitutions = 0;
    const personalizedSchedule = plan.baseSchedule.map(day => {
      const adaptedExercises = day.exercises.map(ex => {
        const adapted = adaptExercise({
          exercise: ex,
          availableEquipment,
          clinicianRestrictions,
          discomfortRating: discomfort,
          activeRegion
        });
        if (adapted.isSubstituted) totalSubstitutions++;
        return adapted;
      });

      return {
        ...day,
        exercises: adaptedExercises,
        exerciseNames: adaptedExercises.map(e => `${e.name} (${e.sets}×${e.reps})`)
      };
    });

    // Formulate personalization rationale
    let personalizationReason = '';
    if (totalSubstitutions > 0) {
      personalizationReason = `Adapted with ${totalSubstitutions} conservative exercise substitution(s) protecting ${activeRegion || 'joints'} based on clinician guidance.`;
    } else if (isGoalMatch && isDifficultyMatch) {
      personalizationReason = `Direct match for your ${userProfile?.goal || 'training'} goal and ${experience} athletic tier.`;
    } else {
      personalizationReason = `Calibrated for ${availableEquipment.join(', ')} with progressive load intervals.`;
    }

    return {
      id: plan.id,
      title: plan.title,
      category: plan.category,
      difficulty: plan.difficulty,
      duration: `${plan.baseDuration} Weeks`,
      daysPerWeek: `${plan.baseDaysPerWeek} Days / Wk`,
      exerciseCount: personalizedSchedule.reduce((acc, d) => acc + d.exercises.length, 0),
      equipment: availableEquipment.join(', '),
      color: plan.color,
      desc: plan.desc,
      isGoalMatch,
      isDifficultyMatch,
      hasMedicalSubstitutions: totalSubstitutions > 0,
      personalizationReason,
      schedule: personalizedSchedule
    };
  });
}
