self.addEventListener('push', function(e) {
    const data = e.data.json();

    self.registration.showNotification(data.head, {
        body: data.body,
        icon: '/static/images/logo.png'
    });
});