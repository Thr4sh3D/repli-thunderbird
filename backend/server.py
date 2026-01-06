from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <--- Ny import
from pydantic import BaseModel

app = FastAPI()

# --- HÄR ÄR NYA SÄKERHETSKODEN ---
# Vi säger åt servern att tillåta trafik från alla håll (för utveckling)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" betyder "alla får komma in"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------

class MailData(BaseModel):
    text: str

@app.post("/skriv-svar")
async def skriv_svar(data: MailData):
    print("Jag fick ett mail!")
    svar = f"Hej! Tack för ditt mail om '{data.text}'. Detta är ett autosvar från Repli."
    return {"svar": svar}