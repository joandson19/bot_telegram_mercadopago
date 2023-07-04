import datetime
import mercadopago
import telebot
import base64
from PIL import Image
from io import BytesIO
import time
import logging

# Configurar o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

sdk = mercadopago.SDK('TOKEN-MERCADOPAGO')
bot = telebot.TeleBot('BOT-TELEGRAM')

# Lista de IDs de chat autorizados
AUTHORIZED_CHAT_IDS = [SEU_ID, SEU_ID]  # Adicione os IDs de chat autorizados aqui, pode ser grupo!
def is_authorized_chat(chat_id):
    return chat_id in AUTHORIZED_CHAT_IDS

@bot.message_handler(commands=['start'])
def cmd_start(message):
    start_message = "Bem-vindo ao Bot de Pagamentos da AlagoinhasTelecom!\n\n" \
                    "Para realizar um pagamento via Pix, utilize o comando /pix seguido do valor do Pix.\n" \
                    "Por exemplo: /pix 10\n\n" \
                    "Você receberá um QR code para realizar o pagamento.\n" \
                    "O bot verificará automaticamente se o pagamento foi recebido e enviará uma confirmação.\n\n" \
                    "Digite /help para ver a lista completa de comandos disponíveis.\n\n" \
                    "Favor somente digitar valores inteiros sem centavos, não geramos qrcode paga valores seguidos de sentavos, somente real inteiro"
    bot.reply_to(message, start_message)


@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_message = "Lista de comandos disponíveis:\n\n" \
                   "/start - Iniciar o bot e obter informações\n" \
                   "/help - Exibir esta mensagem de ajuda\n" \
                   "/listar - Listar pagamentos recentes\n" \
                   "/verificar [ID] - Verificar o status de um pagamento pelo ID\n" \
                   "/pix [valor] - Realizar um pagamento via Pix\n\n" \
                   "Exemplo: /pix 10"
    bot.reply_to(message, help_message)


def create_payment(value, client_name):
    expire = datetime.datetime.now() + datetime.timedelta(minutes=30)
    expire = expire.strftime("%Y-%m-%dT%-H:%M:%S.000-03:00")

    description = f"Pagamento de {client_name}"

    payment_data = {
        "transaction_amount": int(value),
        "payment_method_id": 'pix',
        "installments": 1,
        "description": description,
        "date_of_expiration": f"{expire}",
        "payer": {
            "email": 'pix@alagoinhastelecom.com.br'
        }
    }
    result = sdk.payment().create(payment_data)
    operation_number = result['response']['id']  # Extrai o ID da transação (Número de Operação de Cobrança)
    return result, operation_number


def verificar_pagamento(operation_number, chat_id, message_id, client_name):
    for _ in range(24):  # Executa a verificação por 4 minutos (24 vezes a cada 10 segundos)
        time.sleep(10)  # Aguarda 10 segundos antes de cada verificação
        result = sdk.payment().get(operation_number)
        status = result['response']['status']
        if status == 'approved':
            value = result['response']['transaction_amount']
            logger.info(f"Pagamento de número {operation_number} recebido com sucesso!")
            bot.send_message(chat_id, f"O pagamento de número {operation_number} foi recebido com sucesso!\n\n"
                                      f"Detalhes do pagamento:\n"
                                      f"Cliente: {client_name}\n"
                                      f"Valor: R${value}\n"
                                      f"Link do comprovante:\n"
                                      f"https://www.mercadopago.com.br/money-out/transfer/api/receipt/pix_pdf/"
                                      f"{operation_number}/pix_account/pix_payment.pdf")
            bot.delete_message(chat_id, message_id)  # Apaga a mensagem com o QR code
            return  # Interrompe o loop e a função
    logger.info(f"Pagamento de número {operation_number} não recebido após 4 minutos.")
    bot.send_message(chat_id, "Pagamento não recebido após 4 minutos.")
    bot.delete_message(chat_id, message_id)  # Apaga a mensagem com o QR code


