import React from 'react';
import MetricCard from '../components/common/MetricCard';
import { 
  Apple, 
  Droplets, 
  Plus, 
  AlertTriangle, 
  ShieldCheck, 
  Clock, 
  Flame, 
  CheckCircle2, 
  HelpCircle 
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function NutritionPage() {
  const { 
    nutrition, 
    addHydration, 
    toggleModal, 
    userProfile 
  } = useApp();

  const calorieRemaining = Math.max(0, nutrition.calorieTarget - nutrition.caloriesConsumed);

  return (
    <div className="flex-col gap-6">
      {/* 1. Daily Nutrition KPI Cards */}
      <section className="metrics-grid">
        <MetricCard
          icon={Flame}
          iconColor="orange"
          label="Total Calories"
          value={`${nutrition.caloriesConsumed} / ${nutrition.calorieTarget} kcal`}
          subtext={`${calorieRemaining} kcal remaining today`}
          progress={(nutrition.caloriesConsumed / nutrition.calorieTarget) * 100}
        />

        <MetricCard
          icon={Apple}
          iconColor="teal"
          label="Protein Target"
          value={`${nutrition.proteinConsumedG}g / ${nutrition.proteinTargetG}g`}
          subtext={`${Math.round((nutrition.proteinConsumedG / nutrition.proteinTargetG) * 100)}% of daily synthesis goal`}
          progress={(nutrition.proteinConsumedG / nutrition.proteinTargetG) * 100}
        />

        <MetricCard
          icon={Apple}
          iconColor="cyan"
          label="Carbohydrates"
          value={`${nutrition.carbsConsumedG}g / ${nutrition.carbsTargetG}g`}
          subtext="Glycogen replenishment"
          progress={(nutrition.carbsConsumedG / nutrition.carbsTargetG) * 100}
        />

        <MetricCard
          icon={Droplets}
          iconColor="teal"
          label="Hydration Level"
          value={`${nutrition.hydrationConsumedMl} ml`}
          subtext={`Target: ${nutrition.hydrationTargetMl} ml`}
          progress={(nutrition.hydrationConsumedMl / nutrition.hydrationTargetMl) * 100}
        />
      </section>

      {/* 2. Main Nutrition Layout: Meals Log & Dietary/Allergy Caution Card */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
        {/* Left: Logged Meals List */}
        <section className="card flex-col gap-4">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Apple size={20} className="text-orange" />
                <span>Today's Logged Meals</span>
              </h3>
              <p className="card-subtitle">Illustrative daily meal baseline — click "+ Log Meal" to add custom entries</p>
            </div>

            <button className="btn btn-primary btn-sm" onClick={() => toggleModal('logFood', true)}>
              <Plus size={16} />
              <span>Log Meal</span>
            </button>
          </div>

          <div className="flex-col gap-3">
            {nutrition.meals.map((meal) => (
              <div 
                key={meal.id} 
                className="card-flat flex-row justify-between items-center" 
                style={{ background: 'var(--surface-subtle)', padding: '16px 20px' }}
              >
                <div className="flex-col gap-1">
                  <div className="flex-row items-center gap-2">
                    <span className="badge badge-orange">{meal.type}</span>
                    <span className="text-muted" style={{ fontSize: '0.785rem' }}>{meal.time}</span>
                  </div>
                  <strong className="text-primary" style={{ fontSize: '1rem', marginTop: 2 }}>{meal.name}</strong>
                  {meal.allergens && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--warning-amber)' }}>
                      Allergen profile: {meal.allergens}
                    </span>
                  )}
                </div>

                <div className="flex-col items-end gap-1">
                  <strong className="text-primary" style={{ fontSize: '1.15rem' }}>{meal.calories} kcal</strong>
                  <div className="flex-row gap-2 text-muted" style={{ fontSize: '0.785rem' }}>
                    <span><strong>{meal.p}g</strong> P</span>
                    <span><strong>{meal.c}g</strong> C</span>
                    <span><strong>{meal.f}g</strong> F</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right: Allergen Safety Policy & Dietary Profile */}
        <div className="flex-col gap-5">
          {/* Allergen Verification Card */}
          <section className="card flex-col gap-3">
            <div className="card-header" style={{ marginBottom: 2 }}>
              <div>
                <h3 className="card-title" style={{ fontSize: '1.05rem' }}>
                  <AlertTriangle size={18} className="text-amber" />
                  <span>Allergen & Dietary Safety</span>
                </h3>
                <p className="card-subtitle">Transparent verification protocols</p>
              </div>
            </div>

            {/* Known Allergies */}
            <div className="card-flat" style={{ background: 'var(--surface-subtle)', padding: 14 }}>
              <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>User Reported Allergies:</span>
              <div className="flex-row gap-2" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                {userProfile.knownAllergies.map((all, i) => (
                  <span key={i} className="badge badge-red">{all}</span>
                ))}
              </div>
            </div>

            {/* Unverified / Unknown Allergies */}
            <div className="card-flat" style={{ background: '#FFFBEB', border: '1px solid #FDE68A', padding: 14 }}>
              <div className="flex-row items-center gap-2">
                <HelpCircle size={15} style={{ color: '#B45309' }} />
                <span className="font-semibold" style={{ fontSize: '0.85rem', color: '#B45309' }}>
                  Unconfirmed / Untested:
                </span>
              </div>
              <div className="flex-row gap-2" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                {userProfile.unconfirmedAllergies.map((all, i) => (
                  <span key={i} className="badge badge-amber">{all}</span>
                ))}
              </div>
            </div>

            {/* Safety Policy Notice */}
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <strong>Safety Principle:</strong> PERFORMX never classifies an ingredient or commercial meal as "allergy-safe" simply because an allergen was absent from the label. When unverified, allergen status remains strictly <em>Unknown</em>.
            </p>
          </section>

          {/* Hydration Tracker Card */}
          <section className="card flex-col gap-4">
            <div className="card-header" style={{ marginBottom: 2 }}>
              <div>
                <h3 className="card-title" style={{ fontSize: '1.05rem' }}>
                  <Droplets size={18} className="text-cyan" />
                  <span>Daily Hydration Goal</span>
                </h3>
                <p className="card-subtitle">Electrolyte & water balance</p>
              </div>
            </div>

            <div className="flex-row justify-between items-center">
              <span className="font-bold text-primary" style={{ fontSize: '1.5rem' }}>
                {nutrition.hydrationConsumedMl} <small style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ {nutrition.hydrationTargetMl} ml</small>
              </span>
              <span className="badge badge-cyan">
                {Math.round((nutrition.hydrationConsumedMl / nutrition.hydrationTargetMl) * 100)}%
              </span>
            </div>

            <div className="progress-bar-container lg">
              <div 
                className="progress-bar-fill progress-cyan" 
                style={{ width: `${(nutrition.hydrationConsumedMl / nutrition.hydrationTargetMl) * 100}%` }} 
              />
            </div>

            <div className="flex-row gap-2">
              <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => addHydration(250)}>
                <Plus size={14} /> +250 ml
              </button>
              <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => addHydration(500)}>
                <Plus size={14} /> +500 ml
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
