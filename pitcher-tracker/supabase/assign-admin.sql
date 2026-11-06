-- Run after creating/confirming this Auth account in the Supabase dashboard.
begin;
do $$
declare admin_id uuid;
begin
  select id into strict admin_id from auth.users
  where lower(email) = 'jeff.eckard@daitaspark.com'
    and email_confirmed_at is not null;
  insert into public.bevstats_owner(singleton,user_id) values (true,admin_id)
    on conflict(singleton) do update set user_id = excluded.user_id;
exception when no_data_found then
  raise exception 'Create and confirm jeff.eckard@daitaspark.com in Supabase Auth before assigning admin access.';
end $$;
commit;
