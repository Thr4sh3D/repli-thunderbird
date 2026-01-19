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

    // 1. Hitta din "Skickat"-mapp (över alla konton) och läs exempel därifrån
    let accounts = await browser.accounts.list();
    let sentFolder = null;

    for (let account of accounts) {
        if (!account || !account.folders) continue;
        let found = findSentFolder(account.folders);
        if (found) {
            sentFolder = found;
            break;
        }
    }

    let myStyleSamples = [];
    if (sentFolder) {
        console.log("Found Sent folder:", sentFolder.name);
        myStyleSamples = await getSentMailSamples(sentFolder);
    } else {
        console.log("No Sent folder found");
    }

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

// --- HJÄLPFUNKTION: Hitta "Skickat"-mapp rekursivt + logga allt ---
function findSentFolder(folders) {
    if (!folders) return null;

    for (let folder of folders) {
        if (!folder) continue;

        const name = folder.name || "(no name)";
        const type = folder.type || "(no type)";
        const subCount = (folder.subFolders && folder.subFolders.length) ? folder.subFolders.length : 0;

        console.log("SCANNING:", name, "| Type:", type, "| Subfolders:", subCount);

        // Bred sökning på namn och typ
        if (folder.type === "sent") {
            return folder;
        }

        if (folder.name) {
            const lower = folder.name.toLowerCase();
            if (
                lower.includes("sent") ||
                lower.includes("skickat") ||
                lower.includes("outbox") ||
                lower.includes("items")
            ) {
                return folder;
            }
        }

        if (folder.subFolders && folder.subFolders.length) {
            let found = findSentFolder(folder.subFolders);
            if (found) return found;
        }
    }

    return null;
}

// --- HJÄLPFUNKTION: Hämta exempel från en given "Skickat"-mapp ---
async function getSentMailSamples(sentFolder) {
    if (!sentFolder) return [];

    let sentExamples = [];

    try {
        let messagesResult = await browser.messages.list(sentFolder);
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
        console.warn("Kunde inte läsa meddelanden från mapp", sentFolder.name, e);
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