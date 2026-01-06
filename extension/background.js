browser.menus.create({
  id: "repli-knapp",
  title: "⚡ Svara med min stil",
  contexts: ["message_list"]
});

browser.menus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "repli-knapp") {
    let messageHeader = info.selectedMessages.messages[0];
    
    // Hämta mailet vi ska svara på
    let fullMessage = await browser.messages.getFull(messageHeader.id);
    let incomingBody = await extractBody(fullMessage);
    let incomingSubject = messageHeader.subject;

    console.log("Letar efter din stil...");

    // 1. Hitta dina tidigare skickade mail (för att lära oss stilen)
    let myStyleSamples = await getSentMailSamples(messageHeader.folder.accountId);
    console.log(`Hittade ${myStyleSamples.length} exempel på din stil.`);

    try {
        // 2. Skicka allt till servern
        let response = await fetch("http://127.0.0.1:8000/skriv-svar", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                subject: incomingSubject,
                body: incomingBody,
                examples: myStyleSamples // <--- NYTT: Skickar med dina gamla mail
            })
        });
        
        let data = await response.json();

        // 3. Hantera klassificering: ska vi svara eller inte?
        if (!data.should_reply) {
            console.log("Ignored newsletter/spam");
            return; // Inget svar skapas
        }

        // should_reply === true: skapa svarsutkast som tidigare
        await browser.compose.beginReply(messageHeader.id, {
            body: data.svar
        });

    } catch (error) {
        console.error("Fel:", error);
    }
  }
});

// --- HJÄLPFUNKTION: Hitta 'Skickat'-mappen och hämta text ---
async function getSentMailSamples(accountId) {
    let account = await browser.accounts.get(accountId);
    let sentExamples = [];

    // Hitta mappen som är av typen "sent" (Skickat)
    // OBS: Folders kan ligga nästlade, men vi kollar toppnivån först
    for (let folder of account.folders) {
        if (folder.type === "sent") {
            // Hämta de 3 senaste meddelandena
            let messages = await browser.messages.list(folder);
            // Vi tar de första i listan (oftast nyast)
            for (let i = 0; i < Math.min(3, messages.messages.length); i++) {
                let msg = messages.messages[i];
                let full = await browser.messages.getFull(msg.id);
                let text = await extractBody(full);
                if (text.length > 50) { // Ignorera jättekorta svar
                    sentExamples.push(text.substring(0, 500)); // Ta max 500 tecken per mail
                }
            }
        }
    }
    return sentExamples;
}

// --- SAMMA SOM FÖRUT: Hitta text i mail ---
async function extractBody(message) {
    if (message.body) return message.body;
    let textPart = null;
    function findTextPart(parts) {
        for (let part of parts) {
            if (part.contentType === "text/plain") return part.body;
            if (part.parts) {
                let found = findTextPart(part.parts);
                if (found) return found;
            }
        }
        return null;
    }
    if (message.parts) textPart = findTextPart(message.parts);
    return textPart || "";
}