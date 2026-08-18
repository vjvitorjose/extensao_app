-- 1. Adiciona a coluna CPF na tabela de perfis de usuárias (public.profiles)
alter table public.profiles
  add column if not exists cpf text;

-- 2. Cria a tabela separada para o Banco de Vítimas Reincidentes
create table if not exists public.recurring_victims (
  id uuid not null default gen_random_uuid(),
  cpf text not null unique,
  nome_completo text,
  observacoes text,
  ativo boolean default true,
  criado_em timestamp with time zone default now(),
  constraint recurring_victims_pkey primary key (id)
);

-- Habilita RLS (Row Level Security) e permite leitura autenticada
alter table public.recurring_victims enable row level security;

create policy "Permite leitura autenticada na tabela de vítimas reincidentes"
  on public.recurring_victims
  for select
  to authenticated
  using (true);

-- 3. Insere CPFs de teste no Banco de Vítimas Reincidentes
insert into public.recurring_victims (cpf, nome_completo, observacoes)
values 
  ('12345678900', 'Vítima Exemplo 1', 'Medida protetiva ativa'),
  ('11122233344', 'Vítima Exemplo 2', 'Medida protetiva ativa')
on conflict (cpf) do nothing;
