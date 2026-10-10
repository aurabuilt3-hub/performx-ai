import React, { useState } from 'react';
import Modal from '../common/Modal';
import { Search, Plus, AlertCircle, Apple, Check } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function LogFoodModal({ isOpen, onClose }) {
  const { addMeal } = useApp();
  const [search, setSearch] = useState('');
  const [selectedMealType, setSelectedMealType] = useState('Lunch');

  const foodDatabase = [
    { name: 'Grilled Chicken Breast (200g)', calories: 330, p: 62, c: 0, f: 7, allergens: 'None declared (unverified commercial source)' },
    { name: 'Brown Rice & Steamed Broccoli (150g)', calories: 210, p: 5, c: 45, f: 2, allergens: 'Unknown allergen profile' },
    { name: 'Whey Protein Shake with Almond Milk', calories: 190, p: 28, c: 6, f: 3, allergens: 'Contains Dairy (Milk), Tree Nuts' },
    { name: 'Whole Rolled Oats with Banana & Honey', calories: 360, p: 11, c: 72, f: 5, allergens: 'Gluten-sensitive risk (Processed in facility with wheat)' },
    { name: 'Wild Sockeye Salmon Fillet (180g)', calories: 380, p: 40, c: 0, f: 22, allergens: 'Contains Fish; Shellfish risk: Unknown' },
    { name: 'Greek Salad with Feta & Olive Oil', calories: 290, p: 9, c: 12, f: 24, allergens: 'Contains Dairy (Feta)' },
  ];

  const filteredFoods = foodDatabase.filter(f => 
    f.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleAdd = (food) => {
    addMeal({
      id: 'meal_' + Date.now(),
      name: food.name,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      calories: food.calories,
      p: food.p,
      c: food.c,
      f: food.f,
      type: selectedMealType,
      allergens: food.allergens,
    });
    onClose();
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title="Log Meal or Nutrition" 
      subtitle="Search verified nutritional data. Allergen status is marked explicitly."
      wide={true}
    >
      <div className="flex-col gap-4">
        {/* Meal Type Selector */}
        <div className="tabs-container" style={{ width: '100%' }}>
          {['Breakfast', 'Lunch', 'Pre-Workout', 'Dinner', 'Snack'].map(type => (
            <button
              key={type}
              type="button"
              className={`tab-btn ${selectedMealType === type ? 'active' : ''}`}
              style={{ flex: 1, textAlign: 'center' }}
              onClick={() => setSelectedMealType(type)}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Search Field */}
        <div className="input-wrapper">
          <Search className="input-icon" size={18} />
          <input
            type="text"
            className="input-field has-icon"
            placeholder="Search whole foods, protein shakes, or meals..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Allergen Policy Notice */}
        <div className="feedback-box feedback-neutral" style={{ marginTop: 0 }}>
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '0.8rem' }}>
            <strong>Allergen Safety Standard:</strong> Unverified ingredients are marked as <em>Unknown</em>. Never assume an item is allergy-safe simply because an allergen was not listed.
          </span>
        </div>

        {/* Food List */}
        <div className="flex-col gap-3" style={{ maxHeight: 320, overflowY: 'auto' }}>
          {filteredFoods.map((food, idx) => (
            <div 
              key={idx} 
              className="card-flat flex-row justify-between items-center" 
              style={{ padding: '14px 18px', background: 'var(--surface-subtle)' }}
            >
              <div className="flex-col gap-1">
                <span className="font-semibold text-primary">{food.name}</span>
                <div className="flex-row gap-3 text-muted" style={{ fontSize: '0.8rem' }}>
                  <span><strong>{food.calories}</strong> kcal</span>
                  <span><strong>{food.p}g</strong> Protein</span>
                  <span><strong>{food.c}g</strong> Carbs</span>
                  <span><strong>{food.f}g</strong> Fat</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--warning-amber)', marginTop: 2 }}>
                  Allergens: {food.allergens}
                </div>
              </div>

              <button className="btn btn-primary btn-sm" onClick={() => handleAdd(food)}>
                <Plus size={15} />
                <span>Add</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}
