-- Additive migration: existing plans and RLS policies are preserved.
alter table public.plans add column if not exists selected_at timestamptz;