def capture_name(message):
    global value  # Adicione esta linha para utilizar a variável global "value"
    client_name = message.text
    payment, operation_number = create_payment(value, client_name)
    result = payment['response']
    pix_copia_cola = result['point_of_interaction']['transaction_data']['qr_code']
    qr_code = result['point_of_interaction']['transaction_data']['qr_code_base64']
    qr_code = base64.b64decode(qr_code)
    qr_code_img = Image.open(BytesIO(qr_code))
    qrcode_output = qr_code_img.convert('RGB')

    # Caso queira que o bot envie o qrcode no grupo ou no privado descomente a linha abaixo!
    sent_message = bot.send_photo(message.chat.id, qrcode_output,
    # Caso queira que o bot só envie o qrcode no privado descomente a linha abaixo e comente a de cima!
    #sent_message = bot.send_photo(message.from_user.id, qrcode_output,
                                  f'<code>{pix_copia_cola}</code>\n\n'
                                  f'Número de operação: {operation_number}\n'
                                  f'Cliente: {client_name}\n\n'
                                  f'Aguardando pagamento...',
                                  parse_mode='HTML')

    # Gerando log do pagamento
    logger.info(f"Pix Valor: R${value}, Cliente: {client_name}, Data e Hora: {datetime.datetime.now()}")
    # Agendamento da verificação periódica do pagamento
    verificar_pagamento(operation_number, message.chat.id, sent_message.message_id, client_name)


@bot.message_handler(commands=['listar'])
def cmd_listar(message):
    payments = sdk.payment().search({'sort': 'date_created', 'criteria': 'desc'})
    for payment in payments['response']['results']:
        print(payment['id'], payment['status'], payment['description'], payment['date_of_expiration'])
        logger.info(f"ID: {payment['id']}, Status: {payment['status']}, Descrição: {payment['description']}, "
                    f"Data de Expiração: {payment['date_of_expiration']}")





@bot.message_handler(commands=['verificar'])
def cmd_verificar(message):
    if len(message.text.split()) < 2:
        bot.reply_to(message, "Por favor, forneça o número da transação.")
        return

    pg_id = message.text.split()[1]
    result = sdk.payment().get(pg_id)
    status = result['response']['status']
    if status == 'approved':
        bot.reply_to(message, "Pagamento recebido!")
        logger.info(f"Verificação de pagamento - Pagamento recebido - ID: {pg_id}")
    elif status == 'cancelled':
        bot.reply_to(message, "Pagamento excedeu o tempo!")
        logger.info(f"Verificação de pagamento - Pagamento excedeu o tempo - ID: {pg_id}")
    else:
        bot.reply_to(message, "Pagamento pendente ou não encontrado.")
        logger.info(f"Verificação de pagamento - Pagamento pendente ou não encontrado - ID: {pg_id}")

@bot.message_handler(commands=['pix'])
def cmd_pix(message):
    # Esta sessão inicia a verificação de id autorizado
    if not is_authorized_chat(message.chat.id):
        bot.reply_to(message, f"Acesso não autorizado.\n"
                              f"Solicite a autorização usando seu chatid abaixo.\n\n"
                              f"Seu ID: {message.chat.id}")
        return
    # Inicia a logica de geração do pix qrcode
    try:
        global value  # Adicione esta linha para utilizar a variável global "value"
        value = float(message.text.split()[1].replace(',', '.'))
        bot.reply_to(message, "Digite o nome do cliente:")

        # Define a função de tratamento de mensagem para capturar o nome do cliente
        bot.register_next_step_handler(message, capture_name)
    except IndexError:
        bot.reply_to(message, "Por favor, forneça o valor do Pix após o comando.")
    except ValueError:
        bot.reply_to(message, "Valor do Pix inválido. Certifique-se de usar um número válido.")
    except Exception as e:
        bot.reply_to(message, "Ocorreu um erro ao processar a solicitação. Tente novamente mais tarde.")


if __name__ == "__main__":
    bot.infinity_polling()
