/* LISTING_DETAIL_JAVASCRIPT_STATIC_ASSET_V327 */
(function () {
    const fallbackImagesV325 = document.querySelectorAll(
        "[data-listing-image-fallback-v325]"
    );

    fallbackImagesV325.forEach(function (image) {
        function replaceFailedImageV325() {
            if (!image.parentNode) {
                return;
            }

            const fallback = document.createElement("div");
            fallback.className = (
                image.dataset.listingImageFallbackV325
            );
            fallback.textContent = "No image";
            image.replaceWith(fallback);
        }

        image.addEventListener(
            "error",
            replaceFailedImageV325,
            { once: true }
        );

        if (image.complete && image.naturalWidth === 0) {
            replaceFailedImageV325();
        }
    });

    const mainImage = document.getElementById("classified-main-image");
    const counter = document.getElementById("gallery-counter");
    const prevButton = document.getElementById("gallery-prev");
    const nextButton = document.getElementById("gallery-next");
    const thumbnails = Array.from(document.querySelectorAll(".classified-thumb-button"));

    if (!mainImage || !thumbnails.length) {
        return;
    }

    let currentIndex = 0;

    function showImage(index) {
        if (!thumbnails.length) {
            return;
        }

        currentIndex = (index + thumbnails.length) % thumbnails.length;
        const selected = thumbnails[currentIndex];

        mainImage.src = selected.dataset.gallerySrc;
        mainImage.alt = selected.dataset.galleryAlt || mainImage.alt;

        thumbnails.forEach(function (button, buttonIndex) {
            const isActive = buttonIndex === currentIndex;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        if (counter) {
            counter.textContent = `${currentIndex + 1} / ${thumbnails.length}`;
        }
    }

    thumbnails.forEach(function (button, index) {
        button.addEventListener("click", function () {
            showImage(index);
        });
    });

    if (prevButton) {
        prevButton.addEventListener("click", function () {
            showImage(currentIndex - 1);
        });
    }

    if (nextButton) {
        nextButton.addEventListener("click", function () {
            showImage(currentIndex + 1);
        });
    }

    showImage(0);
})();

(function () {
    const mainImage = document.getElementById(
        "classified-main-image"
    );
    const lightbox = document.getElementById(
        "listing-gallery-lightbox-v318"
    );
    const lightboxImage = document.getElementById(
        "listing-gallery-lightbox-image-v318"
    );
    const lightboxCounter = document.getElementById(
        "listing-gallery-lightbox-counter-v318"
    );
    const closeButton = document.querySelector(
        "[data-gallery-lightbox-close-v318]"
    );
    const previousButton = document.querySelector(
        "[data-gallery-lightbox-prev-v318]"
    );
    const nextButton = document.querySelector(
        "[data-gallery-lightbox-next-v318]"
    );
    const thumbnails = Array.from(
        document.querySelectorAll(
            ".classified-thumb-button"
        )
    );
    const focusableControls = [
        closeButton,
        previousButton,
        nextButton,
    ].filter(Boolean);

    if (
        !mainImage
        || !lightbox
        || !lightboxImage
        || !thumbnails.length
    ) {
        return;
    }

    let activeIndex = 0;
    let restoreFocusNode = null;

    function normalizedIndex(index) {
        return (
            index + thumbnails.length
        ) % thumbnails.length;
    }

    function selectedIndex() {
        const foundIndex = thumbnails.findIndex(
            function (button) {
                return button.classList.contains(
                    "is-active"
                );
            }
        );

        return foundIndex >= 0
            ? foundIndex
            : 0;
    }

    function showLightboxImage(index) {
        activeIndex = normalizedIndex(index);

        const selected = thumbnails[activeIndex];

        selected.click();

        lightboxImage.src = selected.dataset.gallerySrc;
        lightboxImage.alt = (
            selected.dataset.galleryAlt
            || mainImage.alt
        );

        if (lightboxCounter) {
            lightboxCounter.textContent = (
                `${activeIndex + 1} / ${thumbnails.length}`
            );
        }
    }

    function openLightbox() {
        restoreFocusNode = document.activeElement;
        showLightboxImage(selectedIndex());

        if (
            typeof lightbox.showModal === "function"
        ) {
            lightbox.showModal();
        } else {
            lightbox.setAttribute("open", "");
        }

        document.body.classList.add(
            "listing-gallery-lightbox-open-v318"
        );

        if (closeButton) {
            closeButton.focus();
        }
    }

    function closeLightbox() {
        if (
            typeof lightbox.close === "function"
            && lightbox.open
        ) {
            lightbox.close();
        } else {
            lightbox.removeAttribute("open");
        }

        document.body.classList.remove(
            "listing-gallery-lightbox-open-v318"
        );

        if (
            restoreFocusNode
            && typeof restoreFocusNode.focus === "function"
        ) {
            restoreFocusNode.focus();
        }
    }

    mainImage.addEventListener(
        "click",
        openLightbox
    );

    mainImage.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key === "Enter"
                || event.key === " "
            ) {
                event.preventDefault();
                openLightbox();
            }
        }
    );

    if (previousButton) {
        previousButton.addEventListener(
            "click",
            function () {
                showLightboxImage(activeIndex - 1);
            }
        );
    }

    if (nextButton) {
        nextButton.addEventListener(
            "click",
            function () {
                showLightboxImage(activeIndex + 1);
            }
        );
    }

    if (closeButton) {
        closeButton.addEventListener(
            "click",
            closeLightbox
        );
    }

    lightbox.addEventListener(
        "click",
        function (event) {
            if (event.target === lightbox) {
                closeLightbox();
            }
        }
    );

    lightbox.addEventListener(
        "cancel",
        function (event) {
            event.preventDefault();
            closeLightbox();
        }
    );

    lightbox.addEventListener(
        "keydown",
        function (event) {
            if (event.key === "Escape") {
                event.preventDefault();
                closeLightbox();
                return;
            }

            if (
                event.key === "Tab"
                && focusableControls.length
            ) {
                const firstControl = focusableControls[0];
                const lastControl = focusableControls[
                    focusableControls.length - 1
                ];

                if (
                    event.shiftKey
                    && document.activeElement === firstControl
                ) {
                    event.preventDefault();
                    lastControl.focus();
                } else if (
                    !event.shiftKey
                    && document.activeElement === lastControl
                ) {
                    event.preventDefault();
                    firstControl.focus();
                }
            }

            if (event.key === "ArrowLeft") {
                event.preventDefault();
                showLightboxImage(activeIndex - 1);
            }

            if (event.key === "ArrowRight") {
                event.preventDefault();
                showLightboxImage(activeIndex + 1);
            }
        }
    );

    lightbox.addEventListener(
        "close",
        function () {
            document.body.classList.remove(
                "listing-gallery-lightbox-open-v318"
            );
        }
    );
}());

