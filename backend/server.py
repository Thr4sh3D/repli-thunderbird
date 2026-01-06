import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
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
    examples: List[str] = []

@app.post("/skriv-svar")
async def skriv_svar(data: MailData):
    print(f"Analyserar tråd: {data.subject}")

    # 1. Bygg upp stil-delen separat
    style_section = ""
    if data.examples:
        style_section = "### MIN SKRIVSTIL (HÄRMA DENNA) ###\n"
        for i, ex in enumerate(data.examples):
            # Vi kortar ner exemplen så de inte tar över helt
            snippet = ex[:300].replace("\n", " ") 
            style_section += f"- Exempel {i+1}: {snippet}\n"
        style_section += "###################################\n"

    # 2. Systeminstruktion med klassificering + strikt format- och stilregler
    system_instruktion = (
        "Du är min professionella e-postassistent (Ghostwriter). "
        "Du har TVÅ uppgifter: först avgöra om mailet behöver ett personligt svar, "
        "sedan eventuellt skriva ett svarsutkast åt mig.\n\n"

        "KLASSIFICERING & OUTPUTFORMAT (MYCKET VIKTIGT):\n"
        "1. Analysera mailtråden (ämne + innehåll). Avgör om detta är ett personligt mail "
        "eller en direkt fråga där avsändaren rimligen förväntar sig ett svar, ELLER om det är "
        "ett nyhetsbrev, massutskick, automatisk notifikation, kvitto, bekräftelse, spam eller liknande "
        "där svar normalt inte behövs.\n"
        "2. Om det INTE behöver svar (nyhetsbrev/automatisk notifikation/kvitto/spam/etc.):\n"
        "   - Svara med exakt 'NO_REPLY' på första raden och inget mer innehåll.\n"
        "3. Om det BEHÖVER svar (personligt mail/direkt fråga):\n"
        "   - Skriv enbart själva svarsutkastet enligt reglerna nedan.\n"
        "   - Skriv INTE ordet 'NO_REPLY' i detta fall och lägg inte till någon extra förklaring eller metadata.\n\n"

        "REGLER FÖR INNEHÅLL (VAD DU SKA SKRIVA NÄR SVAR KRÄVS):\n"
        "1. Läs den inkommande mailtråden. Identifiera det SENASTE meddelandet från den andra personen.\n"
        "2. Ignorera all gammal historik, citeringar och mina egna tidigare svar i tråden.\n"
        "3. Ditt svar ska bemöta det senaste meddelandet direkt.\n\n"

        "FORMATREGLER (MYCKET VIKTIGA NÄR DU SKRIVER SVAR):\n"
        "1. SKRIV INTE någon rubrik som börjar med 'Ämne:' eller 'Subject:' i svaret. Börja direkt med själva innehållet.\n"
        "2. SKRIV INTE någon avslutande signatur, hälsningsfras eller namn (t.ex. 'Med vänlig hälsning', 'Mvh', eller mitt namn). "
        "Avsluta istället direkt efter den sista meningen i brödtexten.\n"
        "3. Använd radbrytningar ofta så att texten känns luftig och lätt att läsa, med tydligt separerade stycken.\n"
        "4. Om användarens exempelmail innehåller emojis, använd emojis på ett naturligt sätt i svaret för att spegla tonen.\n\n"

        "REGLER FÖR TONLÄGE (HUR DU SKA SKRIVA NÄR SVAR KRÄVS):\n"
        "1. Använd exemplen nedan för att matcha min ton (formell/informell), mina hälsningsfraser och min meningsbyggnad.\n"
        "2. Skriv på svenska.\n\n"
        f"{style_section}"
    )

    # 3. Vi separerar inkommande data tydligt
    user_prompt = (
        f"ÄMNE: {data.subject}\n\n"
        f"--- INKOMMANDE MAILTRÅD (BÖRJA LÄSA HÄR) ---\n"
        f"{data.body}\n"
        f"--- SLUT PÅ TRÅD ---\n\n"
        f"UPPGIFT: Skriv ett svar på det senaste meddelandet i tråden ovan, i min stil."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Byt till "gpt-4o" om du vill ha den ännu smartare på att fatta trådar
            messages=[
                {"role": "system", "content": system_instruktion},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6 # Lite lägre temperatur för att den ska hålla sig till stilen
        )
        raw_svar = response.choices[0].message.content if response.choices else ""
        content = (raw_svar or "").lstrip()

        # Om modellen markerar att inget svar behövs
        if content.upper().startswith("NO_REPLY"):
            return {"should_reply": False, "svar": ""}

        # Annars: detta är ett riktigt svarsutkast
        clean_svar = content.replace("Ämne:", "").replace("Subject:", "").strip()
        return {"should_reply": True, "svar": clean_svar}

    except Exception as e:
        print(f"Fel: {e}")
        return {"should_reply": False, "svar": ""}