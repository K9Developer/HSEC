importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js");

const firebaseConfig = {
    apiKey: "AIzaSyCY-OJpKK605y9zma3vgMKcxX2T5tXUnJc",
    authDomain: "hsec-c39e5.firebaseapp.com",
    projectId: "hsec-c39e5",
    storageBucket: "hsec-c39e5.firebasestorage.app",
    messagingSenderId: "81032145118",
    appId: "1:81032145118:web:6237a53b4c73ada76b3a4f",
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();


messaging.onBackgroundMessage((payload) => {
    console.log("Received background message:", payload);

    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: "/hsec.ico",
        badge: "/hsec.ico",
        image: payload.data?.frame || "/hsec.ico",
        vibrate: [100, 50, 100],
        requireInteraction: true,
        tag: "hsec-notification",
        data: payload.data,
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.data?.url || "/"));
});


