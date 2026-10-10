-- ====================================================================
-- PERFORMX Supabase Database Migration
-- Phase 23: User Profiles, Workout Session Persistence & Row-Level Security
-- Migration Version: 20261010000000
-- ====================================================================

-- 1. Create profiles table
create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    created_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);

comment on table public.profiles is 'User profile records linked to auth.users with zero sensitive biometric data.';

-- 2. Create workout_sessions table
create table if not exists public.workout_sessions (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    exercise_type text not null default 'squat',
    start_time timestamptz not null,
    end_time timestamptz not null,
    duration_seconds double precision not null check (duration_seconds >= 0.0),
    total_frames_processed integer not null check (total_frames_processed >= 0),
    total_reps integer not null check (total_reps >= 0),
    valid_reps integer not null check (valid_reps >= 0),
    mean_symmetry double precision not null check (mean_symmetry >= 0.0 and mean_symmetry <= 1.0),
    mean_rep_duration double precision not null check (mean_rep_duration >= 0.0),
    summary_metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc'::text, now())
);

comment on table public.workout_sessions is 'Completed workout summaries containing strictly aggregated kinematic scalars. Zero frames, images, or raw landmarks.';

-- 3. Indexes for fast user queries and time-series ordering
create index if not exists idx_workout_sessions_user_id on public.workout_sessions(user_id);
create index if not exists idx_workout_sessions_created_at on public.workout_sessions(created_at desc);
create index if not exists idx_workout_sessions_user_created on public.workout_sessions(user_id, created_at desc);

-- 4. Enable Row Level Security (RLS)
alter table public.profiles enable row level security;
alter table public.workout_sessions enable row level security;

-- 5. Profiles RLS Policies (strictly user-scoped)
create policy "Users can view their own profile"
    on public.profiles for select
    using (auth.uid() = id);

create policy "Users can insert their own profile"
    on public.profiles for insert
    with check (auth.uid() = id);

create policy "Users can update their own profile"
    on public.profiles for update
    using (auth.uid() = id)
    with check (auth.uid() = id);

create policy "Users can delete their own profile"
    on public.profiles for delete
    using (auth.uid() = id);

-- 6. Workout Sessions RLS Policies (strictly user-scoped)
create policy "Users can view their own workout sessions"
    on public.workout_sessions for select
    using (auth.uid() = user_id);

create policy "Users can insert their own workout sessions"
    on public.workout_sessions for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own workout sessions"
    on public.workout_sessions for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users can delete their own workout sessions"
    on public.workout_sessions for delete
    using (auth.uid() = user_id);

-- 7. Automatic profile provisioning trigger upon auth.users sign-up
create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.profiles (id, display_name, created_at, updated_at)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
        timezone('utc'::text, now()),
        timezone('utc'::text, now())
    )
    on conflict (id) do nothing;
    return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();
