import { initializeApp } from "firebase/app";
import { getMessaging, getToken } from "firebase/messaging";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCY-OJpKK605y9zma3vgMKcxX2T5tXUnJc",
  authDomain: "hsec-c39e5.firebaseapp.com",
  projectId: "hsec-c39e5",
  storageBucket: "hsec-c39e5.firebasestorage.app",
  messagingSenderId: "81032145118",
  appId: "1:81032145118:web:6237a53b4c73ada76b3a4f"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);
