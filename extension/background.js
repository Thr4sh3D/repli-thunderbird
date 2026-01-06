browser.menus.create({
  id: "repli-knapp",
  title: "🤖 Svara med Repli",
  contexts: ["message_list"]
});

browser.menus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "repli-knapp") {
    let messageHeader = info.selectedMessages.messages[0];
    
    // 1. Hämta hela mailet
    let fullMessage = await browser.messages.getFull(messageHeader.id);
    
    // 2. Använd min hjälpfunktion för att hitta texten (se längst ner)
    let bodyText = await extractBody(fullMessage);
    let subjectText = messageHeader.subject;

    console.log("Skickar ämne:", subjectText);
    // console.log("Skickar text:", bodyText); // Avkommentera om du vill se texten i loggen

    try {
        let response = await fetch("http://127.0.0.1:8000/skriv-svar", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            // UPPDATERING: Skickar nu både subject och body
            body: JSON.stringify({ 
                subject: subjectText,
                body: bodyText
            })
        });
        
        let data = await response.json();

        await browser.compose.beginReply(messageHeader.id, {
            body: data.svar
        });

    } catch (error) {
        console.error("Fel:", error);
    }
  }
});

// --- HJÄLPFUNKTION FÖR ATT HITTA TEXTEN I ETT MAIL ---
async function extractBody(message) {
    // Om mailet bara är enkel text
    if (message.body) {
        return message.body;
    }
    
    // Om mailet har delar (HTML/Text), leta rekursivt
    let textPart = null;
    
    function findTextPart(parts) {
        for (let part of parts) {
            if (part.contentType === "text/plain") {
                return part.body;
            }
            if (part.parts) {
                let found = findTextPart(part.parts);
                if (found) return found;
            }
        }
        return null;
    }

    if (message.parts) {
        textPart = findTextPart(message.parts);
    }
    
    // Om vi inte hittar ren text, ta vad som finns (ofta HTML)
    return textPart || "Kunde inte läsa mailets innehåll.";
}