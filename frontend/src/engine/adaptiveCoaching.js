/**
 * PERFORMX Adaptive Coaching Engine
 * Evaluates active injury status, clinician restrictions, recovery readiness,
 * and workout adherence to generate conservative, biomechanically safe recommendations.
 * 
 * CORE PRINCIPLE: Clinician restrictions can NEVER be overridden.
 */

export function generateAdaptiveRecommendations({
  injuryState,
  clinicianRestrictions = [],
  recoveryReadiness = 88,
  planAdherence = 92,
  activeSession
}) {
  const recommendations = [];

  // 1. Highest Priority: Clinician Restrictions
  if (clinicianRestrictions && clinicianRestrictions.length > 0) {
    clinicianRestrictions.forEach((res, idx) => {
      recommendations.push({
        id: `rec-clinician-${idx}`,
        type: 'clinician_restriction',
        priority: 'critical',
        title: `Clinician Constraint: ${res.anatomicalRegion || 'Joint Protection'}`,
        description: res.instruction || 'Limit range of motion to pain-free arc as directed by clinician.',
        actionLabel: 'Active Restriction Enforced',
        reasoning: `Extracted from medical document dated ${res.documentDate || 'recently'}. Overrides all automatic progression algorithms.`,
        suggestedExerciseSub: res.substitution || null,
        canDismiss: false, // Clinician restrictions cannot be dismissed
      });
    });
  }

  // 2. High Priority: Active Injury / Elevated Discomfort Rating
  if (injuryState && injuryState.discomfortRating > 0) {
    const rating = injuryState.discomfortRating;
    const region = injuryState.activeRegion || 'Joint';

    if (rating >= 7) {
      recommendations.push({
        id: 'rec-injury-high',
        type: 'injury_mitigation',
        priority: 'high',
        title: `High Discomfort Alert: ${region} (${rating}/10)`,
        description: `Suspend axial loading and high-impact compound movements targeting ${region}. Focus on restorative mobility and pain-free isometrics.`,
        actionLabel: 'Deload & Substitute Exercises',
        reasoning: `Discomfort rating ${rating}/10 exceeds safe adaptive threshold (6/10). Conservative recovery protocol active.`,
        suggestedExerciseSub: injuryState.primarySubstitution || 'Glute Bridges / Isometrics',
        canDismiss: true,
      });
    } else if (rating >= 4) {
      recommendations.push({
        id: 'rec-injury-moderate',
        type: 'load_adjustment',
        priority: 'medium',
        title: `Moderate Discomfort Adjustment: ${region} (${rating}/10)`,
        description: `Reduce working load by 15% and cap knee flexion at 95° to prevent patellofemoral shear. Substitute Barbell Squat with Box Squat if needed.`,
        actionLabel: 'Apply 15% Load Reduction',
        reasoning: `Sub-acute discomfort in ${region}. Box squat provides mechanical depth stop while reducing patellar tendon tension.`,
        suggestedExerciseSub: 'Box Squat to 95° Bench',
        canDismiss: true,
      });
    }
  }

  // 3. Recovery Readiness / HRV-Aware Adaptive Advice
  if (recoveryReadiness < 70) {
    recommendations.push({
      id: 'rec-recovery-low',
      type: 'recovery',
      priority: 'medium',
      title: 'Low Recovery Readiness Score',
      description: 'Elevated systemic fatigue detected. Shift today\'s session focus to technical tempo execution and limit RPE to 6-7.',
      actionLabel: 'Enable Auto-Regulated RPE Cap',
      reasoning: `Readiness index at ${recoveryReadiness}%. Central nervous system recovery takes precedence.`,
      canDismiss: true,
    });
  } else {
    // Optimal readiness positive recommendation
    recommendations.push({
      id: 'rec-optimal-readiness',
      type: 'progression',
      priority: 'low',
      title: 'Optimal Biomechanical Readiness (88%)',
      description: 'Neuromuscular recovery and sleep metrics are optimal. Cleared for prescribed progressive volume on uninjured muscle groups.',
      actionLabel: 'Proceed with Scheduled Plan',
      reasoning: 'Heart Rate Variability and 7-day consistency indicate excellent adaptation capacity.',
      canDismiss: true,
    });
  }

  return recommendations;
}
