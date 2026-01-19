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

    # 2. Systeminstruktion med tydliga faser: filter, språk och formatering
    system_instruktion = (
        "PHASE 1: FILTER (CRITICAL)\n"
        "Analysera hela mailtråden (ämne + innehåll). Avgör om detta framför allt är ett nyhetsbrev, en automatisk notifikation, ett kvitto, en systempåminnelse, spam eller ett 'no-reply'-meddelande där man normalt inte svarar.\n"
        "Om SVARET ÄR JA: Svara med exakt ordet 'IGNORE' och ABSOLUT INGENTING MER. Ingen extra text, ingen förklaring, inget utkast.\n"
        "Om SVARET ÄR NEJ (ett personligt eller arbetsrelaterat mail där svar kan förväntas): Fortsätt till PHASE 2 och PHASE 3 och skriv ett svarsutkast. Använd då INTE ordet 'IGNORE'.\n\n"

        "PHASE 2: LANGUAGE (CRITICAL)\n"
        "Identifiera vilket språk den inkommande mailtråden huvudsakligen är skriven på.\n"
        "Du MÅSTE skriva svarsutkastet på EXAKT SAMMA SPRÅK som inkommande mail.\n"
        "Om mailet är på engelska, svara på engelska. Om mailet är på svenska, svara på svenska. Om mailet är på ett annat enskilt språk, svara på det språket.\n"
        "Översätt inte innehållet till ett annat språk än det som används i mailet.\n\n"

        "PHASE 3: FORMATTING (CRITICAL)\n"
        "Skriv svaret med MYCKET korta stycken (max 2–3 meningar per stycke).\n"
        "DU MÅSTE använda DUBBLA RADBRYTNINGAR (\\n\\n) mellan varje stycke så att mailet ser luftigt och lättläst ut.\n"
        "Om du listar saker eller steg, använd alltid punktlista eller streck (t.ex. '- ' i början av raden).\n"
        "Skriv INGEN ämnesrad och inga rubriker eller metadata som 'Subject:' eller 'Ämne:'. Börja direkt med brödtexten.\n"
        "Skriv INGEN signatur eller avslutningshälsning med namn (t.ex. 'Best regards', 'Med vänlig hälsning', 'Mvh' eller mitt namn). Thunderbird lägger till detta själv.\n"
        "Avsluta direkt efter den sista meningen i själva brödtexten.\n\n"

        "INNEHÅLLSREGLER (CONTENT):\n"
        "1. Läs den inkommande mailtråden och identifiera det SENASTE meddelandet från den andra personen.\n"
        "2. Ignorera så långt som möjligt gammal historik, citerade delar och mina egna tidigare svar i tråden.\n"
        "3. Ditt svar ska bemöta det senaste meddelandet direkt och tydligt.\n\n"

        "STIL OCH TON (STYLE AND TONE):\n"
        "Använd exempelmailen nedan (om de finns) för att efterlikna min ton (formell/informell), mina hälsningsfraser och min meningsbyggnad.\n"
        "Om användarens exempelmail innehåller emojis, använd emojis på ett naturligt sätt i svaret för att spegla den stilen.\n\n"
        f"{style_section}"
    )

    # 3. Begränsa trådens längd för att undvika token-problem
    truncated_body = data.body[:15000]
    if len(data.body) > 15000:
        print("Thread too long, truncated to 15k chars.")

    # 4. Vi separerar inkommande data tydligt
    user_prompt = (
        f"ÄMNE: {data.subject}\n\n"
        f"--- INKOMMANDE MAILTRÅD (BÖRJA LÄSA HÄR) ---\n"
        f"{truncated_body}\n"
        f"--- SLUT PÅ TRÅD ---\n\n"
        f"UPPGIFT: Skriv ett svar på det senaste meddelandet i tråden ovan, i min stil.\n\n"
        "FORMAT: Använd mycket korta stycken (max 2–3 meningar per stycke), \n"
        "använd ALLTID dubbla radbrytningar mellan stycken så att mailet blir luftigt, \n"
        "använd punktlista eller streck när du listar saker (t.ex. '- '), och skriv ingen rubrik, \n"
        "ingen ämnesrad och ingen signatur eller avslutningshälsning (Thunderbird lägger till detta själv)."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruktion},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4
        )
        content = response.choices[0].message.content if response.choices else ""
        ai_raw = (content or "").strip()

        # Strikt spam-/nyhetsbrevsdetektion baserat på IGNORE-taggen
        if "IGNORE" in ai_raw.upper():
            print("FILTER: BLOCKING SPAM")
            return {"should_reply": False, "svar": ""}

        # Annars: detta är ett riktigt svarsutkast
        # För att Thunderbird inte ska svälja enkla radbrytningar (använd Windows CRLF + extra rad)
        final_svar = ai_raw.replace("\n", "\r\n\r\n")
        print(f"DEBUG FORMAT: {repr(final_svar[:100])}")
        print("FILTER: ALLOWING REPLY")
        return {"should_reply": True, "svar": final_svar}

    except Exception as e:
        print(f"Fel: {e}")
        return {"should_reply": False, "svar": ""}