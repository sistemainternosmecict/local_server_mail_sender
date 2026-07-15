import io
import os
import requests
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload
from modules.drive_repository import Drive_repository

load_dotenv()

class Send_mail_service:
    def __init__(self):
        self.drive_repo = Drive_repository()
        self.service = self.drive_repo.obter_service()
        
        # Configurações do Mailgun vindas do seu painel e do .env
        self.mailgun_domain = os.getenv("MAILGUN_DOMAIN", "sandboxb5ffc253cc8f4f5fb497f6a5d40ddc82.mailgun.org")
        self.mailgun_api_key = os.getenv("MAILGUN_API_KEY") # Substitua com sua "API_KEY" real no .env
        self.sender_email = f"Mailgun Sandbox <postmaster@{self.mailgun_domain}>"

    def _criar_copia_do_documento(self, link_arquivo_drive: str) -> bytes:
        try:
            if "file/d/" in link_arquivo_drive:
                file_id = link_arquivo_drive.split("file/d/")[1].split("/")[0]
            elif "id=" in link_arquivo_drive:
                file_id = link_arquivo_drive.split("id=")[1].split("&")[0]
            else:
                file_id = link_arquivo_drive  # Caso já seja o ID puro

            request = self.service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            return file_stream.getvalue()

        except Exception as e:
            print(f"Erro ao baixar o binário correto do arquivo no Drive: {e}")
            raise e

    def enviar_email_para_unidade(self, email_unidade: str, link_arquivo_drive: str):
        try:
            # 1. Baixa o arquivo do Google Drive em formato binário (bytes)
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
            
            print(f"Enviando e-mail via API do Mailgun para {email_unidade}...")
            
            # URL oficial da API do Mailgun para mensagens
            url_api = f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages"
            
            # 3. Dispara a requisição HTTP POST para o Mailgun
            response = requests.post(
                url_api,
                auth=("api", self.mailgun_api_key),
                data={
                    "from": self.sender_email,
                    "to": email_unidade,
                    "subject": "Relatório de Serviço Técnico - SMECICT",
                    "html": corpo_html
                },
                # Enviando o arquivo binário direto na requisição multipart/form-data
                files={
                    "attachment": ("Relatorio_Servico_Tecnico.pdf", bytes_pdf, "application/pdf")
                }
            )
            
            # Verifica se o envio HTTP retornou sucesso (status_code 200)
            if response.status_code == 200:
                print(f"Sucesso: E-mail enviado com sucesso para {email_unidade}, usando API Mailgun!")
                return response.json()
            else:
                raise Exception(f"Erro na API do Mailgun ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"Erro crítico no envio de e-mail: {e}")
            raise e
