-- ============================================================
-- Migration 0004: Privacy by Design — Dissociação de Identidade
-- ============================================================
-- Objetivo: garantir que denúncias georreferenciadas sejam
-- acessíveis publicamente SEM expor o usuario_id do denunciante,
-- em conformidade com o princípio de Privacy by Design (LGPD Art. 46).
--
-- Estratégia:
--   1. Cria uma VIEW pública (danger_reports_public) que omite
--      as colunas de identidade (usuario_id, user_id).
--   2. Garante via RLS que usuários autenticados (não-admin) leiam
--      apenas colunas não-identificáveis, ou apenas seus próprios registros.
-- ============================================================

-- 1. View pública sem colunas de identidade
-- Expõe apenas os dados analíticos e geográficos das denúncias.
create or replace view public.danger_reports_public as
select
  id,
  tipo_perigo,
  descricao,
  latitude,
  longitude,
  endereco,
  criado_em,
  created_at,
  nivel_risco,
  anonimo
from public.danger_reports;

-- 2. Habilita RLS na tabela base (caso ainda não esteja ativo).
alter table public.danger_reports enable row level security;

-- 3. Remove policies antigas de SELECT para evitar conflitos.
drop policy if exists "Usuários autenticados podem ver alertas" on public.danger_reports;
drop policy if exists "Leitura pública de alertas" on public.danger_reports;
drop policy if exists "Usuários leem apenas seus próprios registros identificados" on public.danger_reports;

-- 4. Policy de LEITURA para usuários autenticados:
--    Podem ver qualquer registro anônimo (usuario_id/user_id nulos)
--    OU apenas os seus próprios registros identificados.
create policy "Usuarios leem registros anonimos ou proprios"
  on public.danger_reports
  for select
  to authenticated
  using (
    usuario_id is null
    or user_id is null
    or usuario_id = auth.uid()
    or user_id = auth.uid()
  );

-- 5. Policy de INSERÇÃO: qualquer usuário autenticado pode criar denúncias.
drop policy if exists "Usuários autenticados podem inserir alertas" on public.danger_reports;
create policy "Usuarios autenticados podem inserir alertas"
  on public.danger_reports
  for insert
  to authenticated
  with check (true);

-- 6. Concede permissão de SELECT na view pública para usuários autenticados.
grant select on public.danger_reports_public to authenticated;

-- ============================================================
-- NOTA: o papel service_role (usado nas Edge Functions e no
-- painel Supabase) ignora RLS por padrão, mantendo acesso
-- administrativo completo quando necessário.
-- ============================================================
