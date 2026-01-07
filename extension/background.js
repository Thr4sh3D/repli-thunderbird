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
        console.log("AI DECISION:", JSON.stringify(data));

        if (data.should_reply === false) {
            console.log("⛔ STOP: Suppressing window for spam/newsletter.");
            return; // This MUST exit the function immediately to prevent opening a tab.
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

    // Samla alla mappar (inkl. undermappar) rekursivt
    let allFolders = [];
    function collectFolders(folders) {
        if (!folders) return;
        for (let folder of folders) {
            console.log("Checking folder:", folder.name, folder.type);
            allFolders.push(folder);
            if (folder.subFolders && folder.subFolders.length) {
                collectFolders(folder.subFolders);
            }
        }
    }

    collectFolders(account.folders);

    // Vanliga namn för "Skickat"-mappar
    const sentNames = ["Sent", "Skickat", "Sent Items", "Skickade"];

    // Filtrera fram mappar som är av typen "sent" eller har ett matchande namn
    let candidateFolders = allFolders.filter(folder => {
        if (!folder) return false;
        if (folder.type === "sent") return true;
        if (folder.name && sentNames.includes(folder.name)) return true;
        return false;
    });

    // Hämta upp till 3 senaste meddelanden från varje kandidat-mapp
    for (let folder of candidateFolders) {
        try {
            let messagesResult = await browser.messages.list(folder);
            let messages = (messagesResult && messagesResult.messages) ? messagesResult.messages : [];

            for (let i = 0; i < Math.min(3, messages.length); i++) {
                let msg = messages[i];
                let full = await browser.messages.getFull(msg.id);
                let text = await extractBody(full);
                if (text && text.length > 50) { // Ignorera jättekorta svar
                    sentExamples.push(text.substring(0, 500)); // Ta max 500 tecken per mail
                }
            }
        } catch (e) {
            console.warn("Kunde inte läsa meddelanden från mapp", folder.name, e);
        }
    }

    // Fallback: om inga exempel hittades, returnera tom array
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