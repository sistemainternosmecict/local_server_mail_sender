import os
import logging
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from modules.smecict_mail_sender import Send_mail_service
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api-logger")
load_dotenv()

app = FastAPI(
    title="SMECICT Email Gateway API",
    servers=[
        {
            "url": "http://sistecserver.chocolate-gamut.ts.net",
            "description": "Production funnel tailscale server",
        }
    ],
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

mail_service = Send_mail_service()

TOKEN_SECRETO = os.getenv("API_LOCAL_TOKEN")

class EmailSchema(BaseModel):
    to: str
    drive_file_url: str

class LogRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        try:
            response = await call_next(request)
            status_code = response.status_code
            log_msg = f"{method} {path} | Status: {status_code}"
            if status_code >= 400:
                logger.error(log_msg)
            else:
                logger.info(log_msg)
            return response
        except Exception as e:
            logger.exception(
                f"FALHA CRÍTICA: {method} {path} | Erro: {str(e)}"
            )
            raise e


app.add_middleware(LogRequestMiddleware)


@app.get("/api/v1/health")
async def index():
    return {"status": "ok"}


@app.post("/")
async def enviar_email(payload: EmailSchema):

    try:
        mail_service.enviar_email_para_unidade(
            email_unidade=payload.to, link_arquivo_drive=payload.drive_file_url
        )
        print(f"✅ E-mail despachado com sucesso para: {payload.to}")
        return {"status": "E-mail enviado com sucesso!", "sent": True}

    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(ve)}
        )
    except Exception as e:
        print(f"❌ Erro crítico no SMTP local: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Erro interno ao processar o disparo do e-mail."},
        )
