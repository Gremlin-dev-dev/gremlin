
function bindAuthForm(formId, endpoint) {
    const form = document.getElementById(formId);
    const errorBox = document.getElementById("auth-error");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        errorBox.textContent = "";
        errorBox.classList.remove("visible");

        const payload = {};
        new FormData(form).forEach((value, key) => {
            payload[key] = value;
        });

        const submitBtn = form.querySelector(".auth-submit");
        submitBtn.disabled = true;
        submitBtn.textContent = "Please wait...";

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                errorBox.textContent = data.error || "Something went wrong.";
                errorBox.classList.add("visible");
                submitBtn.disabled = false;
                submitBtn.textContent = formId === "login-form" ? "Log in" : "Sign up";
                return;
            }

            window.location.href = data.redirect || "/";

        } catch (err) {
            errorBox.textContent = "Network error. Please try again.";
            errorBox.classList.add("visible");
            submitBtn.disabled = false;
            submitBtn.textContent = formId === "login-form" ? "Log in" : "Sign up";
        }
    });
}

bindAuthForm("login-form", "/auth/login");
bindAuthForm("signup-form", "/auth/signup");
