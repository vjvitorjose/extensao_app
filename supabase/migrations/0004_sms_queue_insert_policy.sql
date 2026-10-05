-- Permite que usuários autenticados enfileirem alertas na sms_queue.
create policy "authenticated can insert sms_queue"
on public.sms_queue
for insert
to authenticated
with check (true);
