-- ====================================================================
-- PERFORMX Comprehensive Supabase Database Migration
-- Phase 27: Master Backend Data Model & Row-Level Security
-- Version: 20261011000000
-- ====================================================================

-- 1. Extend profiles table with fitness and app preferences
alter table public.profiles
    add column if not exists units text not null default 'metric' check (units in ('metric', 'imperial')),
    add column if not exists fitness_experience text not null default 'intermediate' check (fitness_experience in ('beginner', 'intermediate', 'advanced', 'elite')),
    add column if not exists primary_goal text not null default 'general_fitness',
    add column if not exists secondary_goal text,
    add column if not exists available_equipment jsonb not null default '["bodyweight"]'::jsonb,
    add column if not exists preferred_training_days jsonb not null default '[1,3,5]'::jsonb,
    add column if not exists preferred_session_duration integer not null default 45 check (preferred_session_duration > 0 and preferred_session_duration <= 180),
    add column if not exists dietary_preferences jsonb not null default '[]'::jsonb;

-- 2. Health Profiles (Sensitive Health & Biometrics Data)
create table if not exists public.health_profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    height_cm double precision check (height_cm is null or (height_cm >= 50.0 and height_cm <= 300.0)),
    weight_kg double precision check (weight_kg is null or (weight_kg >= 20.0 and weight_kg <= 500.0)),
    body_fat_percentage double precision check (body_fat_percentage is null or (body_fat_percentage >= 2.0 and body_fat_percentage <= 70.0)),
    resting_heart_rate integer check (resting_heart_rate is null or (resting_heart_rate >= 30 and resting_heart_rate <= 220)),
    reported_injuries jsonb not null default '[]'::jsonb,
    reported_symptoms jsonb not null default '[]'::jsonb,
    clinician_restrictions jsonb not null default '[]'::jsonb,
    clinician_approved_plan text,
    allergies jsonb not null default '[]'::jsonb,
    dietary_restrictions jsonb not null default '[]'::jsonb,
    medications jsonb not null default '[]'::jsonb,
    data_provenance text not null default 'USER_REPORTED',
    last_assessed_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);

comment on table public.health_profiles is 'User-reported and clinician-provided health conditions. Not a clinical diagnostic record.';

-- 3. Workout Plans & Prescription
create table if not exists public.workout_plans (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null,
    description text default '',
    is_active boolean not null default true,
    version integer not null default 1,
    exercises jsonb not null default '[]'::jsonb,
    equipment_constraints jsonb not null default '[]'::jsonb,
    target_experience text not null default 'intermediate',
    created_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists idx_workout_plans_user_active on public.workout_plans(user_id, is_active);

-- 4. Adaptive Coaching Recommendations
create table if not exists public.adaptive_recommendations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    recommendation_type text not null,
    rationale text not null,
    status text not null default 'proposed' check (status in ('proposed', 'accepted', 'edited', 'dismissed', 'applied')),
    source_session_id text,
    applied_changes jsonb default '{}'::jsonb,
    decision_timestamp timestamptz,
    created_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists idx_adaptive_rec_user_status on public.adaptive_recommendations(user_id, status);

-- 5. Injury Recovery & Check-ins
create table if not exists public.recovery_checkins (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    affected_area text not null,
    discomfort_score integer not null check (discomfort_score >= 0 and discomfort_score <= 10),
    symptoms text default '',
    exercise_adherence_score double precision default 1.0 check (exercise_adherence_score >= 0.0 and exercise_adherence_score <= 1.0),
    notes text default '',
    recorded_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists idx_recovery_checkins_user on public.recovery_checkins(user_id, recorded_at desc);

-- 6. Nutrition & Hydration Logs
create table if not exists public.nutrition_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    log_date date not null default current_date,
    calories_consumed integer not null default 0 check (calories_consumed >= 0 and calories_consumed <= 20000),
    protein_g double precision not null default 0.0 check (protein_g >= 0.0),
    carbs_g double precision not null default 0.0 check (carbs_g >= 0.0),
    fat_g double precision not null default 0.0 check (fat_g >= 0.0),
    water_ml integer not null default 0 check (water_ml >= 0 and water_ml <= 20000),
    meals jsonb not null default '[]'::jsonb,
    allergen_verification_status text not null default 'UNKNOWN' check (allergen_verification_status in ('VERIFIED_PRESENT', 'VERIFIED_ABSENT', 'UNKNOWN')),
    updated_at timestamptz not null default timezone('utc'::text, now()),
    unique(user_id, log_date)
);

create index if not exists idx_nutrition_logs_user_date on public.nutrition_logs(user_id, log_date desc);

-- 7. Medical Documents Metadata (Private Storage References)
create table if not exists public.medical_documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    storage_path text not null unique,
    file_name text not null,
    file_size_bytes integer not null check (file_size_bytes > 0 and file_size_bytes <= 15728640), -- 15MB limit
    mime_type text not null check (mime_type in ('application/pdf', 'image/png', 'image/jpeg')),
    document_category text not null default 'general',
    description text default '',
    status text not null default 'confirmed' check (status in ('pending_upload', 'confirmed', 'deleted')),
    created_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists idx_medical_docs_user on public.medical_documents(user_id, created_at desc);

-- 8. Privacy & Consent Preferences
create table if not exists public.privacy_consents (
    user_id uuid primary key references auth.users(id) on delete cascade,
    camera_processing_consent boolean not null default false,
    document_processing_consent boolean not null default false,
    data_analytics_consent boolean not null default false,
    updated_at timestamptz not null default timezone('utc'::text, now())
);

-- ====================================================================
-- Row-Level Security (RLS) Configuration
-- ====================================================================
alter table public.health_profiles enable row level security;
alter table public.workout_plans enable row level security;
alter table public.adaptive_recommendations enable row level security;
alter table public.recovery_checkins enable row level security;
alter table public.nutrition_logs enable row level security;
alter table public.medical_documents enable row level security;
alter table public.privacy_consents enable row level security;

-- Health Profiles RLS
create policy "Users can manage their health profile" on public.health_profiles
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Workout Plans RLS
create policy "Users can manage their workout plans" on public.workout_plans
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Adaptive Recommendations RLS
create policy "Users can manage their recommendations" on public.adaptive_recommendations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Recovery Checkins RLS
create policy "Users can manage their recovery checkins" on public.recovery_checkins
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Nutrition Logs RLS
create policy "Users can manage their nutrition logs" on public.nutrition_logs
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Medical Documents RLS
create policy "Users can manage their medical documents" on public.medical_documents
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Privacy Consents RLS
create policy "Users can manage their privacy consents" on public.privacy_consents
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
