console.log("QR Shield JS Loaded");

window.addEventListener("DOMContentLoaded", () => {

    const analyzeBtn = document.getElementById("analyzeBtn");
    const fileInput = document.getElementById("fileInput");
    const loading = document.getElementById("loading");
    const result = document.getElementById("result");

    analyzeBtn.addEventListener("click", async () => {

        if (fileInput.files.length === 0) {
            alert("Please choose a QR image first.");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        loading.innerHTML = "🔍 Analyzing QR Code...";
        result.innerHTML = "";

        try {

            const response = await fetch("/detect", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const data = await response.json();

            loading.innerHTML = "";

            let cardClass;
            let icon;

            switch (data.decision) {

                case "GENUINE":
                    cardClass = "genuine";
                    icon = "✅";
                    break;

                case "UNVERIFIED":
                    cardClass = "unverified";
                    icon = "⚠️";
                    break;

                case "TAMPERED":
                default:
                    cardClass = "tampered";
                    icon = "❌";
                    break;
            }

            result.innerHTML = `
                <div class="report ${cardClass}">

                    <h2>${icon} ${data.decision}</h2>

                    <p class="reason">
                        ${data.reason}
                    </p>

                    <hr>

                    <div class="details">

                        <p>
                            <strong>Merchant</strong><br>
                            ${data.merchant || "-"}
                        </p>

                        <p>
                            <strong>UPI ID</strong><br>
                            ${data.upi || "-"}
                        </p>

                        <p>
                            <strong>Fraud Score</strong><br>
                            ${data.fraud_score}
                        </p>

                    </div>

                </div>
            `;

        }
        catch (err) {

            console.error(err);

            loading.innerHTML = "";

            result.innerHTML = `
                <div class="report error">

                    <h2>⚠️ Connection Error</h2>

                    <p>${err.message}</p>

                </div>
            `;
        }

    });

});