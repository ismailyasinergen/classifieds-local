/* SELLER_RESTRICTION_CONDITIONAL_ASSET_V331 */

document.addEventListener("DOMContentLoaded", function () {
    const hrefTokens = [
        "/listings/create",
        "/listings/new",
        "/listings/add",
        "/edit",
        "/delete",
        "/archive",
        "/renew",
        "/promote",
        "/promotions/"
    ];

    const exactActionLabels = [
        "post listing",
        "+ post listing",
        "promote listing",
        "archive",
        "renew",
        "delete",
        "edit"
    ];

    document.querySelectorAll("a, button, input[type='submit']").forEach(function (el) {
        const label = ((el.innerText || el.value || "") + "").trim().toLowerCase();
        const href = ((el.getAttribute("href") || "") + "").toLowerCase();

        const hrefLooksBlocked = hrefTokens.some(function (token) {
            return href.includes(token);
        });

        const labelLooksBlocked = exactActionLabels.includes(label);

        if (hrefLooksBlocked || labelLooksBlocked) {
            el.classList.add("seller-action-disabled");
            el.setAttribute("title", "Seller action disabled because this account is temporarily suspended.");

            if (el.tagName.toLowerCase() === "a") {
                el.removeAttribute("href");
            } else {
                el.disabled = true;
            }
        }
    });
});
