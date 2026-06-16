-- Adiciona o campo de e-mail aos contatos de emergência.
-- Necessário para que o botão de pânico consiga enviar o alerta por e-mail
-- (canal gratuito que funciona em Android, iOS e Web).
alter table public.emergency_contacts
  add column if not exists email text;
