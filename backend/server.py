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

    # 2. Systeminstruktion med spam/nyhetsbrevsfilter + strikt format- och stilregler
    system_instruktion = (
        "Du är min professionella e-postassistent (Ghostwriter). "
        "Innan du skriver något svar ska du alltid först avgöra "
        "om mailet är ett nyhetsbrev, automatisk notifikation, kvitto eller spam.\n\n"

        "SPAM/NYHETSBREVS-FILTER & OUTPUTFORMAT (MYCKET VIKTIGT):\n"
        "1. Analysera mailtråden (ämne + innehåll) och besvara frågan: \"Är detta mail i första hand ett nyhetsbrev, "
        "automatisk kvitto/bekräftelse, systemnotifikation eller spam, där man normalt inte svarar?\"\n"
        "2. OM SVARET ÄR JA (nyhetsbrev/automatisk notifikation/kvitto/spam/etc.):\n"
        "   - Svara med exakt ordet 'IGNORE' på första raden och inget mer innehåll alls.\n"
        "3. OM SVARET ÄR NEJ (ett personligt eller arbetsrelaterat mail där svar kan förväntas):\n"
        "   - Generera ett svarsutkast enligt reglerna nedan.\n"
        "   - Använd då INTE ordet 'IGNORE' och lägg inte till någon extra förklaring eller metadata.\n\n"

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

        # Om modellen markerar att mailet ska ignoreras (nyhetsbrev/spam/etc.)
        if content.upper().startswith("IGNORE"):
            return {"should_reply": False, "svar": ""}

        # Annars: detta är ett riktigt svarsutkast
        clean_svar = content.replace("Ämne:", "").replace("Subject:", "").strip()
        return {"should_reply": True, "svar": clean_svar}

    except Exception as e:
        print(f"Fel: {e}")
        return {"should_reply": False, "svar": ""}