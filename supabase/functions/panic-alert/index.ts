// Supabase Edge Function: panic-alert
//
// Recebe a localização da usuária, busca os contatos de emergência dela no banco
// e dispara um e-mail de alerta para cada contato usando a API do Brevo (camada
// gratuita: 300 e-mails/dia).
//
// As credenciais NUNCA ficam no app Flutter — só aqui, como secrets do Supabase.
//
// Secrets necessários (configurar com `supabase secrets set`):
//   BREVO_API_KEY   -> chave de API criada no painel do Brevo
//   SENDER_EMAIL    -> e-mail remetente verificado no Brevo (ex: alerta@seudominio.com)
//   SENDER_NAME     -> (opcional) nome de exibição, padrão "SafeHer"
//
// SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são injetados automaticamente.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  // Pré-flight de CORS (necessário para a versão web do app).
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { latitude, longitude } = await req.json();

    // 1. Identifica a usuária pelo token JWT que o app envia no header.
    const authHeader = req.headers.get("Authorization") ?? "";
    const jwt = authHeader.replace("Bearer ", "");

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const admin = createClient(supabaseUrl, serviceKey);

    const { data: userData, error: userError } = await admin.auth.getUser(jwt);
    if (userError || !userData?.user) {
      return new Response(
        JSON.stringify({ error: "Usuária não autenticada." }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }
    const user = userData.user;

    // 2. Busca o nome da usuária e os contatos de emergência.
    const { data: perfil } = await admin
      .from("profiles")
      .select("nome_completo")
      .eq("id", user.id)
      .maybeSingle();

    const nomeUsuaria = perfil?.nome_completo ?? "Uma usuária do SafeHer";

    const { data: contatos } = await admin
      .from("emergency_contacts")
      .select("nome, email")
      .eq("profile_id", user.id);

    const destinatarios = (contatos ?? []).filter(
      (c) => c.email && c.email.trim().length > 0,
    );

    if (destinatarios.length === 0) {
      return new Response(
        JSON.stringify({
          enviados: 0,
          aviso: "Nenhum contato com e-mail cadastrado.",
        }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // 3. Monta a mensagem.
    const temLocal =
      typeof latitude === "number" && typeof longitude === "number";
    const linkMapa = temLocal
      ? `https://www.google.com/maps?q=${latitude},${longitude}`
      : null;

    const html = `
      <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
        <div style="background:#E24B4A; color:#fff; padding:16px; border-radius:8px 8px 0 0;">
          <h2 style="margin:0;">🚨 Alerta de Emergência</h2>
        </div>
        <div style="border:1px solid #eee; border-top:none; padding:20px; border-radius:0 0 8px 8px;">
          <p><strong>${nomeUsuaria}</strong> acionou o botão de pânico no aplicativo <strong>SafeHer</strong> e precisa de ajuda.</p>
          ${
            linkMapa
              ? `<p>📍 Localização atual:<br/>
                 <a href="${linkMapa}" style="color:#D4537E; font-weight:bold;">Abrir no Google Maps</a></p>`
              : `<p>📍 A localização não pôde ser obtida.</p>`
          }
          <p style="color:#888; font-size:12px; margin-top:24px;">
            Este e-mail foi enviado automaticamente pelo SafeHer. Se você é um contato de
            emergência desta pessoa, tente contatá-la imediatamente.
          </p>
        </div>
      </div>`;

    // 4. Dispara um e-mail para cada contato via Brevo.
    const brevoKey = Deno.env.get("BREVO_API_KEY")!;
    const senderEmail = Deno.env.get("SENDER_EMAIL")!;
    const senderName = Deno.env.get("SENDER_NAME") ?? "SafeHer";

    let enviados = 0;
    for (const contato of destinatarios) {
      const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
        method: "POST",
        headers: {
          "api-key": brevoKey,
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify({
          sender: { name: senderName, email: senderEmail },
          to: [{ email: contato.email, name: contato.nome ?? undefined }],
          subject: `🚨 ${nomeUsuaria} acionou um alerta de emergência`,
          htmlContent: html,
        }),
      });

      if (resp.ok) {
        enviados++;
      } else {
        console.error("Falha ao enviar e-mail:", await resp.text());
      }
    }

    return new Response(
      JSON.stringify({ enviados, total: destinatarios.length }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    console.error("Erro na função panic-alert:", e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
