-- Doctor Copilot System — Supabase schema
-- Run in the Supabase SQL editor, or via `supabase db push`.

create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------
-- doctors: one row per authenticated doctor (mirrors auth.users)
-- ---------------------------------------------------------------------
create table if not exists doctors (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
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
  full_name text not null,
  age int,
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
-- Row Level Security: a doctor can only see their own prescriptions
-- ---------------------------------------------------------------------
alter table doctors enable row level security;
alter table patients enable row level security;
alter table prescriptions enable row level security;
alter table prescription_overrides enable row level security;

create policy "doctors can read own profile" on doctors
  for select using (auth.uid() = id);

create policy "doctors can read all patients" on patients
  for select using (auth.role() = 'authenticated');

create policy "doctors can insert patients" on patients
  for insert with check (auth.role() = 'authenticated');

create policy "doctors manage own prescriptions" on prescriptions
  for all using (auth.uid() = doctor_id) with check (auth.uid() = doctor_id);

create policy "doctors manage own overrides" on prescription_overrides
  for all using (auth.uid() = doctor_id) with check (auth.uid() = doctor_id);

create index if not exists idx_prescriptions_doctor on prescriptions (doctor_id, created_at desc);
create index if not exists idx_prescriptions_patient on prescriptions (patient_id);
