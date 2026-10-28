/* Contact page: the original browser-side checks. If everything is fine the
   form is now really submitted to Django (the original only showed an alert). */
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("contact-form");
    if (!form) { return; }

    form.addEventListener("submit", function (event) {
        var name = form.querySelector('[name="name"]').value.trim();
        var email = form.querySelector('[name="email"]').value.trim();
        var message = form.querySelector('[name="message"]').value.trim();

        if (name === "" || email === "" || message === "") {
            event.preventDefault();
            alert("Please fill in all the fields.");
            return;
        }

        var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email)) {
            event.preventDefault();
            alert("Please enter a valid email address.");
        }
    });
});
