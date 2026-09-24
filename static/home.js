const NAME_KEY = "ncv-name";

const nameInput = document.getElementById("name");
const errorText = document.getElementById("home-error");

function loadName() {
  try {
    return localStorage.getItem(NAME_KEY) || "";
  } catch {
    return "";
  }
}

function saveName(name) {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    return;
  }
}

function requireName() {
  const name = nameInput.value.trim();
  if (!name) {
    errorText.textContent = "Enter your name first.";
    nameInput.focus();
    return null;
  }
  saveName(name);
  return name;
}

function goToRoom(code, name) {
  window.location.href = `/room/${code}?name=${encodeURIComponent(name)}`;
}

nameInput.value = loadName();

document.getElementById("create").addEventListener("click", async () => {
  const name = requireName();
  if (!name) return;
  try {
    const response = await fetch("/api/rooms", { method: "POST" });
    if (!response.ok) throw new Error(`server returned ${response.status}`);
    const { code } = await response.json();
    goToRoom(code, name);
  } catch (error) {
    console.error(error);
    errorText.textContent = "Couldn't create a room. Is the server still running?";
  }
});

document.getElementById("join-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = requireName();
  if (!name) return;
  const code = document.getElementById("join-code").value.trim().toUpperCase();
  if (code.length !== 4) {
    errorText.textContent = "Room codes are 4 letters.";
    return;
  }
  try {
    const response = await fetch(`/api/rooms/${code}`);
    if (response.status === 404) {
      errorText.textContent = `There's no room ${code}. Check the code with whoever made it.`;
      return;
    }
    if (!response.ok) throw new Error(`server returned ${response.status}`);
    goToRoom(code, name);
  } catch (error) {
    console.error(error);
    errorText.textContent = "Couldn't reach the server. Is it still running?";
  }
});
