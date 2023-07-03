# bot_telegram_mercadopago

Bot que gera qrcode de paramento usando api do mercadopago
O qrcode é gerado e enviado na tela do bot no telegram para ser lido, caso seja pago no intervalo de 2 minutos o qrcode é apagado e gerado uma mensagem de "O pagamento de número {operation_number} foi recebido com sucesso!", caso contrario ele apaga o qrcode e emite uma mensagem de "Pagamento não recebido após 2 minutos."
