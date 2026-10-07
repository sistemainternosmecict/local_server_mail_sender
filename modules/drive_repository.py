import os, json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class Drive_repository:
    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/gmail.send"
    ]

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
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
            if not creds_path or not os.path.exists(creds_path):
                raise FileNotFoundError(f"Arquivo de credenciais não encontrado localmente em: {creds_path}")
            self.service = self._autenticar(creds_path)
            print(f"Sucesso: Autenticado no Google Drive usando o arquivo local: {creds_path}")

    def _autenticar(self, creds_path: str):
        usuario_alvo = "cpd.educacao@smec.saquarema.rj.gov.br"
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=self.SCOPES
        ).with_subject(usuario_alvo)
        return build('drive', 'v3', credentials=creds)

    def _autenticar_por_dict(self, info_dict: dict):
        usuario_alvo = "cpd.educacao@smec.saquarema.rj.gov.br"
        creds = service_account.Credentials.from_service_account_info(
            info_dict,
            scopes=self.SCOPES
        ).with_subject(usuario_alvo)
        return build('drive', 'v3', credentials=creds)

    def obter_service(self):
        return self.service
