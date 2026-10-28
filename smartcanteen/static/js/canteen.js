/* Shared JavaScript for the Smart Canteen pages.
   - Qty + / - buttons          (increaseQty / decreaseQty were in the original pages)
   - "Add to cart" buttons      (now saved on the server instead of localStorage)
   - closing the flash messages
*/

var MAX_QTY = 20;

function increaseQty(button) {
    var input = button.parentElement.querySelector(".qty-input");
    var value = parseInt(input.value, 10);
    if (isNaN(value) || value < 1) { value = 1; }
    if (value < MAX_QTY) { input.value = value + 1; }
}

function decreaseQty(button) {
    var input = button.parentElement.querySelector(".qty-input");
    var value = parseInt(input.value, 10);
    if (!isNaN(value) && value > 1) {
        input.value = value - 1;
    } else {
        input.value = 1;
    }
}

document.addEventListener("DOMContentLoaded", function () {

    // ---- Add to cart -------------------------------------------------------
    document.querySelectorAll(".add-to-cart").forEach(function (button) {
        button.addEventListener("click", function () {
            var card = button.parentElement;
            var qtyInput = card.querySelector(".qty-input");
            var qty = parseInt(qtyInput.value, 10);

            if (isNaN(qty) || qty < 1 || qty > MAX_QTY) {
                alert("Please enter a quantity between 1 and " + MAX_QTY + ".");
                qtyInput.value = 1;
                return;
            }

            button.disabled = true;
            fetch(window.CANTEEN.addUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": window.CANTEEN.csrfToken
                },
                credentials: "same-origin",
                body: JSON.stringify({ item_id: button.dataset.itemId, quantity: qty })
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { status: response.status, data: data };
                    });
                })
                .then(function (result) {
                    if (result.status === 401) {
                        window.location.href = window.CANTEEN.loginUrl + "?next=" +
                            encodeURIComponent(window.location.pathname);
                        return;
                    }
                    alert(result.data.message);
                    if (result.data.ok) {
                        var badge = document.getElementById("cn-cart-count");
                        if (badge) { badge.textContent = result.data.cart_count; }
                    }
                })
                .catch(function () {
                    alert("Could not reach the server. Please try again.");
                })
                .finally(function () {
                    button.disabled = false;
                });
        });
    });

    // ---- Flash messages: close button + auto-hide ---------------------------
    document.querySelectorAll(".cn-message").forEach(function (box) {
        var close = box.querySelector(".cn-close");
        if (close) { close.addEventListener("click", function () { box.remove(); }); }
        setTimeout(function () { box.remove(); }, 8000);
    });
});