(function () {
    const copyButton = document.querySelector(
        "[data-listing-location-copy-v319]"
    );
    const statusNode = document.querySelector(
        "[data-listing-location-status-v319]"
    );

    if (!copyButton) {
        return;
    }

    function announceLocationAction(message) {
        if (!statusNode) {
            return;
        }

        statusNode.textContent = message;

        window.setTimeout(function () {
            statusNode.textContent = "";
        }, 3500);
    }

    function fallbackCopyLocation(value) {
        const textarea = document.createElement(
            "textarea"
        );

        textarea.value = value;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);
        textarea.select();

        const copied = document.execCommand("copy");

        document.body.removeChild(textarea);

        return copied;
    }

    function copyLocation(value) {
        if (
            navigator.clipboard
            && navigator.clipboard.writeText
        ) {
            navigator.clipboard.writeText(value).then(
                function () {
                    announceLocationAction(
                        "Location copied."
                    );
                },
                function () {
                    if (fallbackCopyLocation(value)) {
                        announceLocationAction(
                            "Location copied."
                        );
                    } else {
                        announceLocationAction(
                            "Location could not be copied."
                        );
                    }
                }
            );

            return;
        }

        if (fallbackCopyLocation(value)) {
            announceLocationAction(
                "Location copied."
            );
        } else {
            announceLocationAction(
                "Location could not be copied."
            );
        }
    }

    copyButton.addEventListener(
        "click",
        function () {
            const locationValue = (
                copyButton.dataset
                    .listingLocationV319
                || ""
            ).trim();

            if (!locationValue) {
                announceLocationAction(
                    "Location is unavailable."
                );
                return;
            }

            copyLocation(locationValue);
        }
    );
}());

(function () {
    const shareButtons = Array.from(
        document.querySelectorAll(
            "[data-listing-share-v317]"
        )
    );
    const printButton = document.querySelector(
        "[data-listing-print-v317]"
    );
    const statusNode = document.querySelector(
        "[data-listing-action-status-v317]"
    );

    function announce(message) {
        if (!statusNode) {
            return;
        }

        statusNode.textContent = message;

        window.setTimeout(function () {
            statusNode.textContent = "";
        }, 3500);
    }

    function fallbackCopy(value) {
        const textarea = document.createElement("textarea");

        textarea.value = value;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);
        textarea.select();

        const copied = document.execCommand("copy");

        document.body.removeChild(textarea);

        return copied;
    }

    function copyListingUrl() {
        const listingUrl = window.location.href;

        if (
            navigator.clipboard
            && navigator.clipboard.writeText
        ) {
            navigator.clipboard.writeText(listingUrl).then(
                function () {
                    announce("Listing link copied.");
                },
                function () {
                    if (fallbackCopy(listingUrl)) {
                        announce("Listing link copied.");
                    } else {
                        announce(
                            "Listing link could not be copied."
                        );
                    }
                }
            );

            return;
        }

        if (fallbackCopy(listingUrl)) {
            announce("Listing link copied.");
        } else {
            announce(
                "Listing link could not be copied."
            );
        }
    }

    shareButtons.forEach(function (shareButton) {
        shareButton.addEventListener(
            "click",
            function () {
                const shareData = {
                    title: document.title,
                    url: window.location.href,
                };

                if (navigator.share) {
                    navigator.share(shareData).then(
                        function () {
                            announce(
                                "Listing shared."
                            );
                        },
                        function (error) {
                            if (
                                error
                                && error.name === "AbortError"
                            ) {
                                return;
                            }

                            copyListingUrl();
                        }
                    );

                    return;
                }

                copyListingUrl();
            }
        );
    });

    if (printButton) {
        printButton.addEventListener(
            "click",
            function () {
                announce(
                    "Opening print and PDF options."
                );
                window.print();
            }
        );
    }
}());
