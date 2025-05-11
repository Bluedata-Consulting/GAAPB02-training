const chat = document.getElementById("chat");
const form = document.getElementById("form");
const msg  = document.getElementById("msg");

function addBubble(text, you) {
  const div   = document.createElement("div");
  div.className = `p-2 my-1 rounded ${you ? "bg-primary text-white" : "bg-secondary bg-opacity-10"}`;
  if (you){
    div.textContent = text;
  } else {
    const html = DOMPurify.sanitize(marked.parse(text));
    div.innerHTML = html;
  }
 
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener("submit", async e => {
  e.preventDefault();
  if (!msg.value.trim()) return;
  addBubble(msg.value, true);
  const q = msg.value;
  msg.value = "";

  const r = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: q })
  });
  const j = await r.json();
  addBubble(j.answer, false);
});
