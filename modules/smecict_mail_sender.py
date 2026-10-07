import os
import io
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account  # Importação direta para criar a credencial limpa

# -------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGS COMPLETA
# -------------------------------------------------------------------------
LOG_FILE = "/var/log/fastapi-mail-out.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mail_sender")

load_dotenv()

class Send_mail_service:
    def __init__(self):
        logger.info("Inicializando o serviço de envio de e-mails (SMTP Local)...")
        
        # 1. Carrega as variáveis de ambiente do .env
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH", "creds.json")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")
        
        # Configurações do SMTP do Gmail
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

        # 2. Inicializa o serviço do Google Drive diretamente aqui (sem usar o drive_repository antigo)
        try:
            logger.info(f"Carregando credenciais do Drive a partir de: {self.creds_path}")
            # Definimos rigidamente APENAS o escopo de leitura do Drive para evitar rejeições do Google
            drive_scopes = ["https://www.googleapis.com/auth/drive.readonly"]
            
            creds = service_account.Credentials.from_service_account_file(
                self.creds_path, 
                scopes=drive_scopes
            )
            self.drive_service = build("drive", "v3", credentials=creds)
            logger.info("Conexão direta com a API do Google Drive inicializada com sucesso!")
            
        except Exception as e:
            logger.error(f"Falha crítica ao inicializar API do Google Drive no __init__: {str(e)}")
            raise e

        if not self.sender_email or not self.sender_password:
            logger.warning("ATENÇÃO: SENDER_EMAIL ou SENDER_PASSWORD não configurados no .env!")
        else:
            logger.info(f"Remetente SMTP configurado: {self.sender_email}")

    def _criar_copia_do_documento(self, link_arquivo_drive: str) -> bytes:
        logger.info(f"Iniciando tentativa de download do arquivo do Drive. Link: {link_arquivo_drive}")
        try:
            if "file/d/" in link_arquivo_drive:
                file_id = link_arquivo_drive.split("file/d/")[1].split("/")[0]
            elif "id=" in link_arquivo_drive:
                file_id = link_arquivo_drive.split("id=")[1].split("&")[0]
            else:
                file_id = link_arquivo_drive 

            logger.info(f"ID do arquivo extraído com sucesso: {file_id}")

            request = self.drive_service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            
            done = False
            chunk_count = 0
            while not done:
                status, done = downloader.next_chunk()
                chunk_count += 1
                logger.info(f"Progresso do download do Drive - Chunk {chunk_count}: {int(status.progress() * 100)}% concluído.")
                
            logger.info(f"Download concluído com sucesso. Tamanho: {len(file_stream.getvalue())} bytes.")
            return file_stream.getvalue()
            
        except Exception as e:
            logger.error(f"Erro crítico ao tentar baixar o arquivo de ID '{file_id if 'file_id' in locals() else 'Desconhecido'}' no Drive: {str(e)}")
            raise e

    def enviar_email_para_unidade(self, email_unidade: str, link_arquivo_drive: str):
        logger.info(f"===== NOVA REQUISIÇÃO RECEBIDA =====")
        logger.info(f"Destinatário: {email_unidade}")
        
        try:
            # 1. Baixa o arquivo do Google Drive usando a credencial isolada e funcional do Drive
            bytes_pdf = self._criar_copia_do_documento(link_arquivo_drive)

            # 2. Define o corpo em formato HTML
            corpo_html = """
            <html>
                <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                    <h2 style="color: #0056b3;">Agradecimento</h2>
                    <p>Olá,</p>
                    <p>Gostaríamos de agradecer pela recepção e colaboração durante o atendimento realizado em sua unidade escolar.</p>
                    <p>O <strong>Relatório de Serviço Técnico (RST)</strong> referente à visita foi gerado com sucesso, assinado digitalmente e encontra-se <strong>anexado a este e-mail</strong>.</p>
                    <p>Qualquer dúvida ou nova solicitação, estaremos à total disposição para ajudá-los.</p>
                    <br>
                    <p>Atenciosamente,</p>
                    <p><strong>SMECICT</strong><br>
                    Prefeitura Municipal de Saquarema / RJ</p>
                </body>
            </html>
            """

            # 3. Monta a estrutura da mensagem MIME
            logger.info("Construindo a estrutura da mensagem MIME e preparando o anexo PDF...")
            mensagem = MIMEMultipart()
            mensagem["From"] = f"Suporte Técnico SMECICT <{self.sender_email}>"
            mensagem["To"] = email_unidade
            mensagem["Subject"] = "Relatório de Serviço Técnico - SMECICT"

            mensagem.attach(MIMEText(corpo_html, "html"))

            parte_anexo = MIMEApplication(bytes_pdf, _subtype="pdf")
            parte_anexo.add_header(
                "Content-Disposition", 
                "attachment", 
                filename="Relatorio_Servico_Tecnico.pdf"
            )
            mensagem.attach(parte_anexo)
            logger.info("Mensagem MIME montada com sucesso.")

            # 4. Conecta ao SMTP do Gmail usando a Senha de App
            logger.info(f"Iniciando conexão com o servidor SMTP: {self.smtp_server}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                logger.info("Iniciando criptografia segura STARTTLS...")
                server.starttls()
                server.ehlo()
                
                logger.info(f"Autenticando no Gmail SMTP com o usuário: {self.sender_email}...")
                server.login(self.sender_email, self.sender_password)
                logger.info("Autenticação SMTP realizada com sucesso!")
                
                logger.info(f"Disparando e-mail para {email_unidade}...")
                server.sendmail(self.sender_email, email_unidade, mensagem.as_string())
                
            logger.info(f"✅ E-mail enviado com sucesso para {email_unidade}!")
            logger.info(f"=====================================\n")
            return {"status": "E-mail enviado com sucesso!", "sent": True}

        except Exception as e:
            logger.error(f"❌ FALHA CRÍTICA no envio para {email_unidade}: {str(e)}")
            logger.info(f"=====================================\n")
            raise e
