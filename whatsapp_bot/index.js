const fetch = require('cross-fetch');
globalThis.fetch = fetch;
globalThis.Headers = fetch.Headers;
globalThis.Request = fetch.Request;
globalThis.Response = fetch.Response;
globalThis.WebSocket = require('ws');

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('Escaneie o QR Code acima com o seu WhatsApp para fazer o login.');
});

client.on('ready', () => {
    console.log('✅ Servidor conectado ao WhatsApp! Iniciando a leitura da fila sms_queue...');
    
    // Inicia o processo de verificação a cada 10 segundos
    setInterval(verificarFilaEEnviar, 10000);
    // Também chama imediatamente na primeira vez
    verificarFilaEEnviar();
});

let isProcessing = false;

async function verificarFilaEEnviar() {
    if (isProcessing) return; // Evita sobreposição se a execução demorar
    isProcessing = true;

    try {
        const { data: mensagensParaEnviar, error } = await supabase
            .from('sms_queue')
            .select('*')
            .eq('status', 'pendente')
            .limit(5); // Processa em lotes de 5

        if (error) {
            console.error('Erro ao buscar mensagens do Supabase:', error.message);
            isProcessing = false;
            return;
        }

        if (!mensagensParaEnviar || mensagensParaEnviar.length === 0) {
            isProcessing = false;
            return;
        }

        for (const item of mensagensParaEnviar) {
            const numero = item.numero;
            if (!numero) continue;
            
            // O numero pode vir como "37991313422", adicionamos o código de país do Brasil (+55) caso não tenha.
            // Para maior robustez, garantimos apenas a formatação whatsapp:
            let fone = numero.toString().trim();
            if (fone.length <= 11) {
                fone = '55' + fone;
            }

            try {
                console.log(`Verificando o número ${fone} no WhatsApp...`);
                // Descobre o ID real do usuário no WhatsApp (resolve o problema do 9º dígito no Brasil)
                const numberId = await client.getNumberId(fone);

                if (!numberId) {
                    console.error(`❌ O número ${fone} não possui WhatsApp ou é inválido.`);
                    // Atualiza o status para 'erro' para não travar a fila
                    await supabase.from('sms_queue').update({ status: 'erro' }).eq('sms_id', item.sms_id);
                    continue;
                }

                console.log(`Enviando alerta para ${numberId.user}...`);
                await client.sendMessage(numberId._serialized, item.mensagem);
                console.log(`✅ Alerta enviado com sucesso para ${numberId.user}`);
                
                // Atualiza o status para 'enviado' para não reenviar
                const { error: updError } = await supabase
                    .from('sms_queue')
                    .update({ status: 'enviado' })
                    .eq('sms_id', item.sms_id);
                if (updError) {
                    console.error(`Erro ao atualizar mensagem ID ${item.sms_id} na fila:`, updError.message);
                }
            } catch (err) {
                console.error(`❌ Erro ao enviar mensagem para ${fone}:`, err);
            }
        }
    } catch (globalError) {
        console.error('Erro inesperado no loop:', globalError);
    } finally {
        isProcessing = false;
    }
}

client.initialize();
