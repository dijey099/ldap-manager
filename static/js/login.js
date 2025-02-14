document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("login-form").addEventListener("submit", async function(event) {
        event.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;
        const errorMessage = document.getElementById("error-message");

        try {
            const response = await fetch("http://localhost:4444/auth", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: username, password: password })
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.message || "Login failed");
            }

            window.location.href = "/admin";
        } catch (error) {
            errorMessage.textContent = error.message;
            errorMessage.style.display = "block";
            console.error("Error:", error);
        }
    });
});

