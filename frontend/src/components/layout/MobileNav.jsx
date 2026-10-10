import React from 'react';
import { 
  LayoutDashboard, 
  Activity, 
  Box, 
  CalendarRange, 
  Apple, 
  User 
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function MobileNav() {
  const { activeTab, setActiveTab } = useApp();

  const primaryItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'live-workout', label: 'Workout', icon: Activity },
    { id: 'kinematics', label: '3D', icon: Box },
    { id: 'plans', label: 'Plans', icon: CalendarRange },
    { id: 'nutrition', label: 'Nutrition', icon: Apple },
    { id: 'profile', label: 'Profile', icon: User },
  ];

  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile Navigation">
      {primaryItems.map((item) => {
        const IconComponent = item.icon;
        const isActive = activeTab === item.id;
        return (
          <div
            key={item.id}
            className={`mobile-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
            role="button"
            tabIndex={0}
          >
            <IconComponent size={20} />
            <span>{item.label}</span>
          </div>
        );
      })}
    </nav>
  );
}
