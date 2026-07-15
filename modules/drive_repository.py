import os, json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class Drive_repository:
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        url_base = os.getenv("URL_BASE", "http://localhost:8000")
        creds_conteudo_render = os.getenv("CREDS")
        if creds_conteudo_render and "localhost" not in url_base:
            try:
                info_dict = json.loads(creds_conteudo_render)
                if "private_key" in info_dict:
                    info_dict["private_key"] = info_dict["private_key"].replace("\\n", "\n")
                self.service = self._autenticar_por_dict(info_dict)
                print("Sucesso: Autenticado no Google Drive via variável de ambiente (Render)")
            except json.JSONDecodeError as e:
                raise ValueError(f"Erro ao decodificar a string da variável 'CREDS' no Render: {e}")
        else:
            creds_path = os.getenv("SERVICE_ACCOUNT_PATH")
            if not creds_path or not os.path.exists(creds_path):
                raise FileNotFoundError(f"Arquivo de credenciais não encontrado localmente em: {creds_path}")
            self.service = self._autenticar(creds_path)
            print(f"Sucesso: Autenticado no Google Drive usando o arquivo local: {creds_path}")

    def _autenticar(self, creds_path: str):
        usuario_alvo = "thyezoliveiramonteiro@smec.saquarema.rj.gov.br"
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=self.SCOPES
        ).with_subject(usuario_alvo)
        return build('drive', 'v3', credentials=creds)

    def _autenticar_por_dict(self, info_dict: dict):
        usuario_alvo = "thyezoliveiramonteiro@smec.saquarema.rj.gov.br"
        creds = service_account.Credentials.from_service_account_info(
            info_dict,
            scopes=self.SCOPES
        ).with_subject(usuario_alvo)
        return build('drive', 'v3', credentials=creds)

    def salvar_arquivo_drive(self, arquivo_pdf: str, drive_dir_id: str) -> str:
        try:
            nome_arquivo = os.path.basename(arquivo_pdf)
            file_metadata = {
                'name': nome_arquivo,
                'parents': [drive_dir_id]
            }
            media = MediaFileUpload(
                arquivo_pdf,
                mimetype='application/pdf',
                resumable=True
            )
            arquivo_drive = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            link_visualizacao = arquivo_drive.get('webViewLink')
            return link_visualizacao
        except Exception as error:
            print(f"Ocorreu um erro ao fazer upload para o Google Drive: {error}")
            raise error

    def obter_service(self):
        return self.service
