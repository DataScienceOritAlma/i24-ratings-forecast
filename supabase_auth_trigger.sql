-- =====================================================
-- Auto-create organization + profile on user signup
-- =====================================================
-- כשמשתמש חדש נרשם דרך Supabase Auth, יוצר אוטומטית:
--   1. organization (פר-משתמש, type='individual', name=email)
--   2. profile (מקושר למשתמש + לאירגון, role='owner')
-- כך RLS עובד מיידית.
-- =====================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_org_id uuid;
  display_name text;
begin
  display_name := coalesce(
    new.raw_user_meta_data->>'full_name',
    new.email,
    'New User'
  );

  insert into public.organizations (name, type)
  values (display_name, 'individual')
  returning id into new_org_id;

  insert into public.profiles (id, organization_id, full_name, role)
  values (new.id, new_org_id, display_name, 'owner');

  return new;
end;
$$;

-- Trigger on auth.users (Supabase managed)
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
