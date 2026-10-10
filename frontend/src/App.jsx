import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import MobileNav from './components/layout/MobileNav';
import MobileDrawer from './components/layout/MobileDrawer';

// Pages
import OverviewPage from './pages/OverviewPage';
import LiveWorkoutPage from './pages/LiveWorkoutPage';
import KinematicsPage from './pages/KinematicsPage';
import WorkoutPlansPage from './pages/WorkoutPlansPage';
import ExerciseLibraryPage from './pages/ExerciseLibraryPage';
import NutritionPage from './pages/NutritionPage';
import ProgressPage from './pages/ProgressPage';
import ProfilePage from './pages/ProfilePage';
import MedicalDocsPage from './pages/MedicalDocsPage';
import InjuryAwareTrainingPage from './pages/InjuryAwareTrainingPage';
import SettingsPage from './pages/SettingsPage';
import LandingPage from './pages/LandingPage';
import AICoachPage from './pages/AICoachPage';

// Modals
import OnboardingModal from './components/modals/OnboardingModal';
import AuthModal from './components/modals/AuthModal';
import WorkoutCompletionModal from './components/modals/WorkoutCompletionModal';
import LogFoodModal from './components/modals/LogFoodModal';
import EditProfileModal from './components/modals/EditProfileModal';

function AppContent() {
  const { activeTab, modalState, toggleModal } = useApp();

  // Public Landing Page view
  if (activeTab === 'landing') {
    return (
      <div className="landing-view-root">
        <LandingPage />
        <AuthModal 
          isOpen={modalState.auth} 
          onClose={() => toggleModal('auth', false)} 
        />
      </div>
    );
  }

  const renderActivePage = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewPage />;
      case 'ai-coach':
        return <AICoachPage />;
      case 'live-workout':
        return <LiveWorkoutPage />;
      case 'kinematics':
        return <KinematicsPage />;
      case 'plans':
        return <WorkoutPlansPage />;
      case 'library':
        return <ExerciseLibraryPage />;
      case 'medical-docs':
        return <MedicalDocsPage />;
      case 'injury-training':
        return <InjuryAwareTrainingPage />;
      case 'nutrition':
        return <NutritionPage />;
      case 'progress':
        return <ProgressPage />;
      case 'profile':
        return <ProfilePage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <div className="app-layout">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Main Wrapper */}
      <div className="main-wrapper">
        <Header />

        <main className="page-container" role="main">
          {renderActivePage()}
        </main>

        {/* Mobile Bottom Navigation */}
        <MobileNav />

        {/* Mobile Drawer */}
        <MobileDrawer />
      </div>

      {/* Modals */}
      <OnboardingModal 
        isOpen={modalState.onboarding} 
        onClose={() => toggleModal('onboarding', false)} 
      />

      <AuthModal 
        isOpen={modalState.auth} 
        onClose={() => toggleModal('auth', false)} 
      />

      <WorkoutCompletionModal 
        isOpen={modalState.completion} 
        onClose={() => toggleModal('completion', false)} 
      />

      <LogFoodModal 
        isOpen={modalState.logFood} 
        onClose={() => toggleModal('logFood', false)} 
      />

      <EditProfileModal 
        isOpen={modalState.editProfile} 
        onClose={() => toggleModal('editProfile', false)} 
      />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
