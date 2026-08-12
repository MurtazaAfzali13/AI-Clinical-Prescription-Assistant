-- Doctor Copilot System — Supabase schema
-- Run in the Supabase SQL editor, or via `supabase db push`.

create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------
-- doctors: one row per authenticated doctor (mirrors auth.users)
-- ---------------------------------------------------------------------
create table if not exists doctors (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
  email text unique,
  license_no text,
  specialty text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- patients
-- ---------------------------------------------------------------------
create table if not exists patients (
  id uuid primary key default uuid_generate_v4(),
  record_no text unique not null,
  national_id text unique,
  full_name text not null,
  father_name text,
  age int,
  date_of_birth date,
  gender text,
  blood_type text,
  phone text,
  allergies text[] not null default '{}',
  chronic_conditions text[] not null default '{}',
  -- Clinical context used by the CDSS Lab/Context and Dose agents:
  weight_kg numeric,
  egfr numeric,               -- estimated glomerular filtration rate (renal function)
  liver_panel_normal boolean, -- null = unknown/not on file, not "assumed normal"
  labs_recorded_at timestamptz,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- prescriptions: one row per Extractor/Safety agent run
-- ---------------------------------------------------------------------
create table if not exists prescriptions (
  id uuid primary key default uuid_generate_v4(),
  trace_id uuid not null unique,
  doctor_id uuid not null references doctors (id) on delete cascade,
  patient_id uuid references patients (id) on delete set null,
  raw_text text not null,
  diagnosis text not null,
  medications jsonb not null default '[]',
  advice text,
  warnings jsonb not null default '[]',
  is_safe boolean not null default true,
  status text not null default 'draft' check (status in ('draft', 'printed', 'overridden')),
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- prescription_overrides: human-in-the-loop audit trail for force-printing
-- a prescription that the Safety agent flagged as unsafe
-- ---------------------------------------------------------------------
create table if not exists prescription_overrides (
  id uuid primary key default uuid_generate_v4(),
  prescription_id uuid not null references prescriptions (id) on delete cascade,
  doctor_id uuid not null references doctors (id) on delete cascade,
  reason text not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- patient_lookup_audit_log: every time the patient-records chatbot looks
-- up a patient's file, we record who asked and what they searched for.
-- This table exists specifically because the chatbot has direct database
-- read access to sensitive medical records (PHI) -- every access must be
-- traceable to a specific doctor and moment in time.
-- ---------------------------------------------------------------------
create table if not exists patient_lookup_audit_log (
  id uuid primary key default uuid_generate_v4(),
  doctor_id uuid not null references doctors (id) on delete cascade,
  patient_id uuid references patients (id) on delete set null,
  query_text text not null,
  found boolean not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- treatment_relationships: the access-control backbone. A doctor may only
-- view a patient's full record if an active (or referred) relationship
-- exists here -- NOT simply because they're an authenticated doctor.
--
-- Lifecycle:
--   - 'active'   created automatically the first time a doctor writes a
--                prescription for a patient (see app trigger logic)
--   - 'referred' created when the treating doctor refers the patient to
--                another doctor/specialist; the referring doctor is
--                recorded in `referred_by`
--   - 'ended'    set when treatment concludes; the relationship row is
--                kept (not deleted) for audit history, just no longer
--                grants access
-- ---------------------------------------------------------------------
create table if not exists treatment_relationships (
  id uuid primary key default uuid_generate_v4(),
  doctor_id uuid not null references doctors (id) on delete cascade,
  patient_id uuid not null references patients (id) on delete cascade,
  status text not null default 'active' check (status in ('active', 'referred', 'ended')),
  referred_by uuid references doctors (id) on delete set null,
  reason text,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  unique (doctor_id, patient_id)
);

-- ---------------------------------------------------------------------
-- Row Level Security: a doctor can only see their own prescriptions
-- ---------------------------------------------------------------------
alter table doctors enable row level security;
alter table patients enable row level security;
alter table prescriptions enable row level security;
alter table prescription_overrides enable row level security;
alter table patient_lookup_audit_log enable row level security;
alter table treatment_relationships enable row level security;

create policy "doctors can read own profile" on doctors
  for select using (auth.uid() = id);

-- Replaces the old "any authenticated doctor can read all patients"
-- policy: a doctor may only SELECT a patient row if they hold an active
-- (or referred) treatment relationship with that patient.
create policy "doctors can read patients they treat" on patients
  for select using (
    exists (
      select 1 from treatment_relationships tr
      where tr.patient_id = patients.id
        and tr.doctor_id = auth.uid()
        and tr.status in ('active', 'referred')
    )
  );

create policy "doctors can insert patients" on patients
  for insert with check (auth.role() = 'authenticated');

create policy "doctors manage own prescriptions" on prescriptions
  for all using (auth.uid() = doctor_id) with check (auth.uid() = doctor_id);

create policy "doctors manage own overrides" on prescription_overrides
  for all using (auth.uid() = doctor_id) with check (auth.uid() = doctor_id);

create policy "doctors can read own lookup log" on patient_lookup_audit_log
  for select using (auth.uid() = doctor_id);

create policy "doctors can insert own lookup log" on patient_lookup_audit_log
  for insert with check (auth.uid() = doctor_id);

create policy "doctors can read own treatment relationships" on treatment_relationships
  for select using (auth.uid() = doctor_id or auth.uid() = referred_by);

create policy "doctors can create treatment relationships" on treatment_relationships
  for insert with check (auth.uid() = doctor_id or auth.uid() = referred_by);

create policy "doctors can update own treatment relationships" on treatment_relationships
  for update using (auth.uid() = doctor_id);

create index if not exists idx_prescriptions_doctor on prescriptions (doctor_id, created_at desc);
create index if not exists idx_prescriptions_patient on prescriptions (patient_id);
create index if not exists idx_patients_full_name on patients (lower(full_name));
create index if not exists idx_patients_father_name on patients (lower(father_name));
create index if not exists idx_lookup_audit_doctor on patient_lookup_audit_log (doctor_id, created_at desc);
create index if not exists idx_treatment_rel_doctor on treatment_relationships (doctor_id, status);
create index if not exists idx_treatment_rel_patient on treatment_relationships (patient_id, status);
