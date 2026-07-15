import os
from fastapi import FastAPI, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from modules.smecict_mail_sender import Send_mail_service

load_dotenv()

app = FastAPI(title="SMECICT Email Gateway API")

mail_service = Send_mail_service()

TOKEN_SECRETO = os.getenv("API_LOCAL_TOKEN")

@app.get("/api/v1/health")
async def index():
    return {"status":"ok"}

@app.post("/api/v1/email")
async def enviar_email(
    to: str = Form(...),
	drive_file_url: str = Form(...)
):

    try:
        mail_service.enviar_email_para_unidade(
            email_unidade=to,
            link_arquivo_drive=drive_file_url
        )
        print(f"✅ E-mail despachado com sucesso para: {to}")
        return {"status": "E-mail enviado com sucesso!", "sent":True}

    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(ve)}
        )
    except Exception as e:
        print(f"❌ Erro crítico no SMTP local: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Erro interno ao processar o disparo do e-mail."}
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=5000)
