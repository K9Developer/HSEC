import { initializeApp } from "firebase/app";
import { getMessaging } from "firebase/messaging/sw";

const firebaseConfig = {
    apiKey: "AIzaSyCY-OJpKK605y9zma3vgMKcxX2T5tXUnJc",
    authDomain: "hsec-c39e5.firebaseapp.com",
    projectId: "hsec-c39e5",
    storageBucket: "hsec-c39e5.firebasestorage.app",
    messagingSenderId: "81032145118",
    appId: "1:81032145118:web:6237a53b4c73ada76b3a4f",
};

const app = initializeApp(firebaseConfig);
export const messaging = getMessaging(app);