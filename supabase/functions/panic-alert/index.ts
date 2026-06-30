// Supabase Edge Function: panic-alert
//
// Recebe a localização da usuária, busca os contatos de emergência no banco
// e envia mensagens SMS para os telefones cadastrado(s) usando Twilio.
//
// IMPORTANTE: as credenciais NUNCA ficam no app Flutter — apenas como secrets
// do Supabase (configurar com `supabase secrets set`). Secrets necessários:
//   TWILIO_ACCOUNT_SID            -> Account SID do Twilio
//   TWILIO_AUTH_TOKEN             -> Auth Token do Twilio
//   TWILIO_FROM_NUMBER            -> Número Twilio para SMS (ex: +15552223333)
//   TWILIO_WHATSAPP_FROM_NUMBER   -> Número Twilio para WhatsApp (ex: whatsapp:+15552223333)
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
      .select("nome, telefone")
      .eq("profile_id", user.id);

    // 3. Monta a mensagem.
    const temLocal =
      typeof latitude === "number" && typeof longitude === "number";
    const linkMapa = temLocal
      ? `https://www.google.com/maps?q=${latitude},${longitude}`
      : null;

    // 4. Envia SMS via Twilio para contatos com telefone.
    const twilioSid = Deno.env.get("TWILIO_ACCOUNT_SID");
    const twilioAuth = Deno.env.get("TWILIO_AUTH_TOKEN");
    const twilioFrom = Deno.env.get("TWILIO_FROM_NUMBER");
    const twilioWhatsappFrom = Deno.env.get("TWILIO_WHATSAPP_FROM_NUMBER");

    let smsEnviados = 0;
    let whatsappEnviados = 0;
    const contatosComTelefone = (contatos ?? []).filter(
      (c) => c.telefone && c.telefone.toString().trim().length > 0,
    );

    if (!twilioSid || !twilioAuth || !twilioFrom) {
      return new Response(
        JSON.stringify({
          enviados_sms: 0,
          enviados_whatsapp: 0,
          total_telefones: contatosComTelefone.length,
          aviso:
            "Twilio não configurado. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_FROM_NUMBER.",
        }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const mensagemPrincipal = temLocal
      ? `🚨 ${nomeUsuaria} acionou um alerta de emergência. Local: ${linkMapa}`
      : `🚨 ${nomeUsuaria} acionou um alerta de emergência. Localização indisponível.`;

    const mensagemWhatsapp = `${mensagemPrincipal} Responda imediatamente.`;

    for (const contato of contatosComTelefone) {
      const telefone = contato.telefone.toString().trim();
      try {
        const body = new URLSearchParams();
        body.append("From", twilioFrom);
        body.append("To", telefone);
        body.append("Body", mensagemPrincipal);

        const resp = await fetch(
          `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
          {
            method: "POST",
            headers: {
              "Authorization": `Basic ${btoa(`${twilioSid}:${twilioAuth}`)}`,
              "Content-Type": "application/x-www-form-urlencoded",
            },
            body: body.toString(),
          },
        );

        if (resp.ok) smsEnviados++;
        else console.error("Falha ao enviar SMS Twilio:", await resp.text());
      } catch (e) {
        console.error("Erro ao enviar SMS Twilio para", telefone, e);
      }

      if (twilioWhatsappFrom) {
        try {
          const whatsappBody = new URLSearchParams();
          whatsappBody.append("From", twilioWhatsappFrom);
          whatsappBody.append("To", `whatsapp:${telefone}`);
          whatsappBody.append("Body", mensagemWhatsapp);

          const respWhatsapp = await fetch(
            `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
            {
              method: "POST",
              headers: {
                "Authorization": `Basic ${btoa(`${twilioSid}:${twilioAuth}`)}`,
                "Content-Type": "application/x-www-form-urlencoded",
              },
              body: whatsappBody.toString(),
            },
          );

          if (respWhatsapp.ok) whatsappEnviados++;
          else console.error("Falha ao enviar WhatsApp Twilio:", await respWhatsapp.text());
        } catch (e) {
          console.error("Erro ao enviar WhatsApp Twilio para", telefone, e);
        }
      }
    }

    return new Response(
      JSON.stringify({
        enviados_sms: smsEnviados,
        enviados_whatsapp: whatsappEnviados,
        total_telefones: contatosComTelefone.length,
      }),
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
