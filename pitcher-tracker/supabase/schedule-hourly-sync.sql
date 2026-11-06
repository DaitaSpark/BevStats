-- First create Vault secrets bevstats_function_url and bevstats_sync_secret.
-- Enable Cron (pg_cron) and pg_net in Supabase Integrations before running.
select cron.schedule('bevstats-hourly-sync','0 * * * *',$job$
 select net.http_post(
  url := (select decrypted_secret from vault.decrypted_secrets where name='bevstats_function_url'),
  headers := jsonb_build_object('Content-Type','application/json','x-sync-secret',
   (select decrypted_secret from vault.decrypted_secrets where name='bevstats_sync_secret')),
  body := '{}'::jsonb,
  timeout_milliseconds := 90000
 );
$job$);
