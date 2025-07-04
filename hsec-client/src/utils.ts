import { getMessaging, getToken, onMessage } from "firebase/messaging";
import { messaging } from "./firebase";
import showPopup from "./utils/Popupmanager";


export const macToId = (mac: string) => {
    return mac.replace(/:/g, "")
}

export const getFCMToken = async () => {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        showPopup("Notification permission not granted. Please enable notifications in your settings.", "error");
        return null;
    }

    const token = await getToken(messaging, {
        vapidKey: "BLnx1M0Zopr1TMD4M8_Em42ffkkl96SgKO_nMm4thRGkscdPg2EC8myoHzVkwzMlJPK0rkyN1ls7HEmwPpuWhr8", // pubkey so no worries
    });
    console.log("FCM Token:", token);

    return token;
}