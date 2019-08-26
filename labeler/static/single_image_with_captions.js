window.addEventListener("unhandledKey", event => {
    let rawEvent = event;
    event = rawEvent.detail;  // original key event
    if (event.key == 'l') {
        $('.to-label-image-caption').toggleClass('hidden-transparent');
    }
});