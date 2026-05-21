-- =====================================================
-- i24 Ratings Forecast — Database Schema v1.0
-- =====================================================
-- מסד נתונים של ה-SaaS: 6 טבלאות, RLS פר-טבלה, indices
-- מקור-אמת: SCHEMA.md
--
-- שימוש:
--   1. כנסי ל-Supabase → SQL Editor → New query
--   2. הדביקי את כל הקובץ
--   3. לחיצה על "Run" (או Ctrl+Enter)
--   4. אמור להופיע: "schema.sql complete · 6 tables ready"
--
-- הקובץ אידמפוטנטי — בטוח להריץ אותו שוב אם משהו השתבש.
-- =====================================================

-- 0. Extensions
create extension if not exists "pgcrypto";  -- ל-gen_random_uuid()

-- =====================================================
-- 1. Tables
-- =====================================================

-- ארגונים (יחידת multi-tenancy)
create table if not exists public.organizations (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  type          text not null check (type in ('agency','research','channel','individual')),
  created_at    timestamptz not null default now()
);

-- פרופילים (מטא-דאטא על משתמשים — מרחיב את auth.users של Supabase)
create table if not exists public.profiles (
  id               uuid primary key references auth.users(id) on delete cascade,
  organization_id  uuid references public.organizations(id) on delete set null,
  full_name        text,
  role             text not null default 'member' check (role in ('owner','member','admin')),
  created_at       timestamptz not null default now()
);

-- מנויים (סנכרון עם Stripe)
create table if not exists public.subscriptions (
  id                       uuid primary key default gen_random_uuid(),
  organization_id          uuid not null unique references public.organizations(id) on delete cascade,
  stripe_customer_id       text unique,
  stripe_subscription_id   text unique,
  status                   text check (status in ('trialing','active','past_due','canceled','incomplete')),
  tier                     text not null check (tier in ('trial','pro','enterprise')),
  trial_ends_at            timestamptz,
  current_period_end       timestamptz,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

-- קטלוג תוכניות (משותף, קריאה ציבורית)
create table if not exists public.programs (
  id              uuid primary key default gen_random_uuid(),
  name            text not null unique,
  source_name     text,
  first_aired     date,
  last_aired      date,
  n_broadcasts    int default 0,
  typical_status  text,
  typical_day     text,
  typical_hour    text,
  updated_at      timestamptz not null default now()
);

-- שידורים היסטוריים (משותף)
create table if not exists public.broadcasts (
  id              uuid primary key default gen_random_uuid(),
  program_id      uuid not null references public.programs(id) on delete cascade,
  broadcast_date  date not null,
  start_time      time not null,
  end_time        time,
  duration_min    int,
  day_of_week     text,
  daypart         text,
  status          text,
  event           text,
  is_rerun        boolean default false,
  actual_rating   numeric(6,3),
  share           numeric(6,2),
  viewers_4plus   integer,
  hut_proxy       numeric(6,2),
  reception_pct   numeric(5,3),
  imported_at     timestamptz not null default now(),
  unique (broadcast_date, start_time, program_id)
);

-- תחזיות (פרטי פר-ארגון)
create table if not exists public.predictions (
  id                    uuid primary key default gen_random_uuid(),
  organization_id       uuid not null references public.organizations(id) on delete cascade,
  user_id               uuid not null references auth.users(id) on delete cascade,
  program_id            uuid references public.programs(id) on delete set null,
  target_date           date not null,
  target_start_time     time,
  target_end_time       time,
  scenario              text default 'routine' check (scenario in ('routine','special_event')),
  predicted_rating      numeric(6,3),
  prediction_low        numeric(6,3),
  prediction_high       numeric(6,3),
  estimated_households  integer,
  estimated_viewers     integer,
  model_version         text,
  created_at            timestamptz not null default now(),
  actual_rating         numeric(6,3),
  actual_recorded_at    timestamptz,
  prediction_error      numeric(6,3) generated always as (predicted_rating - actual_rating) stored
);

-- =====================================================
-- 2. Indices
-- =====================================================

create index if not exists idx_broadcasts_date     on public.broadcasts(broadcast_date);
create index if not exists idx_broadcasts_program  on public.broadcasts(program_id);
create index if not exists idx_broadcasts_status   on public.broadcasts(status);
create index if not exists idx_programs_name       on public.programs(name);
create index if not exists idx_predictions_org     on public.predictions(organization_id, created_at desc);
create index if not exists idx_predictions_target  on public.predictions(target_date);

-- =====================================================
-- 3. Helper Functions
-- =====================================================

-- האירגון של המשתמש הנוכחי (לשימוש ב-RLS policies)
create or replace function public.current_user_org()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select organization_id from public.profiles where id = auth.uid()
$$;

-- אוטומציה ל-updated_at
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Trigger ל-subscriptions
drop trigger if exists trg_subscriptions_updated_at on public.subscriptions;
create trigger trg_subscriptions_updated_at
  before update on public.subscriptions
  for each row execute function public.set_updated_at();

-- Trigger ל-programs
drop trigger if exists trg_programs_updated_at on public.programs;
create trigger trg_programs_updated_at
  before update on public.programs
  for each row execute function public.set_updated_at();

-- =====================================================
-- 4. RLS (Row-Level Security)
-- =====================================================

alter table public.organizations enable row level security;
alter table public.profiles      enable row level security;
alter table public.subscriptions enable row level security;
alter table public.programs      enable row level security;
alter table public.broadcasts    enable row level security;
alter table public.predictions   enable row level security;

-- Drop existing policies (idempotent re-runs)
drop policy if exists org_select_members        on public.organizations;
drop policy if exists profiles_select_org       on public.profiles;
drop policy if exists profiles_update_self      on public.profiles;
drop policy if exists profiles_insert_self      on public.profiles;
drop policy if exists subscriptions_select_org  on public.subscriptions;
drop policy if exists programs_select_auth      on public.programs;
drop policy if exists broadcasts_select_auth    on public.broadcasts;
drop policy if exists predictions_select_org    on public.predictions;
drop policy if exists predictions_insert_org    on public.predictions;
drop policy if exists predictions_update_org    on public.predictions;

-- organizations: members can read their own org
create policy org_select_members on public.organizations
  for select using (id = public.current_user_org());

-- profiles: read others in same org · update only self · insert only self
create policy profiles_select_org on public.profiles
  for select using (organization_id = public.current_user_org());

create policy profiles_update_self on public.profiles
  for update using (id = auth.uid());

create policy profiles_insert_self on public.profiles
  for insert with check (id = auth.uid());

-- subscriptions: read for org members; writes only via service_role (Stripe webhook)
create policy subscriptions_select_org on public.subscriptions
  for select using (organization_id = public.current_user_org());

-- programs + broadcasts: public read for any authenticated user (catalog/training data)
create policy programs_select_auth on public.programs
  for select using (auth.role() = 'authenticated');

create policy broadcasts_select_auth on public.broadcasts
  for select using (auth.role() = 'authenticated');

-- predictions: each org sees only its own; can insert for own org only
create policy predictions_select_org on public.predictions
  for select using (organization_id = public.current_user_org());

create policy predictions_insert_org on public.predictions
  for insert with check (
    organization_id = public.current_user_org() and user_id = auth.uid()
  );

create policy predictions_update_org on public.predictions
  for update using (organization_id = public.current_user_org());

-- =====================================================
-- 5. Verification
-- =====================================================

select 'schema.sql complete · 6 tables ready' as status,
       (select count(*) from information_schema.tables
        where table_schema = 'public'
          and table_name in ('organizations','profiles','subscriptions',
                             'programs','broadcasts','predictions')) as tables_created;
