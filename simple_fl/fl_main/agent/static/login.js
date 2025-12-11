// Get location & store in form + session
navigator.geolocation.getCurrentPosition(
    pos => {
        const loc = pos.coords.latitude + "," + pos.coords.longitude;

        // fill hidden input
        document.getElementById("locationField").value = loc;

        // send to session for google login
        fetch("/save_location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location: loc })
        });
    },
    err => {
        document.getElementById("locationField").value = "unknown";

        fetch("/save_location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location: "unknown" })
        });
    }
);

// handle login/register toggle
function setactionform(action) {
    let form = document.getElementById('auth_form');

    if (action === 'login') {
        form.action = "/login";
        form.method = "POST";
        form.submit();
    } else {
        form.action = "/register";
        form.method = "POST";
        form.submit();
    }
}

// google login redirect
document.getElementById("googleBtn").onclick = function () {
    window.location.href = "/login/google";
};
