import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MailData(BaseModel):
    subject: str
    body: str

@app.post("/skriv-svar")
async def skriv_svar(data: MailData):
    print(f"Analyserar tråd: {data.subject}")

    try:
        # Här är magin: En "Context-Aware" instruktion
        system_instruktion = (
            "Du är en professionell 'Ghostwriter' för e-post. "
            "Här är din uppgift:\n"
            "1. ANALYSERA KONTEXTEN: Läs igenom hela mailtråden nedan för att förstå vad diskussionen handlar om och vad som bestämts tidigare.\n"
            "2. AGERA PÅ DET SENASTE: Ditt svarsutkast ska ENDAST bemöta det absolut senaste meddelandet i tråden.\n"
            "3. TONLÄGE: Skriv naturligt, professionellt och rakt på sak. Låtsas vara jag.\n"
            "4. FÖRBJUDET: Du får INTE inleda med fraser som 'Baserat på konversationen...' och du ska INTE sammanfatta vad som sagts tidigare. "
            "Skriv bara svaret, precis som om jag hade skrivit det själv nu direkt."
        )

        # Vi tydliggör för AI:n vad som är vad
        user_prompt = (
            f"ÄMNE: {data.subject}\n\n"
            f"--- HELA MAILTRÅDEN BÖRJAR HÄR ---\n"
            f"{data.body}\n"
            f"--- SLUT PÅ TRÅDEN ---\n\n"
            f"Uppgift: Skriv mitt svarsutkast på svenska."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Byt till "gpt-4o" för ännu bättre läsförståelse
            messages=[
                {"role": "system", "content": system_instruktion},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7 
        )
        
        ai_svar = response.choices[0].message.content
        return {"svar": ai_svar}

    except Exception as e:
        print(f"Fel: {e}")
        return {"svar": "Kunde inte generera svar."}