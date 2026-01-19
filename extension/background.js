browser.menus.create({
  id: "repli-knapp",
  title: "⚡ Svara med min stil",
  contexts: ["message_list"]
});

browser.menus.onClicked.addListener(async (info, tab) => {
    console.log("🔥 REPLI BUTTON CLICKED!");
    if (info.menuItemId === "repli-knapp") {
    let messageHeader = info.selectedMessages.messages[0];
    await processEmail(messageHeader, false);
  }
});

// Autopilot: lyssna i bakgrunden på nya mail
browser.messages.onNewMailReceived.addListener(async (folder, messages) => {
    if (!messages || !messages.messages || !messages.messages.length) return;

    console.log("📨 AUTOPILOT: New mail detected in folder:", folder && folder.name);

    for (let messageHeader of messages.messages) {
        try {
            await processEmail(messageHeader, true);
        } catch (error) {
            console.error("Autopilot error:", error);
        }
    }
});

// --- KÄRNLOGIK: bearbeta ett mail (manuellt eller autopilot) ---
async function processEmail(messageHeader, isAutopilot) {
    // Hämta mailet vi ska svara på
    let fullMessage = await browser.messages.getFull(messageHeader.id);
    let incomingBody = await extractBody(fullMessage);
    let incomingSubject = messageHeader.subject;

    // 1. Hitta din "Skickat"-mapp (över alla konton) och läs exempel därifrån
    const accounts = await messenger.accounts.list();
    let sentFolder = null;

    for (let account of accounts) {
        if (!account || !account.folders) continue;
        let found = traverse(account.folders);
        if (found) {
            sentFolder = found;
            break;
        }
    }

    let myStyleSamples = [];
    if (sentFolder) {
        myStyleSamples = await getSentMailSamples(sentFolder);
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
                examples: myStyleSamples
            })
        });
        
        let data = await response.json();
        console.log("AI DECISION:", JSON.stringify(data));

        if (data.should_reply === false) {
            console.log("Ignored spam");
            return;
        }

        if (isAutopilot) {
            // Autopilot: markera mailet och skicka notis istället för att öppna fönster
            try {
                if (browser.messages.update) {
                    await browser.messages.update(messageHeader.id, { tags: ["$label1"] });
                    console.log("✅ TAG APPLIED SUCCESS!");
                } else {
                    console.error("⚠️ PERMISSION MISSING: Cannot tag message. 'messagesModify' permission might be inactive.");
                }

                const sender = messageHeader.author || "okänd avsändare";
                await browser.notifications.create({
                    type: "basic",
                    title: "Repli: Important email detected",
                    message: `Important email detected from ${sender}`
                });
            } catch (e) {
                console.error("Autopilot tag/notification error:", e);
            }
        } else {
            // Manuell: öppna utkast i skrivfönster
            await browser.compose.beginReply(messageHeader.id, {
                body: data.svar
            });
        }

    } catch (error) {
        console.error("Fel:", error);
    }
}

// --- HJÄLPFUNKTION: Traversera alla mappar rekursivt och hitta "Skickat" ---
function traverse(folders) {
    if (!folders) return null;

    for (let folder of folders) {
        if (!folder) continue;

        const name = folder.name || "(no name)";
        const type = folder.type || "(no type)";
        const subCount = (folder.subFolders && folder.subFolders.length) ? folder.subFolders.length : 0;

        // Försök hitta "Skickat"-mapp baserat på typ eller namn
        if (folder.type === "sent" || name === "Sent" || name === "Skickat") {
            return folder;
        }

        if (folder.subFolders && folder.subFolders.length) {
            let found = traverse(folder.subFolders);
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

        for (let i = 0; i < Math.min(15, messages.length); i++) {
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