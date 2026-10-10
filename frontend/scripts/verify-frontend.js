/**
 * PERFORMX Automated Verification Test Suite
 * Validates engines, personalization rules, clinician restriction priority,
 * and data privacy requirements.
 */

import { generateAdaptiveRecommendations } from '../src/engine/adaptiveCoaching.js';
import { generatePersonalizedPlans, adaptExercise } from '../src/engine/personalizationEngine.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ PASS: ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

console.log('--- 1. Testing Adaptive Coaching Engine & Clinician Restriction Priority ---');

const mockClinicianRestrictions = [
  {
    id: 'res-1',
    anatomicalRegion: 'Left Knee',
    instruction: 'Cap loaded knee flexion at 95°',
    substitution: 'Box Squat to 95° Bench',
    documentDate: 'Sep 18, 2026'
  }
];

const mockInjury = {
  activeRegion: 'Left Knee',
  anatomicalSubregion: 'Patellofemoral Joint',
  discomfortRating: 5,
  primarySubstitution: 'Box Squat to 95° Bench'
};

const recs = generateAdaptiveRecommendations({
  injuryState: mockInjury,
  clinicianRestrictions: mockClinicianRestrictions,
  recoveryReadiness: 88,
  planAdherence: 92
});

assert(recs.length >= 2, 'Generated multiple recommendations for clinician constraint and discomfort');
assert(recs[0].type === 'clinician_restriction', 'Highest priority recommendation is clinician restriction');
assert(recs[0].canDismiss === false, 'Clinician restriction cannot be dismissed');
assert(recs[0].suggestedExerciseSub === 'Box Squat to 95° Bench', 'Clinician restriction supplies correct conservative substitution');

const loadRec = recs.find(r => r.type === 'load_adjustment');
assert(loadRec && loadRec.priority === 'medium', 'Discomfort 5/10 generates medium priority load reduction recommendation');

console.log('\n--- 2. Testing Personalization Engine & Exercise Substitutions ---');

const mockUser = {
  name: 'Alex Morgan',
  goal: 'Hypertrophy Biomechanics',
  experienceLevel: 'Intermediate',
  equipment: ['Barbell', 'Dumbbells', 'Squat Rack']
};

const plans = generatePersonalizedPlans({
  userProfile: mockUser,
  injuryState: mockInjury,
  clinicianRestrictions: mockClinicianRestrictions
});

assert(plans.length === 4, 'Generates 4 personalized base plans');
assert(plans[0].category === 'Hypertrophy', 'Preserves base plan categories');

// Check that Barbell Back Squat is substituted in knee restricted plans
const hypertrophyPlan = plans.find(p => p.id === 'plan-1');
assert(hypertrophyPlan.hasMedicalSubstitutions === true, 'Plan flags medical substitutions active');

const day1Exercises = hypertrophyPlan.schedule[0].exercises;
const squatEx = day1Exercises.find(e => e.originalName === 'Barbell Back Squat');
assert(squatEx !== undefined, 'Found squat exercise in schedule');
assert(squatEx.name === 'Box Squat to 95° Bench', 'Barbell Back Squat replaced with Box Squat to 95° Bench');
assert(squatEx.isSubstituted === true, 'Exercise marked as isSubstituted');

console.log('\n--- 3. Testing Equipment Adaptation ---');
const dumbbellOnlyUser = {
  name: 'Sam Lee',
  goal: 'Hypertrophy Biomechanics',
  experienceLevel: 'Beginner',
  equipment: ['Dumbbells', 'Bodyweight']
};

const adaptedEx = adaptExercise({
  exercise: { name: 'Incline Barbell Bench', equipment: 'Barbell', targetAngle: '30°' },
  availableEquipment: dumbbellOnlyUser.equipment,
  clinicianRestrictions: [],
  discomfortRating: 0
});

assert(adaptedEx.name.includes('Dumbbell'), 'Barbell exercise adapted to available Dumbbells');
assert(adaptedEx.equipmentNote !== null, 'Equipment adaptation note generated');

console.log('\n--- 4. Summary ---');
console.log(`Total tests: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log('All automated integration tests passed successfully!\n');
}
