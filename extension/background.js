browser.menus.create({
  id: "repli-knapp",
  title: "🤖 Svara med Repli",
  contexts: ["message_list"]
});

browser.menus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "repli-knapp") {
    let message = info.selectedMessages.messages[0];
    let subject = message.subject; 

    console.log("Skickar till hjärnan...");

    try {
        // Skicka till din Python-server
        let response = await fetch("http://127.0.0.1:8000/skriv-svar", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ text: subject })
        });

        let data = await response.json();

        // Skapa svaret
        await browser.compose.beginReply(message.id, {
            body: data.svar
        });

    } catch (error) {
        console.error("Fel:", error);
    }
  }
});